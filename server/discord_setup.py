"""Read-only plan by default; explicit, non-destructive Discord reconciliation."""
import argparse
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error
import uuid

LAYOUT = {
 '01 — COMMAND CENTER':['start-here','mission-control'],
 '02 — TEAM COLLABORATION':['team-chat','dev-watch','agent-handoffs'],
 '03 — BOARDROOM OS':['Boardroom Live','meeting-floor','meeting-recaps'],
 '04 — ENGINEERING COURT':['case-docket','ship-court','parallel-earth'],
 '05 — DELIVERY & DECISIONS':['approvals','github-results'],
 '06 — PERSONAL AI STUDIO':['idea-lab','my-projects'],
 '07 — BACKSTAGE':['agent-traces','system-alerts'],
}
PRIVATE={'approvals','agent-traces','system-alerts'}
MAP_PATH=Path('.runtime/discord_channels.json')


def save_mapping(guild,ids):
    previous=json.loads(MAP_PATH.read_text(encoding='utf-8')) if MAP_PATH.exists() else {}
    if previous and previous.get('guild_id')!=guild:raise PermissionError('Channel map belongs to another server')
    MAP_PATH.parent.mkdir(exist_ok=True)
    MAP_PATH.write_text(json.dumps({**previous,'guild_id':guild,'channels':ids},indent=2),encoding='utf-8')


class DiscordREST:
    def __init__(self, token=None): self.token=token or os.environ['DISCORD_BOT_TOKEN']
    def call(self, method, path, body=None, attachment=None):
        content_type='application/json';payload=json.dumps(body).encode() if body is not None else None
        if attachment:
            filename,document=attachment;boundary='shipcourt'+uuid.uuid4().hex
            payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n'.encode()+json.dumps(body).encode()+
                f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="{filename}"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'.encode()+document.encode()+f'\r\n--{boundary}--\r\n'.encode())
            content_type='multipart/form-data; boundary='+boundary
        for attempt in range(4):
            req=urllib.request.Request('https://discord.com/api/v10'+path,method=method,
                data=payload,headers={'Authorization':'Bot '+self.token,'Content-Type':content_type,'User-Agent':'ShipCourt/1.0'})
            try:
                with urllib.request.urlopen(req,timeout=20) as response:
                    data=response.read();return json.loads(data) if data else None
            except urllib.error.HTTPError as exc:
                if exc.code!=429 or attempt==3: raise
                data=json.load(exc);time.sleep(min(10,float(data.get('retry_after',1))))


def overwrites(guild,bot_id,members,existing=()):
    result={str(o['id']):dict(o) for o in existing}
    for ident,allow,deny,kind in [(guild,0,1024,0),(bot_id,1024|2048|65536,0,1)]+[
        (uid,1024|65536|(2048 if 'operator' in info.get('roles',[]) else 0),0 if 'operator' in info.get('roles',[]) else 2048,1)
        for uid,info in members.items() if set(info.get('roles',[])) & {'operator','approver'}]:
        prev=result.get(ident,{})
        result[ident]={'id':ident,'type':kind,'allow':str((int(prev.get('allow',0))|allow)&~deny),
                      'deny':str((int(prev.get('deny',0))|deny)&~allow)}
    return list(result.values())


def plan(api,guild,members,mapping=None):
    channels=api.call('GET',f'/guilds/{guild}/channels');bot=api.call('GET','/users/@me')
    member=api.call('GET',f"/guilds/{guild}/members/{bot['id']}")
    roles=api.call('GET',f'/guilds/{guild}/roles');permissions=0
    for role in roles:
        if role['id']==guild or role['id'] in member['roles']:permissions|=int(role['permissions'])
    changes=[];conflicts=[];mapping=mapping or {}
    for category,names in LAYOUT.items():
        matches=[c for c in channels if c['type']==4 and c['name']==category]
        if len(matches)>1:conflicts.append('Duplicate category '+category)
        changes.append({'name':category,'type':4,'id':matches[0]['id'] if matches else None,'action':'reuse' if matches else 'create'})
        for name in names:
            kind=2 if name=='Boardroom Live' else 0
            ident=mapping.get(name)
            names_to_match=(name,'boardroom') if name=='Boardroom Live' else (name,)
            matches=[c for c in channels if (c['id']==ident if ident else c['name'] in names_to_match) and c['type']==kind]
            if len(matches)>1:conflicts.append('Ambiguous channel '+name)
            target=matches[0] if matches else None
            item={'name':name,'type':kind,'category':category,'id':target['id'] if target else None,'action':'reuse' if target else 'create','private':name in PRIVATE}
            if name in PRIVATE:item['permission_overwrites']=overwrites(guild,bot['id'],members,(target or {}).get('permission_overwrites',[]))
            if target and name in PRIVATE:
                allowed={guild,bot['id']}|set(members)
                unexpected=[o['id'] for o in target.get('permission_overwrites',[]) if o['id'] not in allowed and int(o.get('allow',0))&1024]
                if unexpected:conflicts.append('Private channel '+name+' has unrelated View Channel grants; review them manually')
            item['permissions_match']=not item.get('permission_overwrites') or sorted(item['permission_overwrites'],key=lambda x:x['id'])==sorted((target or {}).get('permission_overwrites',[]),key=lambda x:x['id'])
            item['parent_matches']=not target or not matches or target.get('parent_id')==next((c['id'] for c in channels if c['type']==4 and c['name']==category),None)
            changes.append(item)
    return {'guild_id':guild,'changes':changes,'conflicts':conflicts,
        'provisioning_allowed':bool(permissions&8 or permissions&16 and permissions&(1<<28)),
        'required_setup_permissions':['Manage Channels','Manage Roles (permission overwrites only)'],
        'runtime_permissions':['View Channels','Send Messages','Read Message History','Attach Files','Manage Webhooks (Switch)','Connect','Speak'],
        'bot_id':bot['id']}


def apply(api,report,approved_guild):
    if approved_guild!=report['guild_id']:raise PermissionError('Explicit target-guild approval required')
    if MAP_PATH.exists() and json.loads(MAP_PATH.read_text(encoding='utf-8')).get('guild_id')!=approved_guild:
        raise PermissionError('Existing channel map belongs to another server')
    if report['conflicts']:raise ValueError('Resolve conflicts before applying')
    if not report['provisioning_allowed']:raise PermissionError('Setup needs Manage Channels and Manage Roles; runtime does not')
    ids={};guild=report['guild_id']
    for item in report['changes']:
        if item['action']=='create':
            payload={'name':item['name'],'type':item['type']}
            if 'category' in item:payload['parent_id']=ids[item['category']]
            if 'permission_overwrites' in item:payload['permission_overwrites']=item['permission_overwrites']
            result=api.call('POST',f'/guilds/{guild}/channels',payload);ident=result['id']
        else:
            ident=item['id']
            payload={}
            if 'category' in item:payload['parent_id']=ids[item['category']]
            if 'permission_overwrites' in item:payload['permission_overwrites']=item['permission_overwrites']
            if payload:api.call('PATCH','/channels/'+ident,payload)
        ids[item['name']]=ident
        save_mapping(guild,ids)
    return ids


def main():
    from .main import env_file
    p=argparse.ArgumentParser();p.add_argument('--plan',action='store_true');p.add_argument('--validate',action='store_true')
    p.add_argument('--apply',action='store_true');p.add_argument('--approve-guild');args=p.parse_args()
    guild=os.environ['DISCORD_GUILD_ID'];api=DiscordREST()
    mapping=json.loads(MAP_PATH.read_text()).get('channels',{}) if MAP_PATH.exists() else {}
    report=plan(api,guild,json.loads(os.getenv('DISCORD_MEMBERS','{}')),mapping)
    if args.apply:print(json.dumps(apply(api,report,args.approve_guild),indent=2))
    else:
        print(json.dumps(report,indent=2))
        if args.validate:
            if report['conflicts'] or any(i['action']=='create' or not i.get('permissions_match',True) or not i.get('parent_matches',True) for i in report['changes']):
                raise SystemExit('Workspace setup is incomplete; inspect plan and permissions')
            save_mapping(guild,{i['name']:i['id'] for i in report['changes']})

if __name__=='__main__':main()
