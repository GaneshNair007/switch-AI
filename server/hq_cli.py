"""Authenticated local HQ client; credentials stay in the local environment."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
import urllib.parse


def main():
    from .main import env_file
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',help='snapshot, create, start, decision, task, resume, meeting, assignment, ...')
    parser.add_argument('--args-file',type=Path)
    parser.add_argument('--url',default=os.getenv('SHIPCOURT_URL','http://127.0.0.1:8080'))
    args=parser.parse_args();url=urllib.parse.urlparse(args.url)
    if url.scheme!='https' and not (url.scheme=='http' and url.hostname in ('127.0.0.1','localhost')):
        parser.error('HTTPS required outside localhost')
    body={'action':args.action,'args':json.loads(args.args_file.read_text(encoding='utf-8-sig')) if args.args_file else {}}
    request=urllib.request.Request(args.url.rstrip('/')+'/api/hq/action',data=json.dumps(body).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['SHIPCOURT_TOKEN']})
    with urllib.request.urlopen(request,timeout=180) as response:result=json.load(response)
    print(json.dumps(result,indent=2,ensure_ascii=True))


if __name__=='__main__':main()
