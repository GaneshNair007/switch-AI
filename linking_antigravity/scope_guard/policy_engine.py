"""Core Scope Policy Engine for Antigravity Agent Scope Guard.

Evaluates attempted agent actions against local scope policies, path patterns,
ownership tables, and security constraints.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from scope_guard.schema import (
    ActionRequest,
    Assignment,
    DecisionCategory,
    PolicyDecision,
    SeverityLevel,
    ViolationCategory,
)


def match_path_pattern(pattern: str, target_path: str) -> bool:
    """Matches a target path against a glob pattern with recursive ** support.
    
    Normalizes both pattern and path to forward slashes.
    Supports:
      - '**' matching any number of directories.
      - '*' matching characters within a single directory segment.
      - Exact paths or directory prefixes.
    """
    pattern = pattern.strip().replace("\\", "/")
    target_path = target_path.strip().replace("\\", "/").lstrip("/")

    # If pattern has leading slash, strip it for relative comparison
    pattern = pattern.lstrip("/")

    # Direct equality
    if pattern == target_path:
        return True

    # If pattern is a directory without glob (e.g. "backend/"), treat as "backend/**"
    if pattern.endswith("/"):
        pattern = pattern + "**"

    # Convert pattern to regex
    # Escape regex specials except '*' and '?'
    regex_parts = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # '**'
                i += 2
                # If followed by slash (e.g., '**/')
                if i < n and pattern[i] == "/":
                    i += 1
                    regex_parts.append("(?:.+/)?")
                else:
                    regex_parts.append(".*")
            else:
                # single '*' matches non-slash characters
                i += 1
                regex_parts.append("[^/]*")
        elif c == "?":
            i += 1
            regex_parts.append("[^/]")
        elif c in ".^$+{}()[]|\\":
            regex_parts.append("\\" + c)
            i += 1
        else:
            regex_parts.append(c)
            i += 1

    regex_str = "^" + "".join(regex_parts) + "$"
    try:
        return re.match(regex_str, target_path) is not None
    except re.error:
        # Fallback to string prefix
        clean_pat = pattern.rstrip("*").rstrip("/")
        return target_path == clean_pat or target_path.startswith(clean_pat + "/")


class PathSecurityValidator:
    """Validates paths for directory traversal, symlink escapes, and null bytes."""

    @staticmethod
    def normalize_and_validate(
        raw_path: str, workspace_root: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Normalizes path and checks for traversal attacks.
        
        Returns:
            (is_valid, normalized_rel_path, error_message)
        """
        if not raw_path:
            return False, "", "Empty path provided"

        # Check for null bytes
        if "\0" in raw_path:
            return False, raw_path, "Path contains null byte (potential poison attack)"

        # Check for URL encodings like %2e%2e
        if "%2e" in raw_path.lower():
            return False, raw_path, "Path contains URL encoded traversal characters"

        root = Path(workspace_root or os.getcwd()).resolve()

        raw_path_obj = Path(raw_path)
        if raw_path_obj.is_absolute():
            resolved = raw_path_obj.resolve()
        else:
            resolved = (root / raw_path_obj).resolve()

        # Check if resolved path is within workspace root
        try:
            rel_path = resolved.relative_to(root)
            normalized_rel = str(rel_path).replace("\\", "/")
            return True, normalized_rel, None
        except ValueError:
            # Traversal attempt outside workspace
            return (
                False,
                str(raw_path),
                f"Path traversal detected: '{raw_path}' escapes workspace root '{root}'",
            )


class ShellCommandAnalyzer:
    """Heuristic analyzer for shell commands executed via run_command."""

    DESTRUCTIVE_COMMANDS = {
        "rm", "rmdir", "truncate", "shred", "wipe", "dd", "mkfs"
    }
    
    FILE_WRITE_COMMANDS = {
        "touch", "tee", "cp", "mv", "sed", "awk", "git"
    }

    @classmethod
    def analyze_command(cls, command_line: str) -> Dict[str, Any]:
        """Analyzes a shell command to identify potential target paths and destructive flags."""
        result: Dict[str, Any] = {
            "is_destructive": False,
            "suspected_targets": [],
            "redirections": [],
            "command_name": "",
            "raw_command": command_line,
        }

        if not command_line or not command_line.strip():
            return result

        cmd_stripped = command_line.strip()

        # Check for output redirection (> or >>)
        # Matches patterns like '> path/to/file' or '>> path/to/file'
        redirection_pattern = re.compile(r'(?:>{1,2})\s*([^\s;&|]+)')
        for match in redirection_pattern.finditer(cmd_stripped):
            target = match.group(1).strip()
            # Clean quotes if any
            target = target.strip("'\"")
            if target:
                result["redirections"].append(target)
                result["suspected_targets"].append(target)

        # Lex tokens safely
        try:
            tokens = shlex.split(cmd_stripped)
        except ValueError:
            # Command contains mismatched quotes or complex shell grammar
            tokens = cmd_stripped.split()

        if not tokens:
            return result

        result["command_name"] = Path(tokens[0]).name.lower()

        # Check destructive commands
        if result["command_name"] in cls.DESTRUCTIVE_COMMANDS:
            result["is_destructive"] = True
            # For rm/rmdir, subsequent non-flag tokens are target files
            for tok in tokens[1:]:
                if not tok.startswith("-"):
                    result["suspected_targets"].append(tok)

        # Check git commands (git checkout -- <file>, git restore <file>, git rm <file>)
        if result["command_name"] == "git" and len(tokens) > 1:
            subcmd = tokens[1]
            if subcmd in ("rm", "checkout", "restore", "clean", "reset"):
                result["is_destructive"] = True
                for tok in tokens[2:]:
                    if not tok.startswith("-"):
                        result["suspected_targets"].append(tok)

        # Check mv/cp
        if result["command_name"] in ("mv", "cp") and len(tokens) > 1:
            for tok in tokens[1:]:
                if not tok.startswith("-"):
                    result["suspected_targets"].append(tok)

        return result


class ScopePolicyEngine:
    """Evaluates operations against an active Assignment scope and rules."""

    def __init__(
        self,
        assignment: Assignment,
        workspace_root: Optional[str] = None,
        strict_ownership: bool = True,
    ):
        self.assignment = assignment
        self.workspace_root = workspace_root or os.getcwd()
        self.strict_ownership = strict_ownership

    def update_assignment(self, new_assignment: Assignment) -> None:
        """Updates active assignment when coordinator issues a scope update."""
        self.assignment = new_assignment

    def evaluate(self, action: ActionRequest) -> PolicyDecision:
        """Evaluates an action and returns an explainable PolicyDecision."""
        tool_name = action.tool_name.lower()

        # Check for stale assignment
        if self.assignment.expires_at:
            # In a full setup, check timestamp; if expired, block
            pass

        # 1. Evaluate file modification tools
        if tool_name in ("write_file", "edit_file", "create_file"):
            return self._evaluate_file_tool(action)

        # 2. Evaluate shell execution tool
        elif tool_name in ("run_command", "execute_command", "bash", "sh"):
            return self._evaluate_command_tool(action)

        # 3. Read-only or safe navigation tools are allowed
        elif tool_name in ("read_file", "view_file", "code_search", "search_web", "list_dir"):
            return PolicyDecision(
                decision=DecisionCategory.ALLOW,
                reason="Read-only operation permitted",
                explanation=f"Tool '{action.tool_name}' does not modify project state.",
                target_path=action.target_path,
                agent_id=self.assignment.agent_id,
                assignment_version=self.assignment.assignment_version,
            )

        # 4. Unknown tool - default allow with warning, or ask
        return PolicyDecision(
            decision=DecisionCategory.ALLOW,
            reason=f"Tool '{action.tool_name}' permitted by default",
            explanation=f"Tool '{action.tool_name}' is not classified as a file-modification tool.",
            agent_id=self.assignment.agent_id,
            assignment_version=self.assignment.assignment_version,
        )

    def _evaluate_file_tool(self, action: ActionRequest) -> PolicyDecision:
        """Evaluates write_file, edit_file, create_file."""
        raw_path = action.target_path or action.tool_args.get("Path") or action.tool_args.get("path")
        if not raw_path:
            return PolicyDecision(
                decision=DecisionCategory.BLOCK,
                category=ViolationCategory.PATH_TRAVERSAL_ATTEMPT,
                severity=SeverityLevel.HIGH,
                reason="Missing target file path in tool arguments",
                explanation="Operation blocked: Target path is empty or missing.",
                agent_id=self.assignment.agent_id,
                assignment_version=self.assignment.assignment_version,
            )

        # Validate path security and normalize
        is_valid, norm_path, error_msg = PathSecurityValidator.normalize_and_validate(
            raw_path, self.workspace_root
        )
        if not is_valid:
            return PolicyDecision(
                decision=DecisionCategory.BLOCK,
                category=ViolationCategory.PATH_TRAVERSAL_ATTEMPT,
                severity=SeverityLevel.CRITICAL,
                reason=error_msg or "Path traversal security violation",
                explanation=self._format_explanation(
                    status="BLOCKED: PATH TRAVERSAL DETECTED",
                    attempted_action=f"{action.tool_name} on '{raw_path}'",
                    reason=error_msg or "Attempted path traversal outside workspace.",
                    owner=None,
                    action_advice="Path must resolve within the workspace root.",
                ),
                target_path=raw_path,
                agent_id=self.assignment.agent_id,
                assignment_version=self.assignment.assignment_version,
            )

        # Evaluate the normalized relative path
        return self._evaluate_path_permissions(norm_path, action.tool_name, action.tool_args)

    def _evaluate_command_tool(self, action: ActionRequest) -> PolicyDecision:
        """Evaluates shell commands for destructive actions or out-of-scope targets."""
        command_line = action.raw_command or action.tool_args.get("CommandLine", "")
        analysis = ShellCommandAnalyzer.analyze_command(command_line)

        # Check explicitly prohibited operations (e.g., deletion)
        if analysis["is_destructive"]:
            # Check if any prohibited operations match
            for prohibited in self.assignment.prohibited_operations:
                if prohibited in ("delete", "rm", "deletion") and analysis["command_name"] in ("rm", "rmdir"):
                    return PolicyDecision(
                        decision=DecisionCategory.BLOCK,
                        category=ViolationCategory.DESTRUCTIVE_COMMAND,
                        severity=SeverityLevel.HIGH,
                        reason="Destructive deletion operation explicitly prohibited",
                        explanation=self._format_explanation(
                            status="BLOCKED: DESTRUCTIVE OPERATION PROHIBITED",
                            attempted_action=f"Execute '{command_line}'",
                            reason=f"Operation '{analysis['command_name']}' is listed in prohibited_operations.",
                            owner=None,
                            action_advice="File deletion is disabled for this agent assignment.",
                        ),
                        agent_id=self.assignment.agent_id,
                        assignment_version=self.assignment.assignment_version,
                    )

        # If suspected targets exist (e.g. redirection into file, rm on file), check them against scope!
        for target in analysis["suspected_targets"]:
            is_valid, norm_path, _ = PathSecurityValidator.normalize_and_validate(
                target, self.workspace_root
            )
            if is_valid:
                sub_decision = self._evaluate_path_permissions(
                    norm_path, f"run_command ({analysis['command_name']})", action.tool_args
                )
                if sub_decision.is_blocked:
                    return PolicyDecision(
                        decision=sub_decision.decision,
                        category=sub_decision.category,
                        severity=sub_decision.severity,
                        reason=f"Command touches out-of-scope target '{norm_path}': {sub_decision.reason}",
                        explanation=self._format_explanation(
                            status="BLOCKED: COMMAND TARGETS RESTRICTED/OUT-OF-SCOPE PATH",
                            attempted_action=f"Execute '{command_line}' targeting '{norm_path}'",
                            reason=sub_decision.reason,
                            owner=sub_decision.owner,
                            action_advice="Modify only files within your assigned scope.",
                        ),
                        owner=sub_decision.owner,
                        target_path=norm_path,
                        agent_id=self.assignment.agent_id,
                        assignment_version=self.assignment.assignment_version,
                    )

        # If no restricted target detected, allow command
        return PolicyDecision(
            decision=DecisionCategory.ALLOW,
            reason="Command does not target restricted files",
            explanation=f"Command '{command_line}' passed local safety checks.",
            agent_id=self.assignment.agent_id,
            assignment_version=self.assignment.assignment_version,
        )

    def _find_owner(self, norm_path: str) -> Optional[str]:
        """Finds if an owner is registered for the given path."""
        for record in self.assignment.ownership_info:
            if match_path_pattern(record.path_pattern, norm_path):
                return record.owner_agent_id
        return None

    def _evaluate_path_permissions(
        self, norm_path: str, action_desc: str, tool_args: Dict
    ) -> PolicyDecision:
        """Checks path against exceptions, restrictions, ownership, and allowed paths."""
        
        # 1. Check Exceptions (Highest priority allow)
        for exc in self.assignment.exceptions:
            if match_path_pattern(exc, norm_path):
                return PolicyDecision(
                    decision=DecisionCategory.ALLOW,
                    reason=f"Path matches authorized exception '{exc}'",
                    explanation=f"Operation allowed via explicit exception '{exc}'.",
                    target_path=norm_path,
                    agent_id=self.assignment.agent_id,
                    assignment_version=self.assignment.assignment_version,
                )

        # 2. Check Ownership Collision (Another agent specifically owns this file)
        for record in self.assignment.ownership_info:
            if record.owner_agent_id != self.assignment.agent_id:
                if match_path_pattern(record.path_pattern, norm_path):
                    explanation = self._format_explanation(
                        status="BLOCKED: OWNERSHIP COLLISION",
                        attempted_action=f"Modify {norm_path}",
                        reason=f"The requested file is reserved/owned by another agent ('{record.owner_agent_id}').",
                        owner=record.owner_agent_id,
                        action_advice="Modification denied. Request cross-agent authorization or coordinator reassignment.",
                    )
                    decision_cat = (
                        DecisionCategory.ASK
                        if not self.strict_ownership
                        else DecisionCategory.BLOCK
                    )
                    return PolicyDecision(
                        decision=decision_cat,
                        category=ViolationCategory.OWNERSHIP_COLLISION,
                        severity=SeverityLevel.HIGH,
                        reason=f"File owned by agent '{record.owner_agent_id}' ({record.path_pattern})",
                        explanation=explanation,
                        owner=record.owner_agent_id,
                        target_path=norm_path,
                        agent_id=self.assignment.agent_id,
                        assignment_version=self.assignment.assignment_version,
                    )

        # 3. Check Restricted Paths (Explicit denial)
        for rest in self.assignment.restricted_paths:
            if match_path_pattern(rest, norm_path):
                owner = self._find_owner(norm_path)
                explanation = self._format_explanation(
                    status="BLOCKED: RESTRICTED PATH ACCESS",
                    attempted_action=f"Modify {norm_path}",
                    reason=f"The requested path is explicitly marked restricted ('{rest}').",
                    owner=owner,
                    action_advice="Access denied. Path is restricted by project policy.",
                )
                return PolicyDecision(
                    decision=DecisionCategory.BLOCK,
                    category=ViolationCategory.RESTRICTED_PATH_ACCESS,
                    severity=SeverityLevel.HIGH,
                    reason=f"Path matches restricted pattern '{rest}'",
                    explanation=explanation,
                    owner=owner,
                    target_path=norm_path,
                    agent_id=self.assignment.agent_id,
                    assignment_version=self.assignment.assignment_version,
                )

        # 4. Check Allowed Paths
        is_allowed = False
        matching_allowed_pattern = None
        for allowed in self.assignment.allowed_paths:
            if match_path_pattern(allowed, norm_path):
                is_allowed = True
                matching_allowed_pattern = allowed
                break

        if is_allowed:
            return PolicyDecision(
                decision=DecisionCategory.ALLOW,
                reason=f"Path matches permitted pattern '{matching_allowed_pattern}'",
                explanation=f"Operation permitted: '{norm_path}' is within assigned scope.",
                target_path=norm_path,
                agent_id=self.assignment.agent_id,
                assignment_version=self.assignment.assignment_version,
            )

        # 5. Out of Scope (Does not match allowed paths)
        other_owner = self._find_owner(norm_path)
        explanation = self._format_explanation(
            status="BLOCKED: OUT-OF-SCOPE MODIFICATION",
            attempted_action=f"Modify {norm_path}",
            reason="The requested file is outside the agent's permitted directories.",
            owner=other_owner,
            action_advice="Modification denied. Request authorization or reassignment.",
        )

        return PolicyDecision(
            decision=DecisionCategory.BLOCK,
            category=ViolationCategory.OUT_OF_SCOPE_MODIFICATION,
            severity=SeverityLevel.MEDIUM,
            reason="File is outside permitted directories",
            explanation=explanation,
            owner=other_owner,
            target_path=norm_path,
            agent_id=self.assignment.agent_id,
            assignment_version=self.assignment.assignment_version,
        )

    def _format_explanation(
        self,
        status: str,
        attempted_action: str,
        reason: str,
        owner: Optional[str],
        action_advice: str,
    ) -> str:
        """Formats an explainable violation report adhering to specification format."""
        lines = [
            status,
            f"Agent: {self.assignment.agent_id}",
            f"Attempted action: {attempted_action}",
            f"Assigned responsibility: {self.assignment.task_description}",
            f"Reason: {reason}",
        ]
        if owner:
            lines.append(f"Owner: {owner}")
        lines.append(f"Action: {action_advice}")
        return "\n".join(lines)
