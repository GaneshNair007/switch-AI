"""Unit tests for Google Opal Workflow Bridge for Switch AI."""
from server.opal_workflow import GoogleOpalWorkflowBridge


def test_opal_manifest_export():
    bridge = GoogleOpalWorkflowBridge()
    manifest = bridge.export_opal_manifest()
    assert manifest["schema_version"] == "opal.google.labs/v1"
    assert manifest["workflow"]["id"] == "opal-ship-court-gate"
    assert len(manifest["workflow"]["nodes"]) == 7
    # Verify human gate node
    gate_node = next(n for n in manifest["workflow"]["nodes"] if n["step_type"] == "human_gate")
    assert gate_node["requires_human_approval"] is True
    assert gate_node["agent_alias"] == "@judge"


def test_opal_workflow_execution():
    bridge = GoogleOpalWorkflowBridge()
    result = bridge.execute_workflow(
        pr_url="https://github.com/acme/shop/pull/482",
        judge_name="Priya",
        canary_percent=5.0,
    )
    assert result["status"] == "AWAITING_AUTHENTICATED_HUMAN"
    assert result["case_id"] == "SC-0482"
    assert result["verdict"] is None
    assert len(result["execution_steps"]) == 6
    assert result["brief_published"] is False
    assert result["switch_room"] == "#ship-court"

