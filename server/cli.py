"""Authenticated CLI for the same HTTP services used by the dashboard."""
import argparse
import json
import os
import urllib.request

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('route', help='API route, e.g. /api/cases')
    parser.add_argument('--json', dest='body', help='JSON object; omit for GET')
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    args = parser.parse_args()
    from .main import env_file  # Load local .env using the application's configuration path.
    token = os.environ.get('SHIPCOURT_TOKEN')
    if not token:
        parser.error('Set SHIPCOURT_TOKEN to a provisioned credential')
    body = json.dumps(json.loads(args.body)).encode() if args.body else None
    req = urllib.request.Request(args.url.rstrip('/') + args.route, data=body,
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        print(json.dumps(json.load(response), indent=2))

if __name__ == '__main__':
    main()
