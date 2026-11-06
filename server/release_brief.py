"""Release Brief generator: builds formatted terminal and room markdown artifact."""
from __future__ import annotations
import json
from typing import Dict, Any
from .models import Case, VerdictType

class ReleaseBriefGenerator:
    @staticmethod
    def generate_markdown(case: Case, room_name: str = "#ship-court") -> str:
        """Format the full Release Brief markdown artifact per Section 8 specification."""
        verdict_str = case.verdict.type.value if case.verdict else "PENDING"
        if case.verdict and case.verdict.type == VerdictType.CONDITIONS:
            verdict_str = "SHIP WITH CONDITIONS"

        judge_name = case.verdict.judge if case.verdict else "Unassigned"
        lines = [
            f"# Release Brief - {case.case_id}",
            f"Change: {case.change_summary}",
            f"Repository: {case.repository}",
            f"PR: #{case.pr_url.rstrip('/').split('/')[-1]}",
            f"Requested by: {judge_name}",
            f"Decision: {verdict_str}",
            "",
            "## Risk assessment",
            "| # | Objection | Classification | Status | Evidence |",
            "|---|---|---|---|---|"
        ]

        for idx, obj in enumerate(case.objections, start=1):
            status_text = obj.status.value.capitalize()
            if status_text == "Conceded": status_text = "Open"
            lines.append(f"| {idx} | {obj.claim} | {obj.classification.value} | {status_text} | {obj.evidence} |")

        lines.append("")
        lines.append("## Rollback plan")
        if case.rollback_plan:
            rb = case.rollback_plan
            checks = ", ".join(rb.health_checks)
            lines.append(f"- Current version: {rb.current_version}")
            lines.append(f"- Rollback target: {rb.target_version}")
            lines.append(f"- Command: {rb.command}")
            lines.append(f"- Health checks: {checks}")
            lines.append(f"- Rollback owner: {rb.rollback_owner}")
            lines.append(f"- Execution status: {rb.execution_status.value} -- requires explicit human approval")
        else:
            lines.append("- No rollback plan registered.")

        if case.tasks:
            lines.append("")
            lines.append("## Conditions before full rollout")
            for task in case.tasks:
                lines.append(f"- [ ] {task.description} -- {task.owner}")

        lines.append("")
        lines.append("## Decision record")
        lines.append(f"- Judge: {judge_name}")
        lines.append(f"- Verdict: {verdict_str}")
        lines.append(f"- Switch room: {room_name}")
        lines.append(f"- Case ID: {case.case_id}")

        return "\n".join(lines)

    @staticmethod
    def generate_json(case: Case) -> Dict[str, Any]:
        """Produce structured JSON artifact for Switch and downstream tooling."""
        return {
            "case_id": case.case_id,
            "pr_url": case.pr_url,
            "repository": case.repository,
            "affected_services": case.affected_services,
            "ci_status": case.ci_status,
            "deployment_target": case.deployment_target,
            "state": case.state.value,
            "verdict": {
                "judge": case.verdict.judge,
                "type": case.verdict.type.value,
                "reason": case.verdict.reason
            } if case.verdict else None,
            "objections": [
                {
                    "id": o.id, "claim": o.claim, "evidence": o.evidence,
                    "classification": o.classification.value, "status": o.status.value
                } for o in case.objections
            ],
            "rollback_plan": {
                "current_version": case.rollback_plan.current_version,
                "target_version": case.rollback_plan.target_version,
                "command": case.rollback_plan.command,
                "health_checks": case.rollback_plan.health_checks,
                "rollback_owner": case.rollback_plan.rollback_owner,
                "execution_status": case.rollback_plan.execution_status.value
            } if case.rollback_plan else None,
            "tasks": [
                {"id": t.id, "description": t.description, "owner": t.owner, "status": t.status}
                for t in case.tasks
            ]
        }

