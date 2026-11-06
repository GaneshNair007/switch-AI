"""Unit tests for Antigravity Hook Handler (PreToolUse contract)."""

import json
import os
import shutil
import tempfile
import unittest

from scope_guard.antigravity.hook_handler import process_hook_input
from scope_guard.assignment_client import AssignmentClient
from scope_guard.schema import Assignment, OwnershipRecord, TaskStatus


class TestAntigravityHooks(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace_root = os.path.join(self.test_dir, "workspace")
        os.makedirs(self.workspace_root, exist_ok=True)

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

        client = AssignmentClient(
            agent_id="frontend-agent",
            cache_dir=os.path.join(self.workspace_root, ".scope_guard"),
        )
        client.save_local(self.assignment)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_hook_allows_permitted_file(self):
        payload = {
            "toolCall": {
                "name": "edit_file",
                "args": {"Path": "frontend/App.jsx"},
            },
            "stepIdx": 1,
            "conversationId": "conv-123",
            "workspacePaths": [self.workspace_root],
        }

        output = process_hook_input(payload, workspace_root=self.workspace_root)
        self.assertEqual(output.get("decision"), "allow")

    def test_hook_denies_restricted_file(self):
        payload = {
            "toolCall": {
                "name": "edit_file",
                "args": {"Path": "backend/server.py"},
            },
            "stepIdx": 2,
            "conversationId": "conv-123",
            "workspacePaths": [self.workspace_root],
        }

        output = process_hook_input(payload, workspace_root=self.workspace_root)
        self.assertEqual(output.get("decision"), "deny")
        self.assertIn("BLOCKED:", output.get("reason", ""))
        self.assertIn("backend-agent", output.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
