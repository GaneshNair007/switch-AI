"""Approval Handler for Antigravity Agent Scope Guard.

Handles structured approval requests for out-of-scope modifications,
processes authorized coordinator decisions, and updates local policy.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from scope_guard.assignment_client import AssignmentClient
from scope_guard.coordinator_adapter import CoordinatorClient
from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    Assignment,
)

logger = logging.getLogger("scope_guard.approval_handler")


class ApprovalHandler:
    """Manages the lifecycle of scope expansion approvals."""

    def __init__(
        self,
        assignment_client: AssignmentClient,
        policy_engine: ScopePolicyEngine,
        coordinator_client: Optional[CoordinatorClient] = None,
    ):
        self.assignment_client = assignment_client
        self.policy_engine = policy_engine
        self.coordinator = coordinator_client

    def create_request(
        self,
        attempted_action: str,
        target_path: str,
        reason: str,
        requested_paths: Optional[List[str]] = None,
    ) -> ApprovalRequest:
        """Constructs an approval request for out-of-scope work."""
        current_assignment = self.policy_engine.assignment
        req = ApprovalRequest(
            request_id=f"appr-{uuid.uuid4().hex[:8]}",
            agent_id=current_assignment.agent_id,
            task_id=current_assignment.task_id,
            attempted_action=attempted_action,
            target_path=target_path,
            reason=reason,
            current_version=current_assignment.assignment_version,
            requested_paths=requested_paths or [target_path],
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ApprovalStatus.PENDING,
        )
        return req

    def submit_and_wait(
        self,
        approval_req: ApprovalRequest,
    ) -> Optional[ApprovalResponse]:
        """Submits an approval request to the coordinator and evaluates the response."""
        if not self.coordinator:
            logger.warning("No coordinator configured to submit approval request.")
            return None

        response = self.coordinator.post_approval_request(approval_req)
        if response and response.status == ApprovalStatus.APPROVED:
            self.apply_approved_update(response)
        return response

    def apply_approved_update(self, response: ApprovalResponse) -> bool:
        """Applies an approved scope expansion to local policy and persistence."""
        if response.status != ApprovalStatus.APPROVED or not response.updated_assignment:
            logger.warning("Cannot apply scope update: response is not approved or lacks updated assignment.")
            return False

        updated = response.updated_assignment

        # Ensure assignment version was bumped
        if updated.assignment_version <= self.policy_engine.assignment.assignment_version:
            updated.assignment_version = self.policy_engine.assignment.assignment_version + 1

        # Save to local cache
        self.assignment_client.save_local(updated)

        # Update running policy engine
        self.policy_engine.update_assignment(updated)
        logger.info(
            f"Successfully applied scope update! New version: {updated.assignment_version}. "
            f"Allowed paths: {updated.allowed_paths}"
        )
        return True
