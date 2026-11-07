import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import pytest
from server.authorization import AuthorizationService
from server.case_manager import CaseManager
from server.switch_room import SwitchRoom
from server.floor_controller import FloorRequestController, FloorState

TOKEN = 'local-test-credential-with-at-least-32-characters'

@pytest.fixture
def auth():
    return AuthorizationService([{'id': 'human-123', 'token_sha256': hashlib.sha256(TOKEN.encode()).hexdigest(),
                                 'roles': ['approver'], 'scopes': ['*']}])

@pytest.fixture
def principal(auth):
    return auth.authenticate('Bearer ' + TOKEN)

@pytest.mark.parametrize('actor', ['admin', 'developer', 'judge', 'approver', 'Priya', '@Priya', 'Priya Nair', 'p', '', {'is_human': True}])
def test_spoofed_actors_rejected(auth, actor):
    assert not SwitchRoom(authorization=auth).enforce_human_verdict_gate(actor)
    mgr = CaseManager(authorization=auth)
    with pytest.raises(PermissionError):
        mgr.record_verdict('fake', 'APPROVE', judge='admin', is_human=True, principal=actor)


def test_session_forgery_scope_expiry_and_revocation(auth, principal):
    with pytest.raises(PermissionError):
        auth.require(replace(principal))
    auth.revoke(principal)
    with pytest.raises(PermissionError):
        auth.require(principal)
    clock = [0]
    scoped = AuthorizationService([{'id': 'user', 'token_sha256': hashlib.sha256(TOKEN.encode()).hexdigest(),
                                   'roles': ['approver'], 'scopes': ['case:1:verdict']}], clock=lambda: clock[0])
    p = scoped.authenticate('Bearer ' + TOKEN)
    with pytest.raises(PermissionError):
        scoped.require(p, scope='case:2:verdict')
    clock[0] = 301
    with pytest.raises(PermissionError):
        scoped.require(p)


def test_authenticated_verdict_ignores_display_name(auth, principal):
    mgr = CaseManager(authorization=auth)
    case = mgr.open_case('https://github.com/acme/shop/pull/482')
    mgr.run_procedural_pipeline(case.case_id)
    mgr.record_verdict(case.case_id, 'CONDITIONS add alert', judge='forged', principal=principal)
    assert case.verdict.judge == 'human-123'
    with pytest.raises(ValueError):
        mgr.record_verdict(case.case_id, 'APPROVE', principal=principal)


def request(controller, agent='agent-1', meeting='m1', priority=80):
    return controller.raise_hand(meeting, agent, 'hand', 'Evidence', 'Speech', priority)


def test_atomic_grants_and_meeting_isolation(auth, principal):
    floor = FloorRequestController(SwitchRoom(authorization=auth))
    requests = [request(floor, str(i)) for i in range(20)]
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda r: floor.grant_floor(r.request_id, principal), requests))
    assert sum(r['granted'] for r in results) == 1
    active = floor.active_speakers['m1']
    assert floor.requests[active].state == FloorState.GRANTED
    assert floor.start_speaking(active) == 'Speech'
    other = request(floor, meeting='m2')
    assert floor.grant_floor(other.request_id, principal)['granted']
    floor.dismiss(active, principal, interrupt=True)
    assert 'm1' not in floor.active_speakers
    assert floor.active_speakers['m2'] == other.request_id
    with pytest.raises(ValueError):
        floor.start_speaking(active)


def test_priority_expiration_dedup_and_restart(auth, principal, tmp_path):
    clock = [10]
    floor = FloorRequestController(SwitchRoom(authorization=auth), db_path=tmp_path/'floor.db', clock=lambda: clock[0])
    low = request(floor, priority=1)
    assert request(floor, priority=1).request_id == low.request_id
    high = request(floor, agent='urgent', priority=99)
    assert floor.grant_floor(low.request_id, principal)['reason'] == 'higher_priority_pending'
    assert floor.grant_floor(high.request_id, principal)['granted']
    assert not floor.grant_floor(high.request_id, principal)['granted']
    floor.close()
    floor = FloorRequestController(SwitchRoom(authorization=auth), db_path=tmp_path/'floor.db', clock=lambda: clock[0])
    assert floor.requests[high.request_id].state == FloorState.INTERRUPTED
    assert not floor.active_speakers
    clock[0] = 100
    assert floor.grant_floor(low.request_id, principal)['reason'] == 'request_expired'
    assert len(floor.events()) >= 10


def test_floor_rejects_unauthenticated_grants(auth):
    floor = FloorRequestController(SwitchRoom(authorization=auth))
    req = request(floor)
    with pytest.raises(PermissionError):
        floor.grant_floor(req.request_id, 'admin')
