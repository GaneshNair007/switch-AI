"""Verdict parser and handler: processes judge commands, records decisions, and creates tasks."""
from __future__ import annotations
import re
from typing import Tuple, List, Optional
from .models import Verdict, VerdictType, Condition, Task, Case, CaseState

class VerdictParser:
    @staticmethod
    def parse_command(command_str: str, judge_name: str = "Priya") -> Verdict:
        """Parse human judge command grammar into structured Verdict."""
        # Clean prefix
        cmd = re.sub(r"^@?court-clerk\s+verdict\s+", "", command_str.strip(), flags=re.IGNORECASE).strip()
        if not cmd:
            raise ValueError("Invalid verdict command: empty command text.")

        parts = cmd.split(maxsplit=1)
        raw_type = parts[0].upper()
        remainder = parts[1].strip() if len(parts) > 1 else ""

        if raw_type == "APPROVE":
            return Verdict(judge=judge_name, type=VerdictType.APPROVE)
        elif raw_type == "BLOCK":
            reason = None
            if remainder:
                m = re.search(r'reason=["\']?([^"\']+)["\']?', remainder, re.IGNORECASE)
                reason = m.group(1) if m else remainder
            return Verdict(judge=judge_name, type=VerdictType.BLOCK, reason=reason or "Blocked by Release Judge")
        elif raw_type in ("CONDITIONS", "CONDITION"):
            conditions: List[Condition] = []
            clauses = [c.strip() for c in remainder.split(";") if c.strip()]
            for idx, clause in enumerate(clauses, start=1):
                owner = judge_name
                desc = clause
                if "owns" in clause.lower():
                    m = re.search(r'^(.*?)\s+owns\s+(.*)$', clause, re.IGNORECASE)
                    if m:
                        owner = m.group(1).strip()
                        desc = f"Confirm rollback owner and rehearse rollback ({m.group(2).strip()})"
                elif "alert" in clause.lower():
                    owner = "DevOps"
                elif "canary" in clause.lower():
                    owner = judge_name
                    desc = f"Configure {clause.strip()} rollout"

                conditions.append(Condition(id=f"COND-{idx}", description=desc, owner=owner))
            return Verdict(judge=judge_name, type=VerdictType.CONDITIONS, conditions=conditions)
        else:
            raise ValueError(f"Unknown verdict type '{raw_type}'. Must be APPROVE, BLOCK, or CONDITIONS.")

    @staticmethod
    def apply_verdict(case: Case, verdict: Verdict) -> Tuple[Case, List[Task]]:
        """Apply verdict to Case and produce Switch tasks for tracking."""
        case.verdict = verdict
        tasks: List[Task] = []
        if verdict.type == VerdictType.APPROVE:
            case.state = CaseState.APPROVED
        elif verdict.type == VerdictType.BLOCK:
            case.state = CaseState.BLOCKED
            tasks.append(Task(id=f"TASK-BLOCK-1", description=f"Resolve blocking issue: {verdict.reason}", owner="DevOps"))
        elif verdict.type == VerdictType.CONDITIONS:
            case.state = CaseState.CONDITIONAL
            for cond in verdict.conditions:
                tasks.append(Task(id=f"TASK-{cond.id}", description=cond.description, owner=cond.owner))
        case.tasks = tasks
        return case, tasks

