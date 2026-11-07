from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Dict, List, Optional
from .bridge_connector import ChatBridgeConnector
from .models import Case, Verdict, VerdictType
from .parallel_earth import EarthSimulationReport
from .switch_room import SwitchRoom


@dataclass
class GitHubOperationRecord:
    op_id: str
    op_type: str
    repository: str
    target_ref: str
    actor: str
    authorized_by_human: str
    labels_applied: List[str] = field(default_factory=list)
    created_issues: List[str] = field(default_factory=list)
    rollback_branch: Optional[str] = None
    mode: str = "SIMULATED — NO EXTERNAL GITHUB CHANGE"
    timestamp: float = field(default_factory=time.time)


class GitHubOpsAgent:
    VERDICT_LABEL_MAP: Dict[VerdictType, str] = {
        VerdictType.APPROVE: "ship-court:approved",
        VerdictType.CONDITIONS: "ship-court:conditional",
        VerdictType.BLOCK: "ship-court:blocked",
    }

    def __init__(self, room: SwitchRoom, bridge: Optional[ChatBridgeConnector] = None, ledger_path: Optional[Path] = None):
        self.room = room
        self.bridge = bridge
        self.ledger_path = ledger_path or Path("data/github_ops_ledger.json")
        self.operations: List[GitHubOperationRecord] = []
        self.room.register_session("shipcourt-github-ops", "github-ops", "github-actions-bridge", "claude")

    def execute_post_verdict_github_ops(
        self,
        case: Case,
        verdict: Verdict,
        human_approver: str,
        earth_report: Optional[EarthSimulationReport] = None,
        pr_number: int = 18,
    ) -> GitHubOperationRecord:
        if not self.room.enforce_human_verdict_gate(human_approver, scope=f"case:{case.case_id}:github"):
            raise PermissionError(f"GitHubOpsAgent blocked: `{human_approver}` is not an authorized human approver.")
        labels = [self.VERDICT_LABEL_MAP[verdict.type], "antigravity:scope-checked"]
        if earth_report and earth_report.auto_rollback_verified:
            labels.append("parallel-earth:verified")
        created_issues = [f"[ShipCourt Condition {c.id}] {c.description[:60]}" for c in verdict.conditions]
        rollback_branch = f"rollback/{case.case_id.lower()}" if verdict.type != VerdictType.APPROVE else None
        op_id = f"GH-OP-{len(self.operations) + 1:03d}"
        record = GitHubOperationRecord(
            op_id=op_id,
            op_type=f"PR_GOVERNANCE_{verdict.type.value}",
            repository=case.repository,
            target_ref=f"PR #{pr_number}",
            actor="github-ops",
            authorized_by_human=human_approver,
            labels_applied=labels,
            created_issues=created_issues,
            rollback_branch=rollback_branch,
        )
        self.operations.append(record)
        msg = f"🐙 **[GITHUB OPS {op_id}]** SIMULATED — NO EXTERNAL GITHUB CHANGE. Proposed labels `{labels}`, {len(created_issues)} condition issues, rollback branch `{rollback_branch}`."
        self.room.post_message("github-ops", msg, sender_role="github-ops")
        if self.bridge:
            self.bridge.forward_to_chat(msg)
        return record
