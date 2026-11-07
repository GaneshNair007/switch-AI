from __future__ import annotations
from dataclasses import dataclass, field
import fnmatch
import uuid
from pathlib import PurePosixPath
import time
from typing import Any, Dict, List, Optional
from .bridge_connector import ChatBridgeConnector
from .models import Case, Objection, ObjectionSeverity
from .switch_room import SwitchRoom


@dataclass
class TeammateScopeAssignment:
    teammate_id: str
    agent_name: str
    allowed_globs: List[str]
    owned_services: List[str]
    machine_location: str = "workstation-local"


@dataclass
class AntigravityToolAttempt:
    teammate_id: str
    tool_name: str
    target_path: str
    diff_summary: str
    repository: str = "GaneshNair007/switch-AI"
    pr_url: str = "PR-18"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SubpoenaNotice:
    subpoena_id: str
    case_id: str
    violating_teammate: str
    colliding_with_teammate: Optional[str]
    target_path: str
    impacted_services: List[str]
    reason: str
    blocked_pre_tool_use: bool


class AntigravitySubpoenaBridge:
    DEFAULT_TEAM_SCOPES: List[TeammateScopeAssignment] = [
        TeammateScopeAssignment(
            teammate_id="teammate-1-frontend",
            agent_name="antigravity-ui-agent",
            allowed_globs=["ui/*", "frontend/*", "docs/*"],
            owned_services=["notification-service"],
            machine_location="laptop-teammate-1",
        ),
        TeammateScopeAssignment(
            teammate_id="teammate-2-pricing",
            agent_name="antigravity-pricing-agent",
            allowed_globs=["services/pricing/*", "pricing/*"],
            owned_services=["pricing-engine"],
            machine_location="laptop-teammate-2",
        ),
        TeammateScopeAssignment(
            teammate_id="teammate-3-checkout",
            agent_name="antigravity-checkout-agent",
            allowed_globs=["services/checkout/*", "services/payment/*"],
            owned_services=["checkout-service", "payment-gateway"],
            machine_location="laptop-teammate-3",
        ),
    ]

    def __init__(
        self,
        room: SwitchRoom,
        bridge: Optional[ChatBridgeConnector] = None,
        assignments: Optional[List[TeammateScopeAssignment]] = None,
    ):
        self.room = room
        self.bridge = bridge
        self.assignments: Dict[str, TeammateScopeAssignment] = {
            a.teammate_id: a for a in (assignments or self.DEFAULT_TEAM_SCOPES)
        }
        self.subpoenas: List[SubpoenaNotice] = []
        self.room.register_session(
            agent_name="shipcourt-antigravity-guard",
            alias="antigravity-guard",
            location="multi-teammate-hook-daemon",
            provider="antigravity",
        )

    def _matches_any(self, path: str, globs: List[str]) -> bool:
        norm = path.replace("\\", "/")
        if not norm or PurePosixPath(norm).is_absolute() or ":" in norm or ".." in PurePosixPath(norm).parts:
            return False
        while norm.startswith("./"):
            norm = norm[2:]
        return any(fnmatch.fnmatch(norm, g) for g in globs)

    def _find_owner_of_path(self, path: str, exclude_teammate: str) -> Optional[TeammateScopeAssignment]:
        for tid, assign in self.assignments.items():
            if tid == exclude_teammate:
                continue
            if self._matches_any(path, assign.allowed_globs):
                return assign
        return None

    def inspect_pre_tool_use(
        self, attempt: AntigravityToolAttempt, case_registry: Optional[Dict[str, Case]] = None
    ) -> Dict[str, Any]:
        assignment = self.assignments.get(attempt.teammate_id)
        if assignment and self._matches_any(attempt.target_path, assignment.allowed_globs) and not self._find_owner_of_path(attempt.target_path, attempt.teammate_id):
            msg = (
                f"✅ [Antigravity Scope Guard] Permitted `{attempt.tool_name}` by "
                f"`{attempt.teammate_id}` on in-scope file `{attempt.target_path}`."
            )
            self.room.post_message("antigravity-guard", msg, sender_role="antigravity-guard")
            return {"allowed": True, "subpoena": None, "case": None}

        colliding_owner = self._find_owner_of_path(attempt.target_path, attempt.teammate_id)
        colliding_id = colliding_owner.teammate_id if colliding_owner else "shared-core-infra"
        impacted_services = list(
            set(
                (assignment.owned_services if assignment else ["pricing-engine"])
                + (colliding_owner.owned_services if colliding_owner else ["checkout-service"])
            )
        )

        subpoena_id = f"SUBPOENA-{uuid.uuid4().hex}"
        case_id = f"CASE-AG-{uuid.uuid4().hex}"
        reason = (
            f"Teammate `{attempt.teammate_id}` attempted `{attempt.tool_name}` on out-of-scope file "
            f"`{attempt.target_path}` (owned by `{colliding_id}`). Diff: {attempt.diff_summary}"
        )

        notice = SubpoenaNotice(
            subpoena_id=subpoena_id,
            case_id=case_id,
            violating_teammate=attempt.teammate_id,
            colliding_with_teammate=colliding_id,
            target_path=attempt.target_path,
            impacted_services=sorted(impacted_services),
            reason=reason,
            blocked_pre_tool_use=True,
        )
        self.subpoenas.append(notice)

        new_case = Case(
            case_id=case_id,
            pr_url=attempt.pr_url,
            repository=attempt.repository,
            affected_services=sorted(impacted_services),
            ci_status="PENDING_COURTROOM_TRIAL",
            change_summary=f"[Antigravity Collision] {attempt.diff_summary} ({attempt.target_path})",
            objections=[
                Objection(
                    id=f"OBJ-{subpoena_id}",
                    claim=f"Cross-teammate scope boundary violation on `{attempt.target_path}`",
                    evidence=reason,
                    classification=ObjectionSeverity.BLOCKING,
                )
            ],
        )
        if case_registry is not None:
            case_registry[case_id] = new_case

        alert_text = (
            f"🛰️ **[AUTO-SUBPOENA {subpoena_id}]** Scope policy rejected `{attempt.tool_name}` "
            f"by `{attempt.teammate_id}` on `{attempt.target_path}` (collides with `{colliding_id}`). "
            f"Summoning 3-AI Ship Court under Case `{case_id}`!"
        )
        self.room.post_message("antigravity-guard", alert_text, sender_role="antigravity-guard")
        if self.bridge:
            self.bridge.forward_to_chat(alert_text)
        return {"allowed": False, "subpoena": notice, "case": new_case}
