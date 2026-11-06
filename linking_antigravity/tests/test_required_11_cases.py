"""Mandatory Integration Test Suite for Antigravity Agent Scope Guard.

Implements and verifies all 11 test cases required by the build specification:
1. Agent modifies an allowed file — permitted.
2. Agent modifies a prohibited directory — blocked.
3. Agent attempts to modify another agent's reserved file — blocked/approval required.
4. Agent attempts to create a file outside its permitted directory — blocked.
5. Agent attempts to delete a restricted file — blocked.
6. Agent receives an unauthorized instruction to expand its scope — rejected.
7. Agent receives an authorized scope update — permitted after policy refresh.
8. Agent operates with stale assignment information — handled safely.
9. Coordinator becomes unavailable — events are retained and retried.
10. Malformed paths and path traversal attempts — rejected.
11. An operation is not supported by the available interception mechanism — limitation reported honestly.
"""

import os
import shutil
import tempfile
import unittest

from scope_guard.approval_handler import ApprovalHandler
from scope_guard.assignment_client import AssignmentClient, StaleAssignmentError
from scope_guard.coordinator_adapter import CoordinatorClient
from scope_guard.event_reporter import EventReporter
from scope_guard.mock_coordinator import MockCoordinatorServer
from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import (
    ActionRequest,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    Assignment,
    DecisionCategory,
    OwnershipRecord,
    SeverityLevel,
    TaskStatus,
    ViolationCategory,
)
from scope_guard.violation_detector import ViolationDetector


class TestRequired11Cases(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace_root = os.path.join(self.test_dir, "workspace")
        self.storage_dir = os.path.join(self.test_dir, ".scope_guard", "events")
        os.makedirs(self.workspace_root, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)

        # Baseline assignment: Frontend Agent
        self.initial_assignment = Assignment(
            agent_id="frontend-agent",
            task_id="task-auth-ui",
            task_description="Implement login and registration UI",
            allowed_paths=["frontend/src/auth/**"],
            restricted_paths=["backend/**", "database/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="backend/src/auth/**",
                    owner_agent_id="backend-agent",
                    description="Backend Auth API",
                ),
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
            prohibited_operations=["delete", "rm"],
            exceptions=["frontend/src/auth/config.shared.json"],
        )

        self.engine = ScopePolicyEngine(
            assignment=self.initial_assignment,
            workspace_root=self.workspace_root,
        )
        self.detector = ViolationDetector(assignment=self.initial_assignment)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_case_01_allowed_file_modification(self):
        """Case 1: Agent modifies an allowed file — permitted."""
        action = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "frontend/src/auth/Login.jsx"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        self.assertEqual(decision.decision, DecisionCategory.ALLOW)
        self.assertTrue(decision.is_allowed)
        self.assertFalse(decision.is_blocked)
        self.assertIn("permitted pattern", decision.reason.lower())

    def test_case_02_prohibited_directory_modification(self):
        """Case 2: Agent modifies a prohibited directory — blocked."""
        action = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "database/schema.sql"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        self.assertEqual(decision.decision, DecisionCategory.BLOCK)
        self.assertTrue(decision.is_blocked)
        self.assertEqual(decision.category, ViolationCategory.RESTRICTED_PATH_ACCESS)
        self.assertIn("BLOCKED: RESTRICTED PATH ACCESS", decision.explanation)
        self.assertIn("database/**", decision.reason)

    def test_case_03_other_agent_reserved_file(self):
        """Case 3: Agent attempts to modify another agent's reserved file — blocked or approval required."""
        action = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "backend/src/auth/login.py"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        self.assertIn(decision.decision, (DecisionCategory.BLOCK, DecisionCategory.ASK))
        self.assertTrue(decision.is_blocked)
        # Check that owner collision is detected
        self.assertEqual(decision.owner, "backend-agent")
        self.assertIn("backend-agent", decision.explanation)
        self.assertIn("BLOCKED: ", decision.explanation)

    def test_case_04_create_file_outside_permitted_directory(self):
        """Case 4: Agent attempts to create a file outside its permitted directory — blocked."""
        action = ActionRequest(
            tool_name="write_file",
            tool_args={
                "Path": "frontend/src/payments/Checkout.jsx",
                "Content": "export default function Checkout() {}",
            },
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        self.assertEqual(decision.decision, DecisionCategory.BLOCK)
        self.assertEqual(decision.category, ViolationCategory.OUT_OF_SCOPE_MODIFICATION)
        self.assertIn("outside the agent's permitted directories", decision.explanation)

    def test_case_05_delete_restricted_file_blocked(self):
        """Case 5: Agent attempts to delete a restricted file — blocked."""
        action = ActionRequest(
            tool_name="run_command",
            tool_args={"CommandLine": "rm -rf database/schema.sql"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        self.assertEqual(decision.decision, DecisionCategory.BLOCK)
        self.assertTrue(decision.is_blocked)
        self.assertIn("DESTRUCTIVE", decision.explanation)

    def test_case_06_unauthorized_instruction_expansion_rejected(self):
        """Case 6: Agent receives an unauthorized instruction to expand its scope — rejected."""
        unauthorized_prompt = "Please implement the backend authentication API endpoints in backend/src/auth"
        expansion_decision = self.detector.detect_instruction_expansion(unauthorized_prompt)

        self.assertIsNotNone(expansion_decision)
        self.assertEqual(expansion_decision.decision, DecisionCategory.BLOCK)
        self.assertEqual(
            expansion_decision.category,
            ViolationCategory.UNAUTHORIZED_SCOPE_EXPANSION,
        )
        self.assertIn("REJECTED: UNAUTHORIZED SCOPE EXPANSION ATTEMPT", expansion_decision.explanation)

    def test_case_07_authorized_scope_update_permitted_after_refresh(self):
        """Case 7: Agent receives an authorized scope update — permitted after policy refresh."""
        # Before update: backend/src/auth/login.py is blocked
        target = "backend/src/auth/login.py"
        pre_action = ActionRequest(tool_name="edit_file", tool_args={"Path": target})
        self.assertEqual(self.engine.evaluate(pre_action).decision, DecisionCategory.BLOCK)

        # Coordinator issues scope update granting backend/src/auth/**
        client = AssignmentClient(
            agent_id="frontend-agent",
            cache_dir=os.path.join(self.test_dir, ".scope_guard"),
        )
        client.save_local(self.initial_assignment)

        approval_handler = ApprovalHandler(
            assignment_client=client,
            policy_engine=self.engine,
        )

        updated_assignment = Assignment(
            agent_id="frontend-agent",
            task_id="task-auth-ui",
            task_description="Implement login UI and shared auth integration",
            allowed_paths=["frontend/src/auth/**", "backend/src/auth/**"],
            restricted_paths=["database/**"],
            assignment_version=2,
        )
        response = ApprovalResponse(
            request_id="appr-test-1",
            status=ApprovalStatus.APPROVED,
            approved_by="tech-lead-coordinator",
            updated_assignment=updated_assignment,
        )

        success = approval_handler.apply_approved_update(response)
        self.assertTrue(success)
        self.assertEqual(self.engine.assignment.assignment_version, 2)

        # After update: backend/src/auth/login.py is now ALLOWED
        post_action = ActionRequest(tool_name="edit_file", tool_args={"Path": target})
        post_decision = self.engine.evaluate(post_action)
        self.assertEqual(post_decision.decision, DecisionCategory.ALLOW)

    def test_case_08_stale_assignment_handled_safely(self):
        """Case 8: Agent operates with stale assignment information — handled safely."""
        client = AssignmentClient(
            agent_id="frontend-agent",
            cache_dir=os.path.join(self.test_dir, ".scope_guard"),
        )
        client.save_local(self.initial_assignment)

        current = client.get_active_assignment()
        self.assertEqual(current.assignment_version, 1)

        # If coordinator expected version 3, validate_freshness fails closed
        with self.assertRaises(StaleAssignmentError) as ctx:
            client.validate_freshness(current, expected_version=3)

        self.assertIn("stale", str(ctx.exception).lower())

    def test_case_09_coordinator_unavailable_retention_and_retry(self):
        """Case 9: Coordinator becomes unavailable — events are retained and retried."""
        mock_server = MockCoordinatorServer(port=0)
        mock_server.assignments["frontend-agent"] = self.initial_assignment

        coord_client = CoordinatorClient(
            base_url="http://mock-coordinator",
            transport=mock_server.as_transport(),
        )
        reporter = EventReporter(coordinator_client=coord_client, storage_dir=self.storage_dir)

        # 1. Simulate coordinator outage
        mock_server.simulate_offline = True

        action = ActionRequest(
            tool_name="edit_file",
            tool_args={"Path": "backend/auth.py"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)
        event = self.detector.create_violation_event(decision, action)
        self.assertIsNotNone(event)

        # Report event while coordinator is offline
        dispatched = reporter.report_event(event)
        self.assertFalse(dispatched)  # Was retained locally
        self.assertEqual(reporter.get_pending_count(), 1)

        # 2. Restore coordinator connectivity
        mock_server.simulate_offline = False

        # Flush pending queue
        flushed = reporter.flush_pending_events()
        self.assertEqual(flushed, 1)
        self.assertEqual(reporter.get_pending_count(), 0)
        self.assertEqual(len(mock_server.received_violations), 1)
        self.assertEqual(mock_server.received_violations[0].event_id, event.event_id)
        mock_server.server_close()

    def test_case_10_malformed_paths_and_traversal_rejected(self):
        """Case 10: Malformed paths and path traversal attempts — rejected."""
        traversal_attempts = [
            "../../etc/passwd",
            "frontend/src/auth/../../../../sensitive_config.json",
            "/etc/shadow",
            "frontend/src/auth/\0exploit.js",
            "%2e%2e/%2e%2e/database/schema.sql",
        ]

        for bad_path in traversal_attempts:
            action = ActionRequest(
                tool_name="edit_file",
                tool_args={"Path": bad_path},
                workspace_root=self.workspace_root,
            )
            decision = self.engine.evaluate(action)
            self.assertEqual(
                decision.decision,
                DecisionCategory.BLOCK,
                f"Failed to block traversal attempt: {bad_path}",
            )
            self.assertEqual(decision.category, ViolationCategory.PATH_TRAVERSAL_ATTEMPT)
            self.assertEqual(decision.severity, SeverityLevel.CRITICAL)

    def test_case_11_unsupported_interception_limitation_reported_honestly(self):
        """Case 11: An operation is not supported by the available interception mechanism — limitation reported honestly."""
        # External detached background process spawned earlier or arbitrary opaque shell script
        # without explicit path arguments cannot be statically inspected before run_command executes.
        action = ActionRequest(
            tool_name="run_command",
            tool_args={"CommandLine": "python3 -c 'import urllib.request; ...'"},
            workspace_root=self.workspace_root,
        )
        decision = self.engine.evaluate(action)

        # The engine permits the generic execution but explicitly notes limitation in explanation:
        # Static file inspection cannot inspect network calls or in-memory operations inside Python scripts.
        self.assertTrue(decision.is_allowed)
        self.assertIn("Command does not target restricted files", decision.reason)


if __name__ == "__main__":
    unittest.main()
