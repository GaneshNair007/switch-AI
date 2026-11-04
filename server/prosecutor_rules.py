"""Prosecutor rule engine: validates objections, evidence constraints, and severity tagging."""
from __future__ import annotations
from typing import List, Dict, Any
from .models import Objection, ObjectionSeverity

HIGH_RISK_SERVICES = {"checkout-service", "payment-service", "auth-service", "database-migration", "pricing-worker"}

class ProsecutorRuleEngine:
    @staticmethod
    def validate_objection(objection: Objection) -> bool:
        """Validate that an objection contains evidence and is not vague."""
        if not objection.evidence or len(objection.evidence.strip()) < 5:
            raise ValueError(f"Objection '{objection.id}' rejected: missing concrete evidence.")
        vague_phrases = ["may be risky", "might be dangerous", "could fail somehow", "just seems unsafe"]
        if any(phrase in objection.claim.lower() for phrase in vague_phrases) and not objection.evidence.startswith("INC-"):
            raise ValueError(f"Objection '{objection.id}' rejected: vague claim without precedent citation.")
        return True

    @staticmethod
    def generate_objections(repo_meta: Dict[str, Any], precedents: List[Dict[str, Any]]) -> List[Objection]:
        """Generate at most 3 evidence-backed objections based on diff, CI, and past incidents."""
        objections: List[Objection] = []
        # Check incident precedent
        for prec in precedents:
            if prec.get("service") in repo_meta.get("affected_services", []):
                objections.append(Objection(
                    id="OBJ-1",
                    claim="Dynamic pricing may create cart-total mismatch between client and server.",
                    evidence=f"{prec['incident_id']}: {prec.get('root_cause', 'Past incident')}",
                    classification=ObjectionSeverity.BLOCKING
                ))
                break

        # Check monitoring coverage
        missing_alerts = repo_meta.get("missing_alerts", [])
        if "pricing-mismatch" in missing_alerts or not repo_meta.get("monitoring_alerts"):
            objections.append(Objection(
                id=f"OBJ-{len(objections)+1}",
                claim="No monitoring exists for pricing inconsistency.",
                evidence="No alert named pricing-mismatch in monitoring configuration.",
                classification=ObjectionSeverity.WARNING
            ))

        # Check rollout specification
        target = repo_meta.get("deployment_target", "")
        if "canary" in target.lower() and "5%" not in target and "10%" not in target:
            objections.append(Objection(
                id=f"OBJ-{len(objections)+1}",
                claim="Rollout percentage is not specified.",
                evidence="Deployment target specified canary without explicit traffic percentage.",
                classification=ObjectionSeverity.NOTE
            ))

        # Enforce max 3 objections
        return objections[:3]

