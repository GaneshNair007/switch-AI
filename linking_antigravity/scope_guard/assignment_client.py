"""Assignment Client for Antigravity Agent Scope Guard.

Loads, caches, validates, and refreshes the agent's active assignment.
Handles coordinator connectivity, local offline caching, and staleness detection.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from scope_guard.coordinator_adapter import CoordinatorClient, CoordinatorNetworkError
from scope_guard.schema import Assignment, TaskStatus

logger = logging.getLogger("scope_guard.assignment_client")


class StaleAssignmentError(Exception):
    """Raised when an operation is attempted with an outdated assignment."""
    pass


class AssignmentClient:
    """Manages agent assignment lifecycle and local caching."""

    def __init__(
        self,
        agent_id: str,
        coordinator_client: Optional[CoordinatorClient] = None,
        cache_dir: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.coordinator = coordinator_client
        self.cache_dir = Path(cache_dir or os.path.join(os.getcwd(), ".scope_guard"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "current_assignment.json"

    def get_active_assignment(self) -> Assignment:
        """Retrieves the active assignment from coordinator or local cache."""
        # Try fetching from coordinator if available
        if self.coordinator:
            try:
                remote_assignment = self.coordinator.get_assignment(self.agent_id)
                if remote_assignment:
                    self.save_local(remote_assignment)
                    return remote_assignment
            except CoordinatorNetworkError as exc:
                logger.warning(
                    f"Coordinator unreachable ({exc}). Falling back to cached assignment."
                )

        # Fallback to local cache
        cached = self.load_local()
        if cached:
            return cached

        raise FileNotFoundError(
            f"No assignment found locally at '{self.cache_file}' or from coordinator."
        )

    def refresh(self) -> Assignment:
        """Forces a refresh from the coordinator."""
        if not self.coordinator:
            raise RuntimeError("Cannot refresh: coordinator client not configured.")

        remote = self.coordinator.get_assignment(self.agent_id)
        if not remote:
            raise RuntimeError(f"Coordinator returned no assignment for agent '{self.agent_id}'.")

        self.save_local(remote)
        return remote

    def load_local(self) -> Optional[Assignment]:
        """Loads assignment from local cache file."""
        if not self.cache_file.exists():
            return None
        with open(self.cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Assignment.from_dict(data)

    def save_local(self, assignment: Assignment) -> None:
        """Persists assignment to local cache file."""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            f.write(assignment.to_json(indent=2))

    def validate_freshness(self, current_assignment: Assignment, expected_version: int) -> bool:
        """Checks if current assignment satisfies expected version requirements."""
        if current_assignment.assignment_version < expected_version:
            raise StaleAssignmentError(
                f"Assignment version {current_assignment.assignment_version} is stale (expected >= {expected_version})."
            )
        return True
