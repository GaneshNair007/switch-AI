"""Switch Native Courtroom Runner.
Direct execution of Ship Court integrated with Switch Console environment,
binding the courtroom state machine to Switch Core template models and room events.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.switch_room import SwitchRoom
from server.case_manager import CaseManager
from server.agent_runners import (
    CourtClerkAgent,
    IncidentHistorianAgent,
    ProsecutorAgent,
    DefenderAgent,
    RollbackEngineerAgent,
)

logger = logging.getLogger("switch-native-runner")


class SwitchNativeCourtroom:
    """Orchestrates Ship Court cases natively with Switch Console runtime hooks."""

    def __init__(self, room_name: str = "ship-court", template_path: Optional[str] = None):
        self.room_name = room_name
        self.template_path = Path(template_path or PROJECT_ROOT / "switch" / "ship-court.template.yaml")
        self.has_switch_core = self._check_switch_core()
        self.room = SwitchRoom(room_name=self.room_name, bridge="mattermost")
        self.manager = CaseManager()
        self._setup_agents()

    def _check_switch_core(self) -> bool:
        """Check if SandboxAQ switch_core is importable in current Python environment."""
        try:
            import switch_core  # type: ignore # noqa: F401
            return True
        except ImportError:
            return False

    def _setup_agents(self):
        """Register agent sessions and listeners."""
        self.room.register_session("court-clerk", "clerk", "host_server", "claude")
        self.room.register_session("incident-historian", "historian", "host_server", "claude")
        self.room.register_session("prosecutor", "prosecutor", "host_server", "claude")
        self.room.register_session("defender", "defender", "local_machine", "claude")
        self.room.register_session("rollback-engineer", "rollback", "local_machine", "claude")

        clerk = CourtClerkAgent(self.room, self.manager)
        historian = IncidentHistorianAgent(self.room, self.manager)
        prosecutor = ProsecutorAgent(self.room, self.manager)
        defender = DefenderAgent(self.room, self.manager)
        rollback = RollbackEngineerAgent(self.room, self.manager)

        self.room.subscribe(clerk.on_message)
        self.room.subscribe(historian.on_message)
        self.room.subscribe(prosecutor.on_message)
        self.room.subscribe(defender.on_message)
        self.room.subscribe(rollback.on_message)

    def run_case(
        self,
        case_id: str = "SC-0482",
        change_summary: str = "Dynamic checkout pricing",
        repo: str = "acme/shop",
        pr_number: int = 482,
        requested_by: str = "Priya",
        verdict_text: str = "CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback",
    ) -> Dict[str, Any]:
        """Execute a full courtroom session from case opening to human verdict."""
        # 1. Clerk opens case
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
        case = self.manager.open_case(pr_url=pr_url, custom_case_id=case_id)
        self.room.post_message(
            sender="court-clerk",
            content=f"CASE OPENED: #{pr_number} ({repo}) by {requested_by}. Change: {change_summary}. ID: {case_id}",
        )

        # 2. Run procedural pipeline
        pipeline_res = self.manager.run_procedural_pipeline(case_id=case_id, rollback_owner=requested_by)

        return {
            "status": "AWAITING_AUTHENTICATED_HUMAN",
            "mode": "LOCAL_PROCEDURAL_SIMULATION",
            "case_id": case_id,
            "switch_core_importable": self.has_switch_core,
            "switch_native_verified": False,
            "messages_count": len(self.room.messages),
            "sessions_count": len(self.room.sessions),
            "has_brief": False,
        }


def main():
    parser = argparse.ArgumentParser(description="Switch Native Courtroom Runner")
    parser.add_argument("--case-id", default="SC-0482", help="Case identifier")
    parser.add_argument("--repo", default="acme/shop", help="Repository slug")
    parser.add_argument("--pr", type=int, default=482, help="Pull request number")
    parser.add_argument("--requester", default="Priya", help="Deploy requester")
    parser.add_argument("--output", help="Optional output path for Release Brief markdown")
    args = parser.parse_args()

    courtroom = SwitchNativeCourtroom()
    result = courtroom.run_case(
        case_id=args.case_id,
        repo=args.repo,
        pr_number=args.pr,
        requested_by=args.requester,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
