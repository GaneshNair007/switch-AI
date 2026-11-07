"""Tests for SwitchRoom and multi-agent live session communication."""
import pytest
from server.switch_room import SwitchRoom
from server.case_manager import CaseManager
from server.agent_runners import (
    CourtClerkAgent, IncidentHistorianAgent, ProsecutorAgent,
    DefenderAgent, RollbackEngineerAgent
)
from server.models import VerdictType
import hashlib
from server.authorization import default_authorization

@pytest.fixture
def human():
    auth = default_authorization()
    token = 'test-room-human-token-at-least-32-characters'
    identity = {'id': 'test-human-id', 'token_sha256': hashlib.sha256(token.encode()).hexdigest(), 'roles': ['approver'], 'scopes': ['*']}
    auth.identities.append(identity)
    principal = auth.authenticate('Bearer ' + token)
    yield principal
    auth.revoke(principal)
    auth.identities.remove(identity)


def test_session_registration_and_status():
    room = SwitchRoom("test-court")
    session = room.register_session("court-clerk", "clerk", "host_server", "claude")
    assert session.status == "ONLINE"
    assert session.session_id is not None

    status_out = room.handle_command("!agents-status", "developer")
    assert "@clerk" in status_out
    assert "host_server" in status_out

def test_exclusive_approver_gate(human):
    room = SwitchRoom("test-court")
    # Agents must never be permitted to approve
    assert room.enforce_human_verdict_gate("prosecutor") is False
    assert room.enforce_human_verdict_gate("court-clerk") is False
    assert room.enforce_human_verdict_gate("random_user") is False
    # Human judge Priya holds exclusive role
    assert room.enforce_human_verdict_gate("Priya") is False
    assert room.enforce_human_verdict_gate(human) is True

def test_live_agent_broadcast_workflow(human):
    room = SwitchRoom("test-court")
    mgr = CaseManager()

    clerk = CourtClerkAgent(room, mgr)
    historian = IncidentHistorianAgent(room, mgr)
    prosecutor = ProsecutorAgent(room, mgr)
    defender = DefenderAgent(room, mgr)
    rollback = RollbackEngineerAgent(room, mgr)

    room.subscribe(clerk.on_message)
    room.subscribe(historian.on_message)
    room.subscribe(prosecutor.on_message)
    room.subscribe(defender.on_message)
    room.subscribe(rollback.on_message)

    # Developer opens case
    room.post_message("Developer", "@court-clerk open case https://github.com/acme/shop/pull/482")

    assert clerk.current_case is not None
    assert clerk.current_case.case_id == "SC-0482"
    assert len(clerk.current_case.objections) > 0
    assert len(clerk.current_case.defenses) > 0
    assert clerk.current_case.rollback_plan is not None

    # Test unauthorized verdict
    room.post_message("prosecutor", "@court-clerk verdict APPROVE")
    assert "SECURITY VIOLATION" in room.messages[-1].content

    # Human Release Judge issues CONDITIONS
    room.post_message("Priya", "@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback", principal=human)
    assert clerk.current_case.verdict.type == VerdictType.CONDITIONS
    assert len(room.tasks) == 3
    assert len(room.decisions) == 1
    assert "Release Brief" in room.messages[-1].content

def test_gate_with_handles_and_aliases():
    room = SwitchRoom("test-court")
    assert room.enforce_human_verdict_gate("@Priya") is False
    assert room.enforce_human_verdict_gate("priya") is False
    assert room.enforce_human_verdict_gate("Priya Nair") is False
    assert room.enforce_human_verdict_gate("judge") is False
    assert room.enforce_human_verdict_gate("human-judge") is False
    assert room.enforce_human_verdict_gate("@clerk") is False
    assert room.enforce_human_verdict_gate("@rollback") is False
    assert room.enforce_human_verdict_gate("bot-service") is False

def test_natural_verdict_in_room_workflow(human):
    room = SwitchRoom("test-court")
    mgr = CaseManager()
    clerk = CourtClerkAgent(room, mgr)
    historian = IncidentHistorianAgent(room, mgr)
    prosecutor = ProsecutorAgent(room, mgr)
    defender = DefenderAgent(room, mgr)
    rollback = RollbackEngineerAgent(room, mgr)

    room.subscribe(clerk.on_message)
    room.subscribe(historian.on_message)
    room.subscribe(prosecutor.on_message)
    room.subscribe(defender.on_message)
    room.subscribe(rollback.on_message)

    # Open case
    room.post_message("Developer", "@clerk open case https://github.com/acme/shop/pull/482")
    assert clerk.current_case is not None

    # Check that Clerk invitation is in room
    invitation = [m.content for m in room.messages if "AWAITING HUMAN VERDICT" in m.content]
    assert len(invitation) > 0

    # Human sends flexible natural verdict command with @handle
    room.post_message("@Priya", "@clerk conditions: add pricing-mismatch alert; canary 5%; Priya owns rollback", principal=human)

    # Verify verdict acknowledged and recorded
    assert clerk.current_case.verdict is not None
    assert clerk.current_case.verdict.type == VerdictType.CONDITIONS
    assert len(room.decisions) == 1
    assert any("Verdict received from @Priya" in m.content for m in room.messages)

