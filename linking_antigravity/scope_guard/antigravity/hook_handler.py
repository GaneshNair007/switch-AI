"""Native Antigravity Hook Handler.

Consumes the stdin/stdout contract for Antigravity's PreToolUse lifecycle hook.
Validates tool actions before execution in Antigravity IDE and Antigravity CLI.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

from scope_guard.assignment_client import AssignmentClient
from scope_guard.coordinator_adapter import CoordinatorClient
from scope_guard.event_reporter import EventReporter
from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import (
    ActionRequest,
    DecisionCategory,
    PolicyDecision,
    SeverityLevel,
    ViolationCategory,
)
from scope_guard.violation_detector import ViolationDetector


def process_hook_input(
    input_data: Dict[str, Any],
    workspace_root: Optional[str] = None,
    storage_dir: Optional[str] = None,
    coordinator_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Processes a PreToolUse hook payload and returns the decision output dictionary."""
    tool_call = input_data.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("args", {})
    step_idx = input_data.get("stepIdx")
    conversation_id = input_data.get("conversationId")

    # Determine workspace root from hook payload if available
    workspace_paths = input_data.get("workspacePaths", [])
    root = workspace_root or os.environ.get("SHIPCOURT_WORKSPACE_ROOT") or os.getcwd()

    # Initialize client and storage
    cache_dir = os.path.join(root, ".scope_guard")
    events_dir = os.path.join(cache_dir, "events")

    # 1. Load active assignment
    coordinator_url = coordinator_url or os.environ.get("SHIPCOURT_COORDINATOR_URL")
    coord_client = CoordinatorClient(base_url=coordinator_url, auth_token=os.environ.get("SHIPCOURT_HOOK_TOKEN")) if coordinator_url else None
    assign_client = AssignmentClient(agent_id=os.environ.get("SHIPCOURT_AGENT_ID", "current"), coordinator_client=coord_client, cache_dir=cache_dir)
    
    try:
        assignment = assign_client.get_active_assignment()
    except FileNotFoundError:
        # If no assignment has been set up, allow with warning or fail safe
        return {
            "decision": "deny",
            "reason": "Scope Guard: No active assignment configured. Human provisioning required.",
        }

    # 2. Build Policy Engine
    engine = ScopePolicyEngine(assignment=assignment, workspace_root=root)
    violation_detector = ViolationDetector(assignment=assignment)
    reporter = EventReporter(coordinator_client=coord_client, storage_dir=events_dir)

    # 3. Create Action Request
    target_path = tool_args.get("Path") or tool_args.get("path") or tool_args.get("file_path")
    raw_command = tool_args.get("CommandLine") or tool_args.get("command")

    action = ActionRequest(
        tool_name=tool_name,
        tool_args=tool_args,
        agent_id=assignment.agent_id,
        step_idx=step_idx,
        conversation_id=conversation_id,
        target_path=target_path,
        raw_command=raw_command,
        workspace_root=root,
    )

    # 4. Evaluate action
    decision = engine.evaluate(action)

    # 5. If violation detected, record and report
    if decision.decision != DecisionCategory.ALLOW:
        event = violation_detector.create_violation_event(
            decision=decision,
            action=action,
            raw_details={"hook_step": step_idx, "conversation_id": conversation_id},
        )
        if event:
            reporter.report_event(event)

    # 6. Map Scope Guard decision to Antigravity hook stdout contract
    # Antigravity hook supports: "allow", "deny", "ask", "force_ask"
    if decision.decision == DecisionCategory.BLOCK:
        return {
            "decision": "deny",
            "reason": decision.explanation,
        }
    elif decision.decision == DecisionCategory.ASK:
        return {
            "decision": "ask",
            "reason": decision.explanation,
        }
    elif decision.decision == DecisionCategory.WARN:
        return {
            "decision": "allow",
            "reason": f"WARNING: {decision.explanation}",
        }
    else:
        return {
            "decision": "allow",
        }


def main() -> None:
    """CLI entrypoint reading from stdin and writing to stdout."""
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            # Empty input, allow
            print(json.dumps({"decision": "deny", "reason": "Missing tool event"}))
            return

        payload = json.loads(raw_input)
        result = process_hook_input(payload)
        print(json.dumps(result))
    except Exception as exc:
        # Fail closed on internal security errors, but report explainable error
        err_response = {
            "decision": "deny",
            "reason": f"Scope Guard Internal Enforcement Error: {exc}",
        }
        print(json.dumps(err_response))
        sys.exit(0)


if __name__ == "__main__":
    main()
