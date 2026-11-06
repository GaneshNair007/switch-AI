"""Unit tests for Antigravity SDK Integration."""

import unittest
from scope_guard.antigravity.sdk_integration import ScopeGuardSDKIntegration
from scope_guard.schema import Assignment, OwnershipRecord, TaskStatus


class MockPolicyModule:
    """Mock representing google.antigravity.hooks.policy."""
    @staticmethod
    def deny(tool_name, when=None, name=None):
        return {"action": "deny", "tool": tool_name, "when": when, "name": name}

    @staticmethod
    def ask_user(tool_name, when=None, handler=None):
        return {"action": "ask_user", "tool": tool_name, "when": when, "handler": handler}

    @staticmethod
    def allow(tool_name, when=None, name=None):
        return {"action": "allow", "tool": tool_name, "when": when, "name": name}


class TestSDKIntegration(unittest.TestCase):
    def setUp(self):
        self.assignment = Assignment(
            agent_id="frontend-agent",
            task_id="task-1",
            task_description="Frontend UI",
            allowed_paths=["frontend/**"],
            restricted_paths=["backend/**"],
            ownership_info=[
                OwnershipRecord(
                    path_pattern="backend/**",
                    owner_agent_id="backend-agent",
                )
            ],
            task_status=TaskStatus.IN_PROGRESS,
            assignment_version=1,
        )
        self.sdk_helper = ScopeGuardSDKIntegration(assignment=self.assignment)

    def test_build_policies(self):
        policies = self.sdk_helper.build_policies(policy_module=MockPolicyModule)
        self.assertEqual(len(policies), 4)

        # Check write_file deny predicate
        write_file_policy = next(p for p in policies if p["name"] == "scope_guard_deny_write_file")
        when_fn = write_file_policy["when"]

        # Should deny backend modification
        self.assertTrue(when_fn({"Path": "backend/auth.py"}))
        # Should NOT deny frontend modification
        self.assertFalse(when_fn({"Path": "frontend/App.jsx"}))


if __name__ == "__main__":
    unittest.main()
