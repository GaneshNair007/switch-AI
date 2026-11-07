"""Provision local bearer credentials without printing secrets."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--voice-gateway',action='store_true')
    group.add_argument('--hook', metavar='AGENT_ID')
    args=parser.parse_args()
    target=Path(__file__).resolve().parents[1]/'.env'
    content=target.read_text(encoding='utf-8') if target.exists() else ''
    lines=content.splitlines()
    values={line.split('=',1)[0].strip():line.split('=',1)[1].strip() for line in lines if '=' in line and not line.lstrip().startswith('#')}
    key='SHIPCOURT_VOICE_TOKEN' if args.voice_gateway else 'SHIPCOURT_HOOK_TOKEN' if args.hook else 'SHIPCOURT_TOKEN'
    if values.get(key):
        raise SystemExit('Credential already exists; refusing to overwrite it.')
    identities=json.loads(values.get('SHIPCOURT_IDENTITIES','[]'))
    token=secrets.token_urlsafe(48)
    identity={'id':'voice-gateway' if args.voice_gateway else 'hook:'+args.hook if args.hook else 'local-human',
              'token_sha256':hashlib.sha256(token.encode()).hexdigest(),
              'roles':['voice_gateway'] if args.voice_gateway else ['hook'] if args.hook else ['operator','approver'],
              'scopes':['gateway:voice'] if args.voice_gateway else ['hook:'+args.hook] if args.hook else ['*']}
    if any(i['id']==identity['id'] for i in identities):
        raise SystemExit('Identity already exists; refusing to duplicate it.')
    identities.append(identity)
    lines=[line for line in lines if line.split('=',1)[0].strip() not in ('SHIPCOURT_IDENTITIES',key)]
    lines.extend(['SHIPCOURT_IDENTITIES='+json.dumps(identities),key+'='+token])
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote {key} and its scoped identity to .env (gitignored). Secrets were not printed.')

if __name__=='__main__': main()
