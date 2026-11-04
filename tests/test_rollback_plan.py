"""Tests for RollbackEngine: runbook lookup, health check validation, owner enforcement."""
import pytest
from server.rollback import RollbackEngine
from server.models import RollbackStatus

def test_rollback_plan_generation():
    engine = RollbackEngine()
    plan = engine.generate_plan("checkout-service", requested_owner="Priya")
    assert plan.current_version == "v2.14.0"
    assert plan.target_version == "v2.13.2"
    assert "checkout error rate" in plan.health_checks[0]
    assert plan.rollback_owner == "Priya"
    assert plan.execution_status == RollbackStatus.READY
    assert engine.validate_plan(plan) is True

def test_rollback_plan_missing_owner():
    engine = RollbackEngine()
    plan = engine.generate_plan("checkout-service", requested_owner="")
    with pytest.raises(ValueError, match="Rollback owner is required"):
        engine.validate_plan(plan)

