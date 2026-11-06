"""Multi-Agent Teammate Collaboration Demo.

Demonstrates how two Antigravity agents (Teammate A: Frontend, Teammate B: Backend)
collaborate on the same project without colliding, overwriting, or stepping outside
their assigned scopes.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from scope_guard.approval_handler import ApprovalHandler
from scope_guard.assignment_client import AssignmentClient
from scope_guard.coordinator_adapter import CoordinatorClient
from scope_guard.event_reporter import EventReporter
from scope_guard.mock_coordinator import MockCoordinatorServer
from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import (
    ActionRequest,
    Assignment,
    DecisionCategory,
    OwnershipRecord,
    TaskStatus,
)
from scope_guard.violation_detector import ViolationDetector


def print_header(title: str) -> None:
    print(f"\n{'='*75}")
    print(f"  {title}")
    print(f"{'='*75}")


def main() -> None:
    demo_dir = tempfile.mkdtemp(prefix="multi_agent_demo_")
    ws_a = os.path.join(demo_dir, "teammate_a_frontend")
    ws_b = os.path.join(demo_dir, "teammate_b_backend")
    os.makedirs(ws_a, exist_ok=True)
    os.makedirs(ws_b, exist_ok=True)

    try:
        print_header("MULTI-AGENT TEAMMATE COLLABORATION DEMONSTRATION")
        print("Architecture: 2 Developers / Antigravity Agents + 1 Central Coordinator")
        print("  - Teammate A: 'frontend-agent' working on Login & Auth UI")
        print("  - Teammate B: 'backend-agent'  working on Auth API & Database models")

        # 1. Central Coordinator with assignments
        mock_server = MockCoordinatorServer(port=0)

        assign_a = Assignment(
            agent_id="frontend-agent",
            task_id="TASK-UI-101",
            task_description="Implement login and registration UI components",
            allowed_paths=["frontend/src/auth/**"],
            restricted_paths=["backend/**", "database/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="backend/**",
                    owner_agent_id="backend-agent",
                    description="Teammate B's Backend API Service",
                )
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
        )

        assign_b = Assignment(
            agent_id="backend-agent",
            task_id="TASK-API-202",
            task_description="Implement authentication API, JWT verification, and database models",
            allowed_paths=["backend/src/auth/**", "database/**"],
            restricted_paths=["frontend/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="frontend/**",
                    owner_agent_id="frontend-agent",
                    description="Teammate A's Frontend UI",
                )
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
        )

        mock_server.assignments["frontend-agent"] = assign_a
        mock_server.assignments["backend-agent"] = assign_b

        # 2. Scope Guard for Teammate A (Frontend)
        client_a = AssignmentClient(agent_id="frontend-agent", cache_dir=os.path.join(ws_a, ".scope_guard"))
        client_a.save_local(assign_a)
        engine_a = ScopePolicyEngine(assignment=assign_a, workspace_root=ws_a)
        detector_a = ViolationDetector(assignment=assign_a)

        # 3. Scope Guard for Teammate B (Backend)
        client_b = AssignmentClient(agent_id="backend-agent", cache_dir=os.path.join(ws_b, ".scope_guard"))
        client_b.save_local(assign_b)
        engine_b = ScopePolicyEngine(assignment=assign_b, workspace_root=ws_b)
        detector_b = ViolationDetector(assignment=assign_b)

        # ---------------------------------------------------------------------
        # Turn 1: Normal In-Scope Work
        # ---------------------------------------------------------------------
        print_header("TURN 1: Both Teammates Work Safely in Their Assigned Scopes")

        action_a1 = ActionRequest(tool_name="edit_file", tool_args={"Path": "frontend/src/auth/Login.jsx"})
        dec_a1 = engine_a.evaluate(action_a1)
        print(f"[Teammate A] edit_file 'frontend/src/auth/Login.jsx' -> [{dec_a1.decision.value}]")
        print(f"             Reason: {dec_a1.reason}")
        assert dec_a1.decision == DecisionCategory.ALLOW

        action_b1 = ActionRequest(tool_name="edit_file", tool_args={"Path": "backend/src/auth/routes.py"})
        dec_b1 = engine_b.evaluate(action_b1)
        print(f"[Teammate B] edit_file 'backend/src/auth/routes.py' -> [{dec_b1.decision.value}]")
        print(f"             Reason: {dec_b1.reason}")
        assert dec_b1.decision == DecisionCategory.ALLOW

        # ---------------------------------------------------------------------
        # Turn 2: Collision Prevention (Teammate A tries to touch Teammate B's file)
        # ---------------------------------------------------------------------
        print_header("TURN 2: Teammate A Accidentally Attempts to Edit Teammate B's Backend File")

        action_a2 = ActionRequest(tool_name="edit_file", tool_args={"Path": "backend/src/auth/routes.py"})
        dec_a2 = engine_a.evaluate(action_a2)
        print(f"[Teammate A] edit_file 'backend/src/auth/routes.py' -> [{dec_a2.decision.value}]")
        print("\n--- Guard Interception on Teammate A's Antigravity ---")
        print(dec_a2.explanation)
        assert dec_a2.decision == DecisionCategory.BLOCK
        assert dec_a2.owner == "backend-agent"

        # ---------------------------------------------------------------------
        # Turn 3: Collision Prevention (Teammate B tries to touch Teammate A's file)
        # ---------------------------------------------------------------------
        print_header("TURN 3: Teammate B Tries to Modify Teammate A's Frontend UI")

        action_b2 = ActionRequest(tool_name="edit_file", tool_args={"Path": "frontend/src/auth/Login.jsx"})
        dec_b2 = engine_b.evaluate(action_b2)
        print(f"[Teammate B] edit_file 'frontend/src/auth/Login.jsx' -> [{dec_b2.decision.value}]")
        print("\n--- Guard Interception on Teammate B's Antigravity ---")
        print(dec_b2.explanation)
        assert dec_b2.decision == DecisionCategory.BLOCK
        assert dec_b2.owner == "frontend-agent"

        # ---------------------------------------------------------------------
        # Turn 4: Controlled Scope Expansion via Coordinator Approval
        # ---------------------------------------------------------------------
        print_header("TURN 4: Teammate A Requests Authorized Scope Update for Shared Contract")
        coord_client_a = CoordinatorClient(base_url="http://mock-coordinator", transport=mock_server.as_transport())
        approval_a = ApprovalHandler(assignment_client=client_a, policy_engine=engine_a, coordinator_client=coord_client_a)

        appr_req = approval_a.create_request(
            attempted_action="edit_file backend/src/auth/shared_contract.json",
            target_path="backend/src/auth/shared_contract.json",
            reason="Coordinate shared API schema format between frontend and backend",
            requested_paths=["backend/src/auth/shared_contract.json"],
        )
        print(f"Submitted Request: {appr_req.request_id} for path '{appr_req.target_path}'")
        resp = approval_a.submit_and_wait(appr_req)
        print(f"Coordinator Response: [{resp.status.value}] by {resp.approved_by}")
        print(f"Teammate A Scope updated to Version {engine_a.assignment.assignment_version}!")

        # Re-attempt shared contract file
        action_a_shared = ActionRequest(tool_name="edit_file", tool_args={"Path": "backend/src/auth/shared_contract.json"})
        dec_shared = engine_a.evaluate(action_a_shared)
        print(f"\n[Teammate A] edit_file 'backend/src/auth/shared_contract.json' after approval -> [{dec_shared.decision.value}]")
        assert dec_shared.decision == DecisionCategory.ALLOW

        # But core backend files are STILL protected!
        dec_still_blocked = engine_a.evaluate(action_a2)
        print(f"[Teammate A] edit_file 'backend/src/auth/routes.py' is STILL -> [{dec_still_blocked.decision.value}]")
        assert dec_still_blocked.decision == DecisionCategory.BLOCK

        print_header("MULTI-AGENT TEST COMPLETED SUCCESSFULLY — ZERO CONFLICTS DETECTED")

    finally:
        shutil.rmtree(demo_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
