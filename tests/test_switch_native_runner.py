"""Unit tests for Switch Native Courtroom Runner."""
from server.switch_native_runner import SwitchNativeCourtroom


def test_switch_native_runner_execution():
    runner = SwitchNativeCourtroom(room_name="ship-court-test")
    result = runner.run_case(
        case_id="SC-0482",
        change_summary="Test checkout dynamic pricing",
        repo="acme/shop",
        pr_number=482,
        requested_by="Priya",
    )
    assert result["status"] == "COMPLETED"
    assert result["case_id"] == "SC-0482"
    assert result["sessions_count"] == 5
    assert result["messages_count"] >= 1
    assert "SHIP WITH CONDITIONS" in result["verdict_result"]
