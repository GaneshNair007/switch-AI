"""GitHub REST adapter. Writes require separate explicit, scoped authorization."""
import hashlib
import json
import os
import re
import threading
import urllib.request
from .store import Store


def parse_pr(url):
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?', url)
    if not match:
        raise ValueError('Expected a GitHub pull request URL')
    return match.group(1), int(match.group(2))


class GitHubClient:
    def __init__(self, token=None, transport=None):
        self.token = token if token is not None else os.getenv('GITHUB_TOKEN', '')
        self.transport = transport

    def request(self, method, path, payload=None):
        if not path.startswith('/repos/'):
            raise ValueError('Unsupported GitHub endpoint')
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'ShipCourt', 'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        elif method != 'GET' and self.transport is None:
            raise RuntimeError('GITHUB_TOKEN is required for live writes')
        req = urllib.request.Request('https://api.github.com' + path,
                                     data=json.dumps(payload).encode() if payload is not None else None,
                                     headers=headers, method=method)
        if self.transport:
            return self.transport(req)
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)

    def pages(self, path):
        for page in range(1, 101):
            values = self.request('GET', path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            if not isinstance(values, list):
                raise RuntimeError('Invalid GitHub list response')
            yield from values
            if len(values) < 100:
                return
        raise RuntimeError('Pagination limit reached; refusing incomplete duplicate check')

    def evidence(self, url):
        repo, number = parse_pr(url)
        prefix = f'/repos/{repo}'
        pr = self.request('GET', f'{prefix}/pulls/{number}')
        if pr.get('number') != number or pr.get('base', {}).get('repo', {}).get('full_name', '').lower() != repo.lower():
            raise ValueError('GitHub returned a different PR target')
        files = list(self.pages(f'{prefix}/pulls/{number}/files'))
        return {'source': 'github_api', 'pr_url': url, 'repository': repo, 'pr_number': number,
                'head_sha': pr['head']['sha'], 'state': pr['state'], 'title': pr['title'],
                'body': pr.get('body') or '', 'files': [{'filename': f['filename'], 'patch': f.get('patch', 'Patch unavailable')} for f in files]}


class GitHubOperations:
    def __init__(self, authorization, store=None, client=None):
        self.authorization = authorization
        self.store, self.client = store or Store(), client or GitHubClient()
        self.lock = threading.RLock()

    def plan(self, case, evidence):
        repo, number = parse_pr(case.pr_url)
        if not case.verdict:
            raise ValueError('A recorded human verdict is required')
        label = {'APPROVE': 'ship-court:approved', 'BLOCK': 'ship-court:blocked', 'CONDITIONS': 'ship-court:conditional'}[case.verdict.type.value]
        return {'case_id': case.case_id, 'repository': repo, 'pr_number': number, 'head_sha': evidence['head_sha'],
                'comment': case.release_brief, 'labels': [label],
                'issues': [{'title': f'[{case.case_id}] {c.description[:150]}', 'body': f'{c.description}\nOwner: {c.owner}\nSource: {case.pr_url}'} for c in case.verdict.conditions]}

    def execute(self, plan, principal):
        self.authorization.require(principal, scope=f"case:{plan['case_id']}:github")
        digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        with self.lock:
            existing = self.store.get('github', digest)
            if existing and existing['status'] == 'CONFIRMED':
                return existing
            repo, number = plan['repository'], plan['pr_number']
            parse_pr(f'https://github.com/{repo}/pull/{number}')
            prefix = f'/repos/{repo}'
            current = self.client.request('GET', f'{prefix}/pulls/{number}')
            if current.get('number') != number or current.get('base', {}).get('repo', {}).get('full_name', '').lower() != repo.lower():
                raise ValueError('GitHub target identity mismatch')
            if current['head']['sha'] != plan['head_sha'] or current['state'] != 'open':
                raise ValueError('PR changed or closed; a new review and approval are required')
            result = {'plan_hash': digest, 'status': 'IN_PROGRESS', 'urls': [], 'actor': principal.subject}
            self.store.put('github', digest, result)
            try:
                marker = f'<!-- shipcourt:{digest} -->'
                comment = next((c for c in self.client.pages(f'{prefix}/issues/{number}/comments') if marker in (c.get('body') or '')), None)
                if comment is None:
                    comment = self.client.request('POST', f'{prefix}/issues/{number}/comments', {'body': plan['comment'] + '\n' + marker})
                result['urls'].append(comment['html_url'])
                # Labels are set idempotently; require existing repository labels.
                labels = self.client.request('POST', f'{prefix}/issues/{number}/labels', {'labels': plan['labels']})
                if not set(plan['labels']).issubset({label['name'] for label in labels}):
                    raise RuntimeError('GitHub did not confirm requested labels')
                all_issues = list(self.client.pages(f'{prefix}/issues?state=all'))
                for index, issue_plan in enumerate(plan['issues']):
                    issue_marker = f'<!-- shipcourt:{digest}:condition:{index} -->'
                    issue = next((i for i in all_issues if issue_marker in (i.get('body') or '')), None)
                    if issue is None:
                        issue = self.client.request('POST', f'{prefix}/issues', {**issue_plan, 'body': issue_plan['body'] + '\n' + issue_marker})
                    result['urls'].append(issue['html_url'])
                result['status'] = 'CONFIRMED'
            except Exception as exc:
                result['status'] = 'FAILED_OR_PARTIAL'
                result['error_type'] = type(exc).__name__
                raise
            finally:
                self.store.put('github', digest, result)
                self.store.event('github.operation', plan['case_id'], principal.subject, result)
            return result
