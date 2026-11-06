"""Unit tests for Scope Guard schemas and data structures."""

import unittest
from scope_guard.schema import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    Assignment,
    DecisionCategory,
    OwnershipRecord,
    PolicyDecision,
    SeverityLevel,
    TaskStatus,
    ViolationCategory,
    ViolationEvent,
)


class TestSchemas(unittest.TestCase):
    def test_assignment_serialization(self):
        assignment = Assignment(
            agent_id="frontend-agent",
            task_id="task-101",
            task_description="Implement login UI",
            allowed_paths=["frontend/src/auth/**"],
            restricted_paths=["backend/**", "database/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="backend/src/auth/**",
                    owner_agent_id="backend-agent",
                    description="Auth API",
                )
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
            prohibited_operations=["delete"],
        )

        json_str = assignment.to_json()
        restored = Assignment.from_json(json_str)

        self.assertEqual(restored.agent_id, "frontend-agent")
        self.assertEqual(restored.task_id, "task-101")
        self.assertEqual(restored.allowed_paths, ["frontend/src/auth/**"])
        self.assertEqual(len(restored.ownership_info), 1)
        self.assertEqual(restored.ownership_info[0].owner_agent_id, "backend-agent")
        self.assertEqual(restored.assignment_version, 1)

    def test_violation_event_serialization(self):
        event = ViolationEvent(
            event_id="evt-12345",
            agent_id="frontend-agent",
            task_id="task-101",
            timestamp="2026-11-06T00:00:00Z",
            attempted_tool="edit_file",
            target_path="backend/src/auth/login.py",
            violation_category=ViolationCategory.OUT_OF_SCOPE_MODIFICATION,
            severity=SeverityLevel.HIGH,
            decision_taken=DecisionCategory.BLOCK,
            explanation="BLOCKED: OUT-OF-SCOPE MODIFICATION",
            assignment_version=1,
            raw_details={"line": 42},
        )

        d = event.to_dict()
        restored = ViolationEvent.from_dict(d)
        self.assertEqual(restored.event_id, "evt-12345")
        self.assertEqual(restored.violation_category, ViolationCategory.OUT_OF_SCOPE_MODIFICATION)
        self.assertEqual(restored.decision_taken, DecisionCategory.BLOCK)


if __name__ == "__main__":
    unittest.main()
