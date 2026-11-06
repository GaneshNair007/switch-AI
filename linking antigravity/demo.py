"""Interactive End-to-End Demonstration for Antigravity Agent Scope Guard.

Demonstrates all key scenarios from the specification:
1. Permitting allowed task modifications.
2. Blocking out-of-scope modifications with explainable violation reports.
3. Detecting ownership collisions with other agents' reserved files.
4. Blocking access to restricted directories.
5. Detecting and thwarting path traversal attacks.
6. Rejecting unauthorized scope expansion prompts.
7. Handling coordinator approval and dynamic scope updates.
8. Offline event buffering and retry when coordinator is unavailable.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

from scope_guard.antigravity.rules_generator import RulesGenerator
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


def print_banner(title: str) -> None:
    print(f"\n{'='*75}")
    print(f"  {title}")
    print(f"{'='*75}")


def main() -> None:
    demo_dir = tempfile.mkdtemp(prefix="scope_guard_demo_")
    workspace_root = os.path.join(demo_dir, "workspace")
    storage_dir = os.path.join(workspace_root, ".scope_guard", "events")
    os.makedirs(workspace_root, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)

    try:
        print_banner("ANTIGRAVITY AGENT SCOPE GUARD — LIVE DEMONSTRATION")

        # Step 1: Initialize assignment for frontend-agent
        print("\n[STEP 1] Receiving & Establishing Agent Scope Assignment...")
        assignment = Assignment(
            agent_id="frontend-agent",
            task_id="TASK-AUTH-UI-101",
            task_description="Implement login and registration UI components",
            allowed_paths=["frontend/src/auth/**"],
            restricted_paths=["backend/**", "database/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="backend/src/auth/**",
                    owner_agent_id="backend-agent",
                    description="Backend Authentication API Service",
                )
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
            prohibited_operations=["delete", "rm"],
        )

        assign_client = AssignmentClient(
            agent_id=assignment.agent_id,
            cache_dir=os.path.join(workspace_root, ".scope_guard"),
        )
        assign_client.save_local(assignment)

        # Generate IDE/CLI rules file
        rule_path = RulesGenerator.write_workspace_rules(assignment, workspace_root=workspace_root)
        print(f"  ✓ Assignment registered for agent: {assignment.agent_id}")
        print(f"  ✓ Permitted paths: {assignment.allowed_paths}")
        print(f"  ✓ Restricted paths: {assignment.restricted_paths}")
        print(f"  ✓ Ownership records: backend/src/auth/** -> backend-agent")
        print(f"  ✓ Antigravity workspace rule generated: {rule_path}")

        # Initialize Scope Guard Engine
        engine = ScopePolicyEngine(assignment=assignment, workspace_root=workspace_root)
        detector = ViolationDetector(assignment=assignment)

        # Initialize Mock Coordinator
        mock_server = MockCoordinatorServer(port=0)
        mock_server.assignments[assignment.agent_id] = assignment
        coord_client = CoordinatorClient(
            base_url="http://mock-coordinator",
            transport=mock_server.as_transport(),
        )
        reporter = EventReporter(coordinator_client=coord_client, storage_dir=storage_dir)

        # -------------------------------------------------------------
        # Scenario A: Modify allowed file
        # -------------------------------------------------------------
        print_banner("SCENARIO A: Permitted Modification (Inside Scope)")
        action_a = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "frontend/src/auth/Login.jsx"},
            workspace_root=workspace_root,
        )
        decision_a = engine.evaluate(action_a)
        print(f"Agent:             {assignment.agent_id}")
        print(f"Attempted Tool:    edit_file")
        print(f"Target Path:       frontend/src/auth/Login.jsx")
        print(f"Decision:          [{decision_a.decision.value}] — {decision_a.reason}")
        assert decision_a.decision == DecisionCategory.ALLOW

        # -------------------------------------------------------------
        # Scenario B: Modify other agent's reserved file
        # -------------------------------------------------------------
        print_banner("SCENARIO B: Ownership Collision (Other Agent's Reserved File)")
        action_b = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "backend/src/auth/login.py"},
            workspace_root=workspace_root,
        )
        decision_b = engine.evaluate(action_b)
        print(f"Agent:             {assignment.agent_id}")
        print(f"Attempted Tool:    edit_file")
        print(f"Target Path:       backend/src/auth/login.py")
        print(f"Decision:          [{decision_b.decision.value}]")
        print(f"\n--- EXPLAINABLE VIOLATION OUTPUT ---")
        print(decision_b.explanation)
        assert decision_b.decision == DecisionCategory.BLOCK
        assert decision_b.owner == "backend-agent"

        # Record violation
        event_b = detector.create_violation_event(decision_b, action_b)
        reporter.report_event(event_b)
        print(f"\n  ✓ Structured Violation Event reported to coordinator: {event_b.event_id}")

        # -------------------------------------------------------------
        # Scenario C: Modify restricted database directory
        # -------------------------------------------------------------
        print_banner("SCENARIO C: Modification of Restricted Directory")
        action_c = ActionRequest(
            tool_name="write_file",
            tool_args={"Path": "database/schema.sql"},
            workspace_root=workspace_root,
        )
        decision_c = engine.evaluate(action_c)
        print(f"Target Path:       database/schema.sql")
        print(f"Decision:          [{decision_c.decision.value}]")
        print(f"\n--- EXPLAINABLE VIOLATION OUTPUT ---")
        print(decision_c.explanation)
        assert decision_c.decision == DecisionCategory.BLOCK

        # -------------------------------------------------------------
        # Scenario D: Path Traversal Attack
        # -------------------------------------------------------------
        print_banner("SCENARIO D: Path Traversal Attack Attempt")
        action_d = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "../../etc/shadow"},
            workspace_root=workspace_root,
        )
        decision_d = engine.evaluate(action_d)
        print(f"Target Path:       ../../etc/shadow")
        print(f"Decision:          [{decision_d.decision.value}] (Severity: {decision_d.severity.value})")
        print(f"\n--- EXPLAINABLE VIOLATION OUTPUT ---")
        print(decision_d.explanation)
        assert decision_d.decision == DecisionCategory.BLOCK

        # -------------------------------------------------------------
        # Scenario E: Unauthorized Scope Expansion Prompt
        # -------------------------------------------------------------
        print_banner("SCENARIO E: Unauthorized Scope Expansion Instruction")
        instruction = "Also implement the backend authentication endpoints and database tables"
        expansion_eval = detector.detect_instruction_expansion(instruction)
        print(f"Incoming Prompt:   '{instruction}'")
        print(f"Decision:          [{expansion_eval.decision.value}]")
        print(f"\n--- EXPLAINABLE VIOLATION OUTPUT ---")
        print(expansion_eval.explanation)
        assert expansion_eval.decision == DecisionCategory.BLOCK

        # -------------------------------------------------------------
        # Scenario F: Coordinator Approval & Dynamic Scope Update
        # -------------------------------------------------------------
        print_banner("SCENARIO F: Coordinator Approval & Dynamic Scope Update")
        approval_handler = ApprovalHandler(
            assignment_client=assign_client,
            policy_engine=engine,
            coordinator_client=coord_client,
        )

        appr_req = approval_handler.create_request(
            attempted_action="edit_file backend/src/auth/login.py",
            target_path="backend/src/auth/login.py",
            reason="Need to add shared token validation header between UI and API",
            requested_paths=["backend/src/auth/**"],
        )
        print(f"Approval Request created: {appr_req.request_id}")
        print(f"  Target: {appr_req.target_path}")
        print(f"  Reason: {appr_req.reason}")

        # Submitting to coordinator
        appr_resp = approval_handler.submit_and_wait(appr_req)
        print(f"\nCoordinator Decision Received:")
        print(f"  Status:       {appr_resp.status.value}")
        print(f"  Approved By:  {appr_resp.approved_by}")
        print(f"  New Version:  {engine.assignment.assignment_version}")
        print(f"  Allowed:      {engine.assignment.allowed_paths}")

        # Re-attempt previously blocked action
        print("\nRe-evaluating 'edit_file backend/src/auth/login.py' after scope update...")
        post_update_decision = engine.evaluate(action_b)
        print(f"Decision:          [{post_update_decision.decision.value}] — {post_update_decision.reason}")
        assert post_update_decision.decision == DecisionCategory.ALLOW

        # -------------------------------------------------------------
        # Scenario G: Coordinator Offline Resilience & Event Spooling
        # -------------------------------------------------------------
        print_banner("SCENARIO G: Offline Resilience (Coordinator Unavailable)")
        mock_server.simulate_offline = True
        print("  ! Simulating coordinator network outage (503 Service Unavailable)...")

        action_offline = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "database/migrations/001.sql"},
            workspace_root=workspace_root,
        )
        dec_off = engine.evaluate(action_offline)
        ev_off = detector.create_violation_event(dec_off, action_offline)

        dispatched = reporter.report_event(ev_off)
        print(f"  Attempted immediate dispatch: {dispatched} (Successfully buffered offline)")
        print(f"  Pending offline events in queue: {reporter.get_pending_count()}")

        print("\n  ! Restoring coordinator connectivity...")
        mock_server.simulate_offline = False
        flushed_count = reporter.flush_pending_events()
        print(f"  Flushed events to coordinator: {flushed_count}")
        print(f"  Remaining in pending queue:     {reporter.get_pending_count()}")
        assert reporter.get_pending_count() == 0

        print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY — ALL GUARD CHECKS VERIFIED")

    finally:
        shutil.rmtree(demo_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
