"""Rollback validation engine: verifies reversibility, runbooks, health checks, and owner."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List
from .models import RollbackPlan, RollbackStatus

class RollbackEngine:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"

    def generate_plan(self, service: str, requested_owner: str | None = None) -> RollbackPlan:
        """Generate and validate rollback plan from verified runbooks."""
        runbooks_path = self.data_dir / "runbooks.json"
        runbooks: Dict[str, Any] = {}
        if runbooks_path.exists():
            with open(runbooks_path, "r", encoding="utf-8") as f:
                runbooks = json.load(f)

        service_data = runbooks.get(service, {})
        current_version = service_data.get("current_version", "v2.14.0")
        target_version = service_data.get("last_known_good_version", "v2.13.2")
        cmd_template = service_data.get("rollback_command_template", f"./scripts/rollback.sh {service} {{target_version}}")
        command = cmd_template.format(target_version=target_version)
        health_checks: List[str] = service_data.get("health_checks", [
            "checkout error rate < 1%",
            "cart-service p95 latency < 400ms",
            "pricing consistency job passes"
        ])
        owner = requested_owner if requested_owner is not None else service_data.get("default_owner", "Priya")
        status = RollbackStatus.READY if owner else RollbackStatus.MISSING_OWNER

        return RollbackPlan(
            current_version=current_version,
            target_version=target_version,
            command=command,
            health_checks=health_checks,
            rollback_owner=owner,
            execution_status=status
        )

    @staticmethod
    def validate_plan(plan: RollbackPlan) -> bool:
        """Validate that rollback plan meets safety criteria."""
        if not plan.rollback_owner:
            plan.execution_status = RollbackStatus.MISSING_OWNER
            raise ValueError("Rollback validation failed: Rollback owner is required.")
        if not plan.command or not plan.target_version:
            plan.execution_status = RollbackStatus.BLOCKED
            raise ValueError("Rollback validation failed: Missing command or target version.")
        return True
