from __future__ import annotations
import pytest
from server.antigravity_subpoena import AntigravitySubpoenaBridge, AntigravityToolAttempt
from server.bridge_connector import ChatBridgeConnector
from server.floor_controller import FloorRequestController, FloorState
from server.github_ops_agent import GitHubOpsAgent
from server.models import Case, Verdict, VerdictType
from server.parallel_earth import ParallelEarthSimulator
from server.switch_room import SwitchRoom
from server.unified_pipeline import UnifiedBoardroomCourtPipeline


def test_superpowers_1_to_5_and_unified_pipeline():
    pipeline = UnifiedBoardroomCourtPipeline()
    result = pipeline.execute_full_flowchart_run(human_approver="Priya")
    assert result["case"].state.value == "CASE_CLOSED"
    assert result["subpoena"].blocked_pre_tool_use is True
    assert result["floor_grant"]["granted"] is True
    assert result["earth_report"].auto_rollback_verified is True
    assert "ship-court:conditional" in result["github_op"].labels_applied
    assert "parallel-earth:verified" in result["github_op"].labels_applied
    assert result["discord_payload_count"] >= 5
