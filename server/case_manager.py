"""Case Manager: orchestrates case intake, bounded agent rounds, and verdict enforcement."""
from __future__ import annotations
import random
from typing import Dict, Any, Optional, List
from .models import Case, CaseState, ObjectionSeverity, RollbackStatus
from .evidence import EvidenceCollector
from .prosecutor_rules import ProsecutorRuleEngine
from .defender_rules import DefenderRuleEngine
from .rollback import RollbackEngine
from .verdict import VerdictParser
from .release_brief import ReleaseBriefGenerator

class CaseManager:
    def __init__(self, data_dir=None):
        self.evidence_collector = EvidenceCollector(data_dir=data_dir)
        self.rollback_engine = RollbackEngine(data_dir=data_dir)
        self.prosecutor_rules = ProsecutorRuleEngine
        self.defender_rules = DefenderRuleEngine
        self.active_cases: Dict[str, Case] = {}

    def open_case(self, pr_url: str, custom_case_id: Optional[str] = None) -> Case:
        """Initialize a new courtroom case from PR URL."""
        case_id = custom_case_id or f"SC-{random.randint(100, 999):04d}"
        repo_meta = self.evidence_collector.fetch_pr_evidence(pr_url)
        ci_meta = repo_meta.get("ci_status", {})
        ci_str = f"{ci_meta.get('passed', 42)} passed, {ci_meta.get('failed', 0)} failed" if isinstance(ci_meta, dict) else str(ci_meta)

        case = Case(
            case_id=case_id,
            pr_url=pr_url,
            repository=repo_meta.get("repository", "acme/shop"),
            affected_services=repo_meta.get("affected_services", ["checkout-service"]),
            ci_status=ci_str,
            deployment_target=repo_meta.get("deployment_target", "staging -> production canary"),
            state=CaseState.CASE_OPENED
        )
        self.active_cases[case_id] = case
        return case

    def run_procedural_pipeline(self, case_id: str, rollback_owner: str = "Priya") -> Dict[str, Any]:
        """Execute the 4 bounded procedural rounds: evidence, prosecution, defense, rollback."""
        case = self.active_cases.get(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        # Round 1: Evidence collection from Incident Historian
        case.state = CaseState.EVIDENCE_COLLECTION
        case.round_count += 1
        service = case.affected_services[0] if case.affected_services else "checkout-service"
        precedents = self.evidence_collector.search_incidents(service=service)

        # Round 2: Prosecutor objections
        case.state = CaseState.OBJECTIONS_RAISED
        case.round_count += 1
        repo_meta = self.evidence_collector.fetch_pr_evidence(case.pr_url)
        case.objections = ProsecutorRuleEngine.generate_objections(repo_meta, precedents)

        # Round 3: Defender rebuttals and concessions
        case.state = CaseState.DEFENSE_RESPONSE
        case.round_count += 1
        case.defenses = DefenderRuleEngine.answer_objections(case.objections, repo_meta)

        # Round 4: Rollback Engineer reversibility validation
        case.state = CaseState.ROLLBACK_REQUIRED
        case.round_count += 1
        case.rollback_plan = self.rollback_engine.generate_plan(service, requested_owner=rollback_owner)
        self.rollback_engine.validate_plan(case.rollback_plan)

        # Ready for Human Release Judge verdict (bounded rule enforced)
        case.state = CaseState.AWAITING_VERDICT

        unresolved_blocking = [
            obj for obj in case.objections if obj.classification == ObjectionSeverity.BLOCKING
        ]

        return {
            "case_id": case.case_id,
            "state": case.state.value,
            "round_count": case.round_count,
            "precedents": precedents,
            "objections_count": len(case.objections),
            "unresolved_blocking": len(unresolved_blocking),
            "rollback_status": case.rollback_plan.execution_status.value
        }

    def record_verdict(self, case_id: str, command: str, judge: str = "Priya", is_human: bool = True) -> str:
        """Enforce exclusive human approver role and register final verdict."""
        if not is_human:
            raise PermissionError("Security violation: Only a human holding the exclusive approver role may issue a verdict.")
        case = self.active_cases.get(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        verdict = VerdictParser.parse_command(command, judge_name=judge)
        VerdictParser.apply_verdict(case, verdict)
        case.release_brief = ReleaseBriefGenerator.generate_markdown(case)
        case.state = CaseState.CASE_CLOSED
        return case.release_brief

