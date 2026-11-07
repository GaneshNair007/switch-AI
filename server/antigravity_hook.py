"""Real IDE hook entry point. Consumes actual stdin; never synthesizes an event."""
import json
import os
from pathlib import Path
import sys


def main():
    root=Path(__file__).resolve().parents[1]
    values={}
    env=root/'.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);values[k.strip()]=v.strip().strip('\"').strip("'")
    # Deliberately do not export unrelated Groq, Discord or GitHub credentials.
    for key in ('SHIPCOURT_HOOK_TOKEN','SHIPCOURT_AGENT_ID','SHIPCOURT_COORDINATOR_URL','SHIPCOURT_WORKSPACE_ROOT'):
        if values.get(key):os.environ.setdefault(key,values[key])
    os.environ.setdefault('SHIPCOURT_WORKSPACE_ROOT',str(root))
    os.environ.setdefault('SHIPCOURT_COORDINATOR_URL','http://127.0.0.1:8080')
    if not os.environ.get('SHIPCOURT_HOOK_TOKEN') or not os.environ.get('SHIPCOURT_AGENT_ID'):
        print(json.dumps({'decision':'deny','reason':'Provision a scoped hook identity and server assignment first'}));return
    sys.path.insert(0,str(root/'linking_antigravity'))
    from scope_guard.antigravity.hook_handler import main as consume_real_event
    consume_real_event()


if __name__=='__main__':main()
