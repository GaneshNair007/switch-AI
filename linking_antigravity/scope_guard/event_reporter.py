"""Event Reporter for Antigravity Agent Scope Guard.

Buffers violation events locally and transmits them to the external coordinator.
Features offline resilience: retains events during network disruption and retries safely.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from scope_guard.coordinator_adapter import CoordinatorClient, CoordinatorNetworkError
from scope_guard.schema import ViolationEvent

logger = logging.getLogger("scope_guard.event_reporter")


class EventReporter:
    """Manages the persistence, buffering, and dispatch of violation events."""

    def __init__(
        self,
        coordinator_client: Optional[CoordinatorClient] = None,
        storage_dir: Optional[str] = None,
    ):
        self.coordinator = coordinator_client
        self.storage_dir = Path(storage_dir or os.path.join(os.getcwd(), ".scope_guard", "events"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.audit_log_path = self.storage_dir / "audit.jsonl"
        self.pending_path = self.storage_dir / "pending.jsonl"

    def report_event(self, event: ViolationEvent) -> bool:
        """Records an event locally and attempts transmission to coordinator.
        
        Guarantees that event is preserved locally even if coordinator is offline.
        """
        # 1. Append to local persistent audit log
        self._append_to_file(self.audit_log_path, event)

        # 2. If no coordinator configured, buffer into pending
        if not self.coordinator:
            self._append_to_file(self.pending_path, event)
            return False

        # 3. Attempt immediate dispatch to coordinator
        try:
            success = self.coordinator.post_violation(event)
            if success:
                logger.info(f"Dispatched violation event {event.event_id} to coordinator.")
                return True
            else:
                logger.warning(
                    f"Coordinator rejected event {event.event_id}. Retaining locally."
                )
                self._append_to_file(self.pending_path, event)
                return False
        except (CoordinatorNetworkError, Exception) as exc:
            logger.warning(
                f"Coordinator unavailable ({exc}). Retaining event {event.event_id} for retry."
            )
            self._append_to_file(self.pending_path, event)
            return False

    def get_pending_count(self) -> int:
        """Returns the number of events waiting in the offline queue."""
        if not self.pending_path.exists():
            return 0
        with open(self.pending_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def flush_pending_events(self) -> int:
        """Attempts to flush buffered events to coordinator when connectivity returns.
        
        Returns the number of successfully delivered events.
        """
        if not self.coordinator or not self.pending_path.exists():
            return 0

        pending_events: List[ViolationEvent] = []
        with open(self.pending_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        pending_events.append(ViolationEvent.from_dict(json.loads(line)))
                    except Exception as e:
                        logger.error(f"Failed to parse buffered event line: {e}")

        if not pending_events:
            return 0

        remaining: List[ViolationEvent] = []
        flushed_count = 0

        for event in pending_events:
            try:
                if self.coordinator.post_violation(event):
                    flushed_count += 1
                else:
                    remaining.append(event)
            except (CoordinatorNetworkError, Exception):
                # Coordinator still unreachable, retain remaining
                remaining.append(event)

        # Re-write pending file with only remaining un-sent events
        with open(self.pending_path, "w", encoding="utf-8") as f:
            for ev in remaining:
                f.write(json.dumps(ev.to_dict()) + "\n")

        return flushed_count

    def _append_to_file(self, file_path: Path, event: ViolationEvent) -> None:
        """Atomically appends JSON line to file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
