"""Google Antigravity SDK Integration Layer.

Provides policy factories and lifecycle hook decorators for Python SDK applications
using `google-antigravity`.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from scope_guard.policy_engine import ScopePolicyEngine
from scope_guard.schema import ActionRequest, Assignment, DecisionCategory, PolicyDecision

logger = logging.getLogger("scope_guard.sdk")


class ScopeGuardSDKIntegration:
    """Provides SDK policies and hooks for google-antigravity Agent configurations."""

    def __init__(
        self,
        assignment: Assignment,
        workspace_root: Optional[str] = None,
        on_violation: Optional[Callable[[PolicyDecision], None]] = None,
    ):
        self.assignment = assignment
        self.workspace_root = workspace_root
        self.policy_engine = ScopePolicyEngine(assignment=assignment, workspace_root=workspace_root)
        self.on_violation = on_violation

    def evaluate_tool_args(self, tool_name: str, args: Dict[str, Any]) -> PolicyDecision:
        """Evaluates a tool call from the SDK."""
        action = ActionRequest(
            tool_name=tool_name,
            tool_args=args,
            agent_id=self.assignment.agent_id,
            target_path=args.get("Path") or args.get("path") or args.get("file_path"),
            raw_command=args.get("CommandLine") or args.get("command"),
            workspace_root=self.workspace_root,
        )
        decision = self.policy_engine.evaluate(action)
        if decision.decision != DecisionCategory.ALLOW and self.on_violation:
            try:
                self.on_violation(decision)
            except Exception as e:
                logger.error(f"Error in on_violation callback: {e}")
        return decision

    def is_tool_call_denied(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Predicate helper for policy.deny()."""
        decision = self.evaluate_tool_args(tool_name, args)
        return decision.decision == DecisionCategory.BLOCK

    def is_tool_call_ask(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Predicate helper for policy.ask_user()."""
        decision = self.evaluate_tool_args(tool_name, args)
        return decision.decision == DecisionCategory.ASK

    def build_policies(self, policy_module: Any = None) -> List[Any]:
        """Constructs a list of `policy` objects compatible with SDK LocalAgentConfig.
        
        Args:
            policy_module: The `google.antigravity.hooks.policy` module (passed dynamically
                           or imported if available).
        """
        if policy_module is None:
            try:
                from google.antigravity.hooks import policy as policy_module
            except ImportError:
                raise ImportError(
                    "google-antigravity SDK is not installed. Pass policy_module explicitly or install google-antigravity."
                )

        policies = [
            # Deny out-of-scope write_file
            policy_module.deny(
                "write_file",
                when=lambda args: self.is_tool_call_denied("write_file", args),
                name="scope_guard_deny_write_file",
            ),
            # Deny out-of-scope edit_file
            policy_module.deny(
                "edit_file",
                when=lambda args: self.is_tool_call_denied("edit_file", args),
                name="scope_guard_deny_edit_file",
            ),
            # Deny out-of-scope create_file
            policy_module.deny(
                "create_file",
                when=lambda args: self.is_tool_call_denied("create_file", args),
                name="scope_guard_deny_create_file",
            ),
            # Deny out-of-scope or destructive run_command
            policy_module.deny(
                "run_command",
                when=lambda args: self.is_tool_call_denied("run_command", args),
                name="scope_guard_deny_run_command",
            ),
        ]
        return policies

    def create_pre_tool_call_hook(self) -> Callable:
        """Returns a hook function for SDK `@hooks.pre_tool_call_decide`."""
        async def scope_guard_decide(tool_call: Any) -> Any:
            tool_name = getattr(tool_call, "name", "")
            tool_args = getattr(tool_call, "args", {})
            decision = self.evaluate_tool_args(tool_name, tool_args)

            # Check if HookResult type is available
            try:
                from google.antigravity import types
                if decision.decision == DecisionCategory.BLOCK:
                    return types.HookResult(allow=False, reason=decision.explanation)
                elif decision.decision == DecisionCategory.ASK:
                    return types.HookResult(allow=False, reason=f"Confirmation required: {decision.explanation}")
                return types.HookResult(allow=True)
            except ImportError:
                # Mock representation for testing without SDK installed
                return {
                    "allow": decision.decision == DecisionCategory.ALLOW,
                    "reason": decision.explanation if decision.decision != DecisionCategory.ALLOW else None,
                }

        return scope_guard_decide
