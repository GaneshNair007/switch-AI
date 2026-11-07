"""Local integration contracts; GitHub and LLM responses are controlled fixtures."""
import hashlib
import json
from dataclasses import asdict
from unittest.mock import Mock
import pytest
from server.authorization import AuthorizationService
from server.github_client import GitHubClient
from server.unified_pipeline import UnifiedBoardroomCourtPipeline

TOKEN = 'test-only-credential-32-characters-minimum'

class FakeGitHub:
    def __init__(self):
        self.comments, self.issues, self.writes = [], [], []
        self.sha = 'abc123'

    def __call__(self, req):
        path = req.full_url.split('api.github.com')[1].split('?')[0]
        method = req.get_method()
        if path.endswith('/pulls/18'):
            return {'number': 18, 'head': {'sha': self.sha}, 'base': {'repo': {'full_name': 'acme/shop'}}, 'state': 'open', 'title': 'New checkout timeout', 'body': 'Use bounded retries'}
        if path.endswith('/files'):
            return [{'filename': 'checkout.py', 'patch': '+ timeout=0.2'}]
        if method == 'GET':
            return self.comments if path.endswith('/comments') else self.issues
        self.writes.append(path)
        body = json.loads(req.data)
        if path.endswith('/labels'):
            return [{'name': name} for name in body['labels']]
        record = {**body, 'html_url': 'https://github.com/acme/shop/issues/' + str(len(self.writes)), 'id': len(self.writes)}
        (self.comments if path.endswith('/comments') else self.issues).append(record)
        return record

@pytest.fixture
def setup(tmp_path):
    auth = AuthorizationService([{'id': 'human-1', 'token_sha256': hashlib.sha256(TOKEN.encode()).hexdigest(),
                                  'roles': ['operator', 'approver', 'hook'], 'scopes': ['*']}])
    principal = auth.authenticate('Bearer ' + TOKEN)
    fake = FakeGitHub()
    engine = Mock()
    engine.run_live_trial.return_value = {'prosecutor_indictment': 'Timeout shown in checkout.py patch.',
        'defender_rebuttal': 'Load testing remains unverified.', 'verdict': 'CONDITIONS', 'conditions': ['Load test'], 'is_live_trial': False}
    path = tmp_path/'state.sqlite3'
    service = UnifiedBoardroomCourtPipeline(authorization=auth, db_path=path, github_client=GitHubClient(transport=fake), debate_engine=engine)
    return service, principal, fake, path


def test_full_workflow_requires_separate_human_steps_and_persists(setup):
    service, p, fake, path = setup
    case = service.open_case('https://github.com/acme/shop/pull/18', ['checkout-service'], p)
    result = service.review(case.case_id, p)
    assert result['binding_authorization'] is False
    assert case.verdict is None
    assert case.state.value == 'AWAITING_VERDICT'
    assert not fake.writes
    with pytest.raises(PermissionError):
        service.decide(case.case_id, 'APPROVE', 'admin')
    service.decide(case.case_id, 'CONDITIONS load test checkout', p)
    plan = service.github_plan(case.case_id, p)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    assert not fake.writes
    with pytest.raises(ValueError):
        service.execute_github(case.case_id, p, 'wrong-hash')
    confirmed = service.execute_github(case.case_id, p, digest)
    assert confirmed['status'] == 'CONFIRMED'
    assert len(confirmed['urls']) == 2
    assert len(fake.writes) == 3
    assert service.execute_github(case.case_id, p, digest) == confirmed
    assert len(fake.writes) == 3
    restarted = UnifiedBoardroomCourtPipeline(authorization=service.authorization, db_path=path)
    assert restarted.cases[case.case_id].verdict.judge == 'human-1'
    assert restarted.store.events()[-1]['event_type'] == 'github.operation'


def test_changed_pr_blocks_github_execution(setup):
    service, p, fake, _ = setup
    case = service.open_case('https://github.com/acme/shop/pull/18', ['checkout-service'], p)
    service.review(case.case_id, p)
    service.decide(case.case_id, 'APPROVE', p)
    plan = service.github_plan(case.case_id, p)
    fake.sha = 'new-unreviewed-commit'
    with pytest.raises(ValueError, match='changed'):
        service.github_ops.execute(plan, p)
    assert not fake.writes


def test_violation_replay_survives_restart(setup):
    service, p, _, path = setup
    event = {'agent_id': 'agent-1', 'event_id': 'event-1', 'decision_taken': 'BLOCK', 'explanation': 'Cross-scope edit'}
    first = service.ingest_violation(event, p)
    restarted = UnifiedBoardroomCourtPipeline(authorization=service.authorization, db_path=path)
    assert restarted.ingest_violation(event, p) == first
    assert len(restarted.cases) == 1


def test_legacy_pipeline_cannot_approve_automatically(setup):
    with pytest.raises(RuntimeError, match='approval removed'):
        setup[0].execute_full_flowchart_run(human_approver='Priya')
