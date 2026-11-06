"""Violation Detector for Antigravity Agent Scope Guard.

Identifies, categorizes, and formats structured violation events from
policy decisions and unauthorized instructions.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scope_guard.schema import (
    ActionRequest,
    Assignment,
    DecisionCategory,
    PolicyDecision,
    SeverityLevel,
    ViolationCategory,
    ViolationEvent,
)


class ViolationDetector:
    """Detects and produces structured violation events for coordinator reporting."""

    def __init__(self, assignment: Assignment):
        self.assignment = assignment

    def create_violation_event(
        self,
        decision: PolicyDecision,
        action: ActionRequest,
        raw_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[ViolationEvent]:
        """Creates a structured ViolationEvent if the policy decision is not ALLOW."""
        if decision.decision == DecisionCategory.ALLOW:
            return None

        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        category = decision.category or ViolationCategory.OUT_OF_SCOPE_MODIFICATION
        severity = decision.severity

        details = dict(raw_details or {})
        details.update({
            "tool_name": action.tool_name,
            "tool_args": action.tool_args,
            "owner": decision.owner,
            "conversation_id": action.conversation_id,
            "step_idx": action.step_idx,
        })

        return ViolationEvent(
            event_id=event_id,
            agent_id=self.assignment.agent_id,
            task_id=self.assignment.task_id,
            timestamp=timestamp,
            attempted_tool=action.tool_name,
            target_path=decision.target_path or action.target_path,
            violation_category=category,
            severity=severity,
            decision_taken=decision.decision,
            explanation=decision.explanation,
            assignment_version=self.assignment.assignment_version,
            raw_details=details,
        )

    def detect_instruction_expansion(
        self, prompt_text: str
    ) -> Optional[PolicyDecision]:
        """Detects whether an incoming user/orchestrator prompt attempts unauthorized scope expansion.
        
        For example, if a frontend-agent receives an instruction to:
        "Implement the backend authentication API" or "Modify database schema".
        """
        prompt_lower = prompt_text.lower()

        # Check if prompt explicitly asks for tasks outside assigned scope
        for rest in self.assignment.restricted_paths:
            base_dir = rest.split("/")[0].rstrip("*")
            if base_dir and re.search(rf"\b(?:implement|build|create|modify|update|write)\s+.*?\b{base_dir}\b", prompt_lower):
                explanation = (
                    f"REJECTED: UNAUTHORIZED SCOPE EXPANSION ATTEMPT\n"
                    f"Agent: {self.assignment.agent_id}\n"
                    f"Instruction received: '{prompt_text.strip()}'\n"
                    f"Assigned responsibility: {self.assignment.task_description}\n"
                    f"Reason: Instruction requests modifications in restricted domain '{base_dir}'.\n"
                    f"Action: Scope expansion rejected. Requires coordinator reassignment or authorized scope update."
                )
                return PolicyDecision(
                    decision=DecisionCategory.BLOCK,
                    category=ViolationCategory.UNAUTHORIZED_SCOPE_EXPANSION,
                    severity=SeverityLevel.HIGH,
                    reason=f"Prompt attempts scope expansion into restricted domain '{base_dir}'",
                    explanation=explanation,
                    agent_id=self.assignment.agent_id,
                    assignment_version=self.assignment.assignment_version,
                )

        return None
