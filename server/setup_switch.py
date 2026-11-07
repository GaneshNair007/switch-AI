"""Register real custom agents; persist returned secrets locally, never print them."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
from .groq_agents import ROLES

ROOT = Path(__file__).resolve().parents[1]


def write_env(updates):
    path = ROOT / '.env'
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    lines = [line for line in lines if line.partition('=')[0].strip() not in updates]
    lines.extend(key + '=' + value for key,value in updates.items())
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def register():
    from .main import env_file
    base = os.environ['SWITCH_URL'].rstrip('/')
    from .switch_protocol import SwitchProtocolClient
    # Validate loopback/HTTPS before sending a registration credential.
    from .store import Store
    SwitchProtocolClient(base, 'probe', 'probe', 'probe', Store())
    token = os.environ.get('SWITCH_REGISTRATION_TOKEN')
    if not token:
        raise RuntimeError('Save SWITCH_REGISTRATION_TOKEN in .env first')
    registry_path = ROOT / '.runtime' / 'switch-agents.json'
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
    for role,(label,_) in ROLES.items():
        if role in registry:
            print('Preserved existing registration:',role)
            continue
        payload = {'name':'shipcourt-'+role.replace('_','-'),'display_name':label,
            'description':label+' for Ship Court. Custom Groq Python runtime; advisory only.',
            'connector_type':'groq_custom',
            'integration_profile':{'connection_model':'always_on','message_exchange':True,
                'pre_invocation_mediation':[],'post_invocation_mediation':[],'event_reporting':[]},
            'models':[{'name':os.environ['DEFAULT_GROQ_MODEL'],'description':'Configured Groq model'}],
            'metadata':{'runtime':'groq_custom','role':role},'overwrite':False}
        req = urllib.request.Request(base+'/agents',data=json.dumps(payload).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=20) as response:
            result = json.load(response)
        registry[role] = {'agent_id':result['id'],'api_key':result['api_key'],'name':payload['name']}
        registry_path.parent.mkdir(exist_ok=True)
        registry_path.write_text(json.dumps(registry),encoding='utf-8')
        write_env({'SWITCH_'+role.upper()+'_KEY':result['api_key']})
        print('Registered:',role,'ID:',result['id'])
    print('All five custom Groq agents registered. Keys saved locally; no paid harness used.')


def configure(room_id, sender_map):
    """Build local client configuration from registrations and observed identities."""
    from .main import env_file
    from .switch_protocol import SwitchProtocolClient
    from .store import Store
    registry=json.loads((ROOT/'.runtime'/'switch-agents.json').read_text(encoding='utf-8'))
    senders=json.loads(Path(sender_map).read_text(encoding='utf-8-sig'))
    agents=senders.get('agents',{});humans=senders.get('humans',[])
    if not room_id.strip() or set(registry)!=set(ROLES) or set(agents)!=set(ROLES):
        raise ValueError('A real room ID, five registrations and five observed agent sender IDs are required')
    if not isinstance(humans,list) or not humans or any(not isinstance(s,str) or not s.strip() for s in [*agents.values(),*humans]):
        raise ValueError('Supply actual agent sender IDs and at least one human sender ID')
    if len(set(agents.values()))!=len(ROLES) or set(humans)&set(agents.values()):
        raise ValueError('Agent and human transport identities must be distinct')
    base=os.environ['SWITCH_URL'].rstrip('/')
    SwitchProtocolClient(base,'validation-only','validation-only',room_id,Store())
    clients=[];updates={}
    for role in ROLES:
        agent=registry[role];key='SWITCH_'+role.upper()+'_KEY'
        updates[key]=agent['api_key']
        clients.append({'url':base,'agent_id':agent['agent_id'],'key_env':key,'room_id':room_id,
            'role':role,'runtime':'groq_custom','mention':'@'+agent['name'],'sender_id':agents[role]})
    updates['SWITCH_CLIENTS']=json.dumps(clients,separators=(',',':'))
    updates['SWITCH_PARTICIPANTS']=json.dumps({s:{'actor_type':'human','roles':['operator'],'scopes':[]} for s in humans},separators=(',',':'))
    write_env(updates)
    print('Configured five existing custom clients and verified-by-operator transport mappings. Keys were not printed. Restart the backend to connect.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    operation=parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--register',action='store_true')
    operation.add_argument('--configure',action='store_true')
    parser.add_argument('--room-id');parser.add_argument('--sender-map',type=Path)
    args=parser.parse_args()
    if args.register:register()
    else:
        if not args.room_id or not args.sender_map:parser.error('--configure needs --room-id and --sender-map')
        configure(args.room_id,args.sender_map)
