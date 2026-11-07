"""Verdict parser and handler: processes judge commands, records decisions, and creates tasks."""
from __future__ import annotations
import re
from typing import Tuple, List, Optional
from .models import Verdict, VerdictType, Condition, Task, Case, CaseState

class VerdictParser:
    @staticmethod
    def parse_command(command_str: str, judge_name: str = "Priya") -> Verdict:
        """Parse human judge command grammar into structured Verdict."""
        # Clean prefix: handle @court-clerk, @clerk, @judge, court-clerk, clerk, and optional 'verdict'
        cmd = command_str.strip()
        cmd = re.sub(r"^@?(court-clerk|clerk|judge|release-judge)\s*[:,-]?\s*", "", cmd, flags=re.IGNORECASE).strip()
        cmd = re.sub(r"^verdict\s*[:,-]?\s*", "", cmd, flags=re.IGNORECASE).strip()
        if not cmd:
            raise ValueError(
                "Invalid verdict command: empty command text.\n"
                "Allowed formats:\n"
                "  @court-clerk verdict APPROVE\n"
                "  @court-clerk verdict BLOCK reason=\"<reason>\"\n"
                "  @court-clerk verdict CONDITIONS <c1>; <c2>; rollback owner <name>"
            )

        # Check for natural commands
        # 1. APPROVE variants: APPROVE, APPROVED, SHIP, YES
        if re.fullmatch(r"(APPROVE|APPROVED|SHIP|YES)[.!]?", cmd, re.IGNORECASE):
            return Verdict(judge=judge_name, type=VerdictType.APPROVE)

        # 2. BLOCK variants: BLOCK, BLOCKED, REJECT, REJECTED, NO
        elif re.match(r"^(BLOCK|BLOCKED|REJECT|REJECTED|NO)\b", cmd, re.IGNORECASE):
            remainder = re.sub(r"^(BLOCK|BLOCKED|REJECT|REJECTED|NO)\s*[:,-]?\s*", "", cmd, flags=re.IGNORECASE).strip()
            reason = None
            if remainder:
                m = re.search(r'(?:reason\s*=\s*["\']?([^"\']+)["\']?|because\s+(.+)|reason\s*:\s*(.+))', remainder, re.IGNORECASE)
                if m:
                    reason = m.group(1) or m.group(2) or m.group(3)
                else:
                    reason = remainder
            return Verdict(judge=judge_name, type=VerdictType.BLOCK, reason=reason or "Blocked by Release Judge")

        # 3. CONDITIONS variants: CONDITIONS, CONDITION, CONDITIONAL, SHIP WITH CONDITIONS
        elif re.match(r"^(CONDITIONS?|CONDITIONAL|SHIP\s+WITH\s+CONDITIONS?)\b", cmd, re.IGNORECASE):
            remainder = re.sub(r"^(CONDITIONS?|CONDITIONAL|SHIP\s+WITH\s+CONDITIONS?)\s*[:,-]?\s*", "", cmd, flags=re.IGNORECASE).strip()
            conditions: List[Condition] = []
            
            # Split clauses by semicolon, newline, or ' and '
            raw_clauses = re.split(r"[;\n]|(?<=\S)\s+and\s+(?=\S)", remainder)
            clauses = [c.strip() for c in raw_clauses if c.strip()]
            
            # Fallback if only commas were used with multiple clauses
            if len(clauses) == 1 and "," in clauses[0] and ("alert" in clauses[0].lower() or "canary" in clauses[0].lower()):
                clauses = [c.strip() for c in clauses[0].split(",") if c.strip()]

            for idx, clause in enumerate(clauses, start=1):
                owner = judge_name
                desc = clause
                clause_lower = clause.lower()
                if "owns" in clause_lower or "rollback owner" in clause_lower:
                    m = re.search(r'^(.*?)\s+owns\s+(.*)$', clause, re.IGNORECASE)
                    if m:
                        owner = m.group(1).strip()
                        desc = f"Confirm rollback owner and rehearse rollback ({m.group(2).strip()})"
                    else:
                        m2 = re.search(r'rollback\s+owner\s*[:=]?\s*([a-zA-Z0-9_-]+)', clause, re.IGNORECASE)
                        if m2:
                            owner = m2.group(1).strip()
                            desc = f"Confirm rollback owner and rehearse rollback"
                elif "alert" in clause_lower:
                    owner = "DevOps"
                elif "canary" in clause_lower:
                    owner = judge_name
                    desc = f"Configure {clause.strip()} rollout"

                conditions.append(Condition(id=f"COND-{idx}", description=desc, owner=owner))
            if not conditions:
                raise ValueError('Conditional verdict requires at least one explicit condition')
            return Verdict(judge=judge_name, type=VerdictType.CONDITIONS, conditions=conditions)
        else:
            raise ValueError(
                f"Unknown verdict command '{command_str}'. Must be APPROVE, BLOCK, or CONDITIONS.\n"
                "Examples:\n"
                "  @court-clerk verdict APPROVE\n"
                "  @court-clerk verdict BLOCK reason=\"No rollback owner\"\n"
                "  @court-clerk verdict CONDITIONS add pricing-mismatch alert; canary 5%; Priya owns rollback"
            )

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

