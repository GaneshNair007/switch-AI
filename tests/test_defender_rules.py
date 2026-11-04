"""Tests for DefenderRuleEngine: matching order and concession handling."""
from server.defender_rules import DefenderRuleEngine
from server.models import Objection, ObjectionSeverity, ObjectionStatus

def test_answer_and_concession():
    objections = [
        Objection(id="OBJ-1", claim="Cart-total mismatch between client and server", evidence="INC-017", classification=ObjectionSeverity.WARNING),
        Objection(id="OBJ-2", claim="No monitoring exists for pricing inconsistency", evidence="Missing alert", classification=ObjectionSeverity.WARNING)
    ]
    defenses = DefenderRuleEngine.answer_objections(objections, {})
    assert len(defenses) == 2
    assert defenses[0].is_conceded is False
    assert defenses[1].is_conceded is True
    assert "CONCEDED" in defenses[1].claim
    assert objections[1].classification == ObjectionSeverity.BLOCKING
