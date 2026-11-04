"""Tests for ProsecutorRuleEngine: max objections, evidence validation, and vague claim rejection."""
import pytest
from server.prosecutor_rules import ProsecutorRuleEngine
from server.models import Objection, ObjectionSeverity

def test_validate_vague_objection_rejected():
    obj = Objection(
        id="OBJ-TEST",
        claim="This PR might be dangerous in production.",
        evidence="",
        classification=ObjectionSeverity.BLOCKING
    )
    with pytest.raises(ValueError, match="missing concrete evidence"):
        ProsecutorRuleEngine.validate_objection(obj)

def test_generate_objections_capped_at_three():
    meta = {
        "affected_services": ["checkout-service"],
        "missing_alerts": ["pricing-mismatch"],
        "deployment_target": "production canary"
    }
    precedents = [{"incident_id": "INC-017", "service": "checkout-service", "root_cause": "divergence"}]
    objections = ProsecutorRuleEngine.generate_objections(meta, precedents)
    assert len(objections) <= 3
    assert any(o.classification == ObjectionSeverity.BLOCKING for o in objections)

