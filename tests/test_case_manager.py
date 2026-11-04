"""Tests for CaseManager: intake, bounded rounds, and security boundaries."""
import pytest
from server.case_manager import CaseManager
from server.models import CaseState

def test_case_intake():
    mgr = CaseManager()
    case = mgr.open_case("https://github.com/acme/shop/pull/482")
    assert case.case_id.startswith("SC-")
    assert case.repository == "acme/shop"
    assert case.state == CaseState.CASE_OPENED

def test_pipeline_bounded_execution():
    mgr = CaseManager()
    case = mgr.open_case("https://github.com/acme/shop/pull/482", custom_case_id="SC-0482")
    result = mgr.run_procedural_pipeline("SC-0482", rollback_owner="Priya")
    assert result["round_count"] == 4
    assert result["state"] == CaseState.AWAITING_VERDICT.value
    assert len(case.objections) <= 3
    assert len(case.defenses) == len(case.objections)
    assert case.rollback_plan is not None

def test_prevent_non_human_verdict():
    mgr = CaseManager()
    case = mgr.open_case("https://github.com/acme/shop/pull/482", custom_case_id="SC-0482")
    mgr.run_procedural_pipeline("SC-0482")
    with pytest.raises(PermissionError, match="Security violation"):
        mgr.record_verdict("SC-0482", "@court-clerk verdict APPROVE", is_human=False)

