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

def test_natural_command_variations():
    # 1. Direct approve without @court-clerk
    v1 = VerdictParser.parse_command("@clerk approve", judge_name="Priya")
    assert v1.type == VerdictType.APPROVE

    v2 = VerdictParser.parse_command("APPROVE", judge_name="Priya")
    assert v2.type == VerdictType.APPROVE

    v3 = VerdictParser.parse_command("@court-clerk: ship", judge_name="Priya")
    assert v3.type == VerdictType.APPROVE

    # 2. Block variations
    v4 = VerdictParser.parse_command("@court-clerk block because no rollback owner", judge_name="Priya")
    assert v4.type == VerdictType.BLOCK
    assert "no rollback owner" in v4.reason.lower()

    v5 = VerdictParser.parse_command("@clerk block: unmonitored pricing drift", judge_name="Priya")
    assert v5.type == VerdictType.BLOCK
    assert "pricing drift" in v5.reason.lower()

    # 3. Conditions variations
    v6 = VerdictParser.parse_command(
        "@clerk conditions: add pricing-mismatch alert; canary 5%; Priya owns rollback",
        judge_name="Priya"
    )
    assert v6.type == VerdictType.CONDITIONS
    assert len(v6.conditions) == 3
    assert any("alert" in c.description.lower() for c in v6.conditions)
    assert any(c.owner == "DevOps" for c in v6.conditions)
    assert any("canary" in c.description.lower() for c in v6.conditions)

