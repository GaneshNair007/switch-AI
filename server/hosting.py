"""Deployment configuration checks; no cloud resources are created here."""
import os
import json
import hashlib
import shutil
import sqlite3
import re
from pathlib import Path
from urllib.parse import urlsplit


def public_origin():
    value=os.getenv('SHIPCOURT_PUBLIC_ORIGIN','').rstrip('/')
    if not value:return None
    parsed=urlsplit(value)
    if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('SHIPCOURT_PUBLIC_ORIGIN must be an HTTPS origin without path or credentials')
    return value


def validate_host(handler):
    configured=public_origin()
    if not configured:return
    host=handler.headers.get('Host','')
    expected=urlsplit(configured).netloc
    loopback=host.split(':',1)[0] in ('localhost','127.0.0.1') and handler.client_address[0] in ('127.0.0.1','::1')
    if host!=expected and not loopback:raise PermissionError('Unexpected request host')


def read_env(path):
    return {k.strip():v.strip().strip("'").strip('"') for line in Path(path).read_text(encoding='utf-8-sig').splitlines()
            if line.strip() and not line.lstrip().startswith('#') and '=' in line for k,v in [line.split('=',1)]}


def write_private(path,values):
    # Never overwrite a bundle that may already contain a different deployment.
    with open(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf-8') as f:
        for key,value in values.items():
            if '\n' in value or '\r' in value:raise ValueError('Environment values must be one line')
            f.write(key+'='+value+'\n')


def prepare_bundle(root,destination,domain,email,switch_env=None):
    from .groq_agents import ROLES
    hostname=r'(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'
    if len(domain)>253 or not re.fullmatch(hostname,domain):
        raise ValueError('Use a DNS hostname, without scheme or path')
    if not re.fullmatch(r'[A-Za-z0-9._%+-]+@'+hostname,email):raise ValueError('Certificate contact email required')
    root=Path(root).resolve();destination=Path(destination).resolve()
    if not destination.is_relative_to(root/'.runtime'):
        raise ValueError('Keep private exports under the gitignored .runtime directory')
    values=read_env(root/'.env')
    for key in ('SHIPCOURT_TOKEN','SHIPCOURT_IDENTITIES','GROQ_API_KEY','DEFAULT_GROQ_MODEL'):
        if not values.get(key):raise ValueError('Missing '+key)
    identities=json.loads(values['SHIPCOURT_IDENTITIES'])
    digest=hashlib.sha256(values['SHIPCOURT_TOKEN'].encode()).hexdigest()
    if not any(i.get('token_sha256')==digest and 'operator' in i.get('roles',[]) for i in identities):
        raise ValueError('Workspace credential has no matching operator identity')
    clients=json.loads(values.get('SWITCH_CLIENTS','[]'))
    if {c['role'] for c in clients}!=set(ROLES):raise ValueError('Configure the five actual Switch clients before exporting')
    old_url=values.get('SWITCH_URL','').rstrip('/')
    for client in clients:
        if old_url and client['url'].rstrip('/')!=old_url:raise ValueError('Multiple Switch servers require an explicit deployment configuration')
        if not values.get(client['key_env']):raise ValueError('Missing registered agent credential')
        client['url']='http://127.0.0.1:8000'
    values['SWITCH_URL']='http://127.0.0.1:8000';values['SWITCH_CLIENTS']=json.dumps(clients,separators=(',',':'))
    backend_names={'SHIPCOURT_TOKEN','SHIPCOURT_IDENTITIES','GROQ_API_KEY','GROQ_API_KEY_FALLBACK_1','GROQ_API_KEY_FALLBACK_2',
        'DEFAULT_GROQ_MODEL','GITHUB_TOKEN','DISCORD_BOT_TOKEN','DISCORD_APPLICATION_ID','DISCORD_GUILD_ID','DISCORD_MEMBERS',
        'DISCORD_PUBLIC_KEY','SWITCH_URL','SWITCH_CLIENTS','SWITCH_PARTICIPANTS','SHIPCOURT_RESEARCH_HOSTS'}|{c['key_env'] for c in clients}
    voice_names={'DISCORD_VOICE_BOT_TOKEN','DISCORD_GUILD_ID','SHIPCOURT_VOICE_TOKEN','GROQ_API_KEY',
        'GROQ_STT_MODEL','GROQ_STT_LANGUAGE','GROQ_TTS_MODEL','GROQ_TTS_VOICE'}
    if values.get('DISCORD_VOICE_BOT_TOKEN') and not values.get('SHIPCOURT_VOICE_TOKEN'):
        raise ValueError('Voice bot needs its scoped gateway credential')
    if values.get('DISCORD_VOICE_BOT_TOKEN'):
        voice_digest=hashlib.sha256(values['SHIPCOURT_VOICE_TOKEN'].encode()).hexdigest()
        if not any(i.get('token_sha256')==voice_digest and 'voice_gateway' in i.get('roles',[]) for i in identities):
            raise ValueError('Voice credential has no matching gateway identity')
    db=Path(values.get('SHIPCOURT_STATE_PATH','.runtime/shipcourt.sqlite3'))
    if not db.is_absolute():db=root/db
    if not db.is_file():raise ValueError('Application database does not exist')
    if not (root/'.runtime'/'discord_channels.json').is_file():raise ValueError('Discord channel map is required for this deployment')
    switch=read_env(switch_env) if switch_env else None
    if destination.exists():raise ValueError('Bundle destination already exists; use a new path')
    destination.mkdir(parents=True,mode=0o700);config=destination/'config';state=destination/'state'
    config.mkdir(mode=0o700);state.mkdir(mode=0o700)
    write_private(config/'backend.env',{k:v for k,v in values.items() if k in backend_names and v})
    write_private(config/'voice.env',{k:v for k,v in values.items() if k in voice_names and v})
    write_private(config/'host.env',{'SHIPCOURT_DOMAIN':domain,'ACME_EMAIL':email,
        'SHIPCOURT_CONFIG_DIR':'/opt/shipcourt/config','SHIPCOURT_STATE_DIR':'/opt/shipcourt/state'})
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(state/'shipcourt.sqlite3') as target:
        source.backup(target)
    os.chmod(state/'shipcourt.sqlite3',0o600)
    for name in ('discord_channels.json','switch-agents.json'):
        source=root/'.runtime'/name
        if source.exists():shutil.copyfile(source,state/name);os.chmod(state/name,0o600)
    if not (state/'discord_channels.json').exists():raise ValueError('Discord channel map is required for the voice deployment')
    if switch:
        switch.update(SWITCH_VERSION='0.31.0',SWITCH_BIND_ADDR='127.0.0.1',API_HOST_PORT='8000',
            POSTGRES_HOST_PORT='5432',FRONTEND_BASE_URL='http://127.0.0.1:8000')
        write_private(config/'switch.env',switch)
    manifest={'hostname':domain,'application_database':'state/shipcourt.sqlite3','switch_database_included':False,
        'switch_secrets_included':bool(switch_env),'native_clients':len(clients),'secret_files':'config/*.env; never commit or publish',
        'cutover':'Restore the matching Switch Postgres database and encryption keys; stop laptop gateways before starting cloud gateways.'}
    (destination/'MIGRATION.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',required=True)
    parser.add_argument('--domain',required=True);parser.add_argument('--email',required=True)
    parser.add_argument('--output',type=Path,default=Path('.runtime/hosting-export'))
    parser.add_argument('--switch-env',type=Path,help='Existing Switch native environment; keeps encryption keys for migration')
    args=parser.parse_args()
    print(json.dumps(prepare_bundle(Path(__file__).resolve().parents[1],args.output,args.domain,args.email,args.switch_env),indent=2))


if __name__=='__main__':main()
