from __future__ import annotations
from typing import Any, Dict, Optional
from .antigravity_subpoena import AntigravitySubpoenaBridge, AntigravityToolAttempt
from .bridge_connector import ChatBridgeConnector
from .dependency_graph import DependencyGraph
from .floor_controller import FloorRequestController
from .github_ops_agent import GitHubOpsAgent
from .models import (
    Case,
    CaseState,
    Defense,
    Objection,
    ObjectionSeverity,
    ObjectionStatus,
    Verdict,
    VerdictType,
)
from .parallel_earth import ParallelEarthSimulator
from .switch_room import SwitchRoom


class UnifiedBoardroomCourtPipeline:
    """Orchestrates the 5-ring flowchart: Antigravity -> Third Voice -> 3-AI Courtroom -> Parallel Earth -> GitHub Ops."""

    def __init__(self, room_name: str = "ship-court", webhook_url: Optional[str] = None):
        self.room = SwitchRoom(room_name=room_name, bridge="discord")
        self.bridge = ChatBridgeConnector(self.room, webhook_url=webhook_url, platform="discord")
        self.graph = DependencyGraph()
        self.cases: Dict[str, Case] = {}

        self.room.register_session("shipcourt-clerk", "clerk", "server-node", "claude")
        self.room.register_session("shipcourt-historian", "historian", "server-node", "claude")
        self.room.register_session("shipcourt-prosecutor", "prosecutor", "server-node", "claude")
        self.room.register_session("shipcourt-defender", "defender", "local-workstation", "codex")
        self.room.register_session("shipcourt-rollback", "rollback", "server-node", "opencode")

        self.subpoena_bridge = AntigravitySubpoenaBridge(self.room, bridge=self.bridge)
        self.parallel_earth = ParallelEarthSimulator(self.room, graph=self.graph, bridge=self.bridge)
        self.floor_controller = FloorRequestController(self.room, bridge=self.bridge)
        self.github_ops = GitHubOpsAgent(self.room, bridge=self.bridge)

    def execute_full_flowchart_run(self, human_approver: str = "Priya") -> Dict[str, Any]:
        attempt = AntigravityToolAttempt(
            teammate_id="teammate-2-pricing",
            tool_name="EditFile",
            target_path="services/checkout/dynamic_surge_multiplier.py",
            diff_summary="Added unthrottled surge multiplier calling payment-gateway synchronously",
        )
        hook_result = self.subpoena_bridge.inspect_pre_tool_use(attempt, self.cases)
        case: Case = hook_result["case"]

        floor_req = self.floor_controller.raise_hand(
            meeting_id="boardroom-huddle-042",
            agent_id="third-voice",
            emoji="⚠️",
            reason="Teammate-2 synchronous payment call contradicts Decision #DEC-014.",
            spoken_script="Hold on team—Teammate 2 modified checkout with a synchronous payment call.",
            priority=90,
            evidence_refs=["DEC-014", "INC-2025-112", case.case_id],
        )
        floor_grant = self.floor_controller.grant_floor(floor_req.request_id, human_actor=human_approver)

        case.state = CaseState.OBJECTIONS_RAISED
        prosecutor_obj = Objection(
            id=f"OBJ-{case.case_id}-2",
            claim="Synchronous call in checkout path risks Tier-1 SLA breach.",
            evidence="Historical incident INC-2025-112 match.",
            classification=ObjectionSeverity.WARNING,
        )
        case.objections.append(prosecutor_obj)
        self.bridge.forward_to_chat(prosecutor_obj.claim, agent_role="prosecutor")

        case.state = CaseState.DEFENSE_RESPONSE
        defense = Defense(
            objection_id=prosecutor_obj.id,
            claim="Circuit breaker wraps pricing lookup with 150ms fallback cache.",
            evidence="Unit test passes in local worktree.",
            is_conceded=False,
        )
        case.defenses.append(defense)
        prosecutor_obj.status = ObjectionStatus.MITIGATED
        self.bridge.forward_to_chat(defense.claim, agent_role="defender")

        earth_report = self.parallel_earth.run_simulation(case, estimated_downtime_minutes=15.0)
        case.state = CaseState.AWAITING_VERDICT

        verdict = Verdict(
            judge=human_approver,
            type=VerdictType.CONDITIONAL,
            reason="Approved with Parallel Earth canary guardrails.",
            conditions=earth_report.recommended_conditions,
        )
        case.verdict = verdict
        case.state = CaseState.CASE_CLOSED
        self.room.record_decision(case.case_id, verdict)

        gh_record = self.github_ops.execute_post_verdict_github_ops(
            case=case,
            verdict=verdict,
            human_approver=human_approver,
            earth_report=earth_report,
            pr_number=18,
        )
        return {
            "case": case,
            "subpoena": hook_result["subpoena"],
            "floor_grant": floor_grant,
            "earth_report": earth_report,
            "github_op": gh_record,
            "discord_payload_count": len(self.bridge.sent_payloads),
        }
