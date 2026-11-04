"""Tests for VerdictParser: command parsing, task extraction, and release brief artifact."""
from server.verdict import VerdictParser
from server.models import Case, VerdictType, CaseState
from server.release_brief import ReleaseBriefGenerator

def test_parse_approve():
    v = VerdictParser.parse_command("@court-clerk verdict APPROVE", judge_name="Priya")
    assert v.type == VerdictType.APPROVE
    assert v.judge == "Priya"

def test_parse_block():
    v = VerdictParser.parse_command('@court-clerk verdict BLOCK reason="No rollback owner"', judge_name="Priya")
    assert v.type == VerdictType.BLOCK
    assert v.reason == "No rollback owner"

def test_parse_conditions_and_create_tasks():
    cmd = "@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback"
    v = VerdictParser.parse_command(cmd, judge_name="Priya")
    assert v.type == VerdictType.CONDITIONS
    assert len(v.conditions) == 3

    case = Case(
        case_id="SC-0482",
        pr_url="https://github.com/acme/shop/pull/482",
        repository="acme/shop",
        affected_services=["checkout-service"],
        ci_status="42 passed, 0 failed",
        deployment_target="production canary"
    )
    VerdictParser.apply_verdict(case, v)
    assert case.state == CaseState.CONDITIONAL
    assert len(case.tasks) == 3

    brief = ReleaseBriefGenerator.generate_markdown(case)
    assert "SHIP WITH CONDITIONS" in brief
    assert "SC-0482" in brief

