"""CLI for Antigravity Agent Scope Guard.

Provides commands for hook execution, assignment initialization, status inspection,
action checking, and event flushing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from scope_guard.antigravity.hook_handler import process_hook_input
from scope_guard.antigravity.rules_generator import RulesGenerator
from scope_guard.assignment_client import AssignmentClient
from scope_guard.coordinator_adapter import CoordinatorClient
from scope_guard.event_reporter import EventReporter
from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import (
    ActionRequest,
    Assignment,
    DecisionCategory,
    OwnershipRecord,
    TaskStatus,
)


def cmd_hook(args: argparse.Namespace) -> None:
    """Invoked by Antigravity PreToolUse hook (reads stdin, outputs stdout)."""
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        result = process_hook_input(
            payload,
            workspace_root=args.workspace,
            coordinator_url=args.coordinator,
        )
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"decision": "deny", "reason": f"Scope Guard Hook Error: {exc}"}))


def cmd_init(args: argparse.Namespace) -> None:
    """Initializes a new assignment and sets up workspace rules."""
    root = os.path.abspath(args.workspace or os.getcwd())
    cache_dir = os.path.join(root, ".scope_guard")
    client = AssignmentClient(agent_id=args.agent_id, cache_dir=cache_dir)

    ownership = []
    if args.ownership:
        for own_str in args.ownership:
            # Format: "pattern:owner_id"
            if ":" in own_str:
                pat, own_id = own_str.split(":", 1)
                ownership.append(OwnershipRecord(path_pattern=pat.strip(), owner_agent_id=own_id.strip()))

    assignment = Assignment(
        agent_id=args.agent_id,
        task_id=args.task_id,
        task_description=args.description or "Assigned task",
        allowed_paths=args.allow or [],
        restricted_paths=args.restrict or [],
        ownership_info=ownership,
        prohibited_operations=args.prohibit or [],
        assignment_version=1,
    )

    client.save_local(assignment)
    rule_path = RulesGenerator.write_workspace_rules(assignment, workspace_root=root)

    print(f"Scope Guard initialized successfully for agent '{assignment.agent_id}'.")
    print(f"Assignment cached at: {client.cache_file}")
    print(f"Workspace rules generated at: {rule_path}")


def cmd_status(args: argparse.Namespace) -> None:
    """Displays current assignment and scope status."""
    root = os.path.abspath(args.workspace or os.getcwd())
    cache_dir = os.path.join(root, ".scope_guard")
    client = AssignmentClient(agent_id="current", cache_dir=cache_dir)
    reporter = EventReporter(storage_dir=os.path.join(cache_dir, "events"))

    try:
        assignment = client.get_active_assignment()
        print("=== ANTIGRAVITY AGENT SCOPE GUARD STATUS ===")
        print(f"Agent ID:           {assignment.agent_id}")
        print(f"Task ID:            {assignment.task_id}")
        print(f"Task Description:   {assignment.task_description}")
        print(f"Assignment Version: {assignment.assignment_version}")
        print(f"Task Status:        {assignment.task_status.value}")
        print(f"Allowed Paths:      {', '.join(assignment.allowed_paths) or '(None)'}")
        print(f"Restricted Paths:   {', '.join(assignment.restricted_paths) or '(None)'}")
        print(f"Ownership Entries:  {len(assignment.ownership_info)}")
        for o in assignment.ownership_info:
            print(f"  - {o.path_pattern} -> {o.owner_agent_id}")
        print(f"Pending Events:     {reporter.get_pending_count()}")
    except FileNotFoundError:
        print("No active assignment found in workspace. Run 'scope-guard init' first.")


def cmd_check(args: argparse.Namespace) -> None:
    """Checks whether an attempted action would be allowed or blocked."""
    root = os.path.abspath(args.workspace or os.getcwd())
    cache_dir = os.path.join(root, ".scope_guard")
    client = AssignmentClient(agent_id="current", cache_dir=cache_dir)

    try:
        assignment = client.get_active_assignment()
    except FileNotFoundError:
        print("Error: No active assignment found.")
        sys.exit(1)

    engine = ScopePolicyEngine(assignment=assignment, workspace_root=root)
    action = ActionRequest(
        tool_name=args.tool,
        target_path=args.path,
        raw_command=args.command,
        workspace_root=root,
    )
    decision = engine.evaluate(action)

    print(f"Decision: {decision.decision.value}")
    print(f"Reason:   {decision.reason}")
    if decision.explanation:
        print("\nExplanation:")
        print(decision.explanation)


def cmd_flush(args: argparse.Namespace) -> None:
    """Flushes buffered events to the coordinator."""
    root = os.path.abspath(args.workspace or os.getcwd())
    cache_dir = os.path.join(root, ".scope_guard")
    coord = CoordinatorClient(base_url=args.coordinator)
    reporter = EventReporter(coordinator_client=coord, storage_dir=os.path.join(cache_dir, "events"))

    count = reporter.flush_pending_events()
    remaining = reporter.get_pending_count()
    print(f"Flushed {count} event(s) to coordinator. Remaining in queue: {remaining}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Agent Scope Guard CLI")
    parser.add_argument("--workspace", help="Workspace root path (default: cwd)")
    parser.add_argument("--coordinator", default="http://localhost:8080", help="Coordinator URL")

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # hook subcommand
    sub_hook = subparsers.add_parser("hook", help="Run PreToolUse hook (reads stdin)")
    sub_hook.set_defaults(func=cmd_hook)

    # init subcommand
    sub_init = subparsers.add_parser("init", help="Initialize assignment and rules")
    sub_init.add_argument("--agent-id", required=True, help="Agent identifier")
    sub_init.add_argument("--task-id", required=True, help="Task identifier")
    sub_init.add_argument("--description", help="Task description")
    sub_init.add_argument("--allow", action="append", help="Allowed path glob pattern")
    sub_init.add_argument("--restrict", action="append", help="Restricted path glob pattern")
    sub_init.add_argument("--ownership", action="append", help="Ownership mapping 'pattern:owner_id'")
    sub_init.add_argument("--prohibit", action="append", help="Prohibited operations (e.g. delete)")
    sub_init.set_defaults(func=cmd_init)

    # status subcommand
    sub_status = subparsers.add_parser("status", help="Show scope guard status")
    sub_status.set_defaults(func=cmd_status)

    # check subcommand
    sub_check = subparsers.add_parser("check", help="Check an action against policy")
    sub_check.add_argument("--tool", default="edit_file", help="Tool name")
    sub_check.add_argument("--path", help="Target file path")
    sub_check.add_argument("--command", help="Target shell command")
    sub_check.set_defaults(func=cmd_check)

    # flush subcommand
    sub_flush = subparsers.add_parser("flush", help="Flush buffered events to coordinator")
    sub_flush.set_defaults(func=cmd_flush)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
