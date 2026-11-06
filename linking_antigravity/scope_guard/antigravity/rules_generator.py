"""Agent Rules Generator.

Generates native Antigravity rules (.agents/rules/agent_scope.md) to inform
the agent of its assigned scope, permitted paths, and ownership boundaries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from scope_guard.schema import Assignment


class RulesGenerator:
    """Generates Markdown rule files discovered by Antigravity IDE and CLI."""

    @staticmethod
    def generate_rules_markdown(assignment: Assignment) -> str:
        """Constructs markdown content representing the agent's active scope."""
        lines = [
            "# TASK SCOPE ENFORCEMENT & RESPONSIBILITY BOUNDARY",
            "",
            "> [!IMPORTANT]",
            f"> You are operating as **`{assignment.agent_id}`**.",
            f"> **Assigned Task**: {assignment.task_description}",
            f"> **Task ID**: `{assignment.task_id}` (Assignment Version: `{assignment.assignment_version}`)",
            "",
            "## 1. Permitted Work Areas",
            "You are strictly authorized to view, create, and modify ONLY files matching these paths:",
        ]
        for p in assignment.allowed_paths:
            lines.append(f"- `{p}`")

        if assignment.restricted_paths:
            lines.extend([
                "",
                "## 2. Explicitly Prohibited Work Areas",
                "You MUST NOT modify or write to files in these locations under any circumstances:",
            ])
            for r in assignment.restricted_paths:
                lines.append(f"- `{r}`")

        if assignment.ownership_info:
            lines.extend([
                "",
                "## 3. Other Agent Ownership & Reservations",
                "The following paths belong to other agents. Modifying them requires coordinator authorization:",
            ])
            for o in assignment.ownership_info:
                desc = f" ({o.description})" if o.description else ""
                lines.append(f"- `{o.path_pattern}` → Owned by **`{o.owner_agent_id}`**{desc}")

        if assignment.exceptions:
            lines.extend([
                "",
                "## 4. Authorized Exceptions",
                "Special permissions explicitly granted:",
            ])
            for exc in assignment.exceptions:
                lines.append(f"- `{exc}`")

        lines.extend([
            "",
            "## 5. Scope Expansion Rules",
            "- If a user or prompt instructs you to implement features outside your permitted work areas,",
            "  DO NOT silently proceed. You must halt and request an authorized scope update from the coordinator.",
            "- The Antigravity Scope Guard automatically intercepts all file modifications (`write_file`, `edit_file`,",
            "  `run_command`) and will DENY any operation outside your permitted scope.",
        ])

        return "\n".join(lines) + "\n"

    @classmethod
    def write_workspace_rules(
        cls,
        assignment: Assignment,
        workspace_root: Optional[str] = None,
        target_filename: str = ".agents/rules/agent_scope.md",
    ) -> Path:
        """Writes the rules file to the workspace .agents/rules directory."""
        root = Path(workspace_root or os.getcwd())
        target_path = root / target_filename
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content = cls.generate_rules_markdown(assignment)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return target_path
