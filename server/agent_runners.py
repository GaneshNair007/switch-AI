"""Autonomous Courtroom Agent Sessions running over the Switch Room Bus.
Implements the 5 distinct roles: Clerk, Historian, Prosecutor, Defender, and Rollback Engineer.
Enforces fierce adversarial cross-examination, evidence-backed debate, and exclusive human gate.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from .switch_room import SwitchRoom, RoomMessage
from .case_manager import CaseManager
from .models import Case, ObjectionSeverity, RollbackStatus
from .verdict import VerdictParser
from .release_brief import ReleaseBriefGenerator

class CourtClerkAgent:
    def __init__(self, room: SwitchRoom, case_manager: CaseManager):
        self.room = room
        self.mgr = case_manager
        self.alias = "clerk"
        self.name = "court-clerk"
        self.current_case: Optional[Case] = None

    def on_message(self, msg: RoomMessage):
        content = msg.content.strip()

        # Handle case intake: @court-clerk open case <PR_URL>
        if "@court-clerk open case" in content or "@clerk open case" in content:
            parts = content.split("open case")
            pr_url = parts[1].strip() if len(parts) > 1 else "https://github.com/acme/shop/pull/482"
            self.current_case = self.mgr.open_case(pr_url, custom_case_id="SC-0482")
            case = self.current_case

            reply = (
                f"[COURT IN SESSION] DOCKET CASE {case.case_id}: PR #{case.pr_url.split('/')[-1]} ({case.repository})\n"
                f"PETITION: Authorization to deploy '{case.affected_services[0]}' to production canary.\n"
                f"EVIDENCE DOSSIER: Services: {', '.join(case.affected_services)} | CI: {case.ci_status} | Target: {case.deployment_target}.\n"
                f"PROCEDURAL RULE: Maximum 4 adversarial rounds. Rubber-stamping is prohibited under penalty of contempt.\n"
                f"@historian: Subpoena past failure records and incident post-mortems for {case.affected_services[0]} immediately!"
            )
            self.room.post_message(self.name, reply)

        # Handle verdict command: @court-clerk verdict ...
        elif "@court-clerk verdict" in content or "@clerk verdict" in content:
            if not self.current_case:
                self.room.post_message(self.name, "No active case to issue a verdict on.")
                return

            # Security gate: exclusive approver check
            if not self.room.enforce_human_verdict_gate(msg.sender):
                self.room.post_message(
                    self.name,
                    f"[SECURITY VIOLATION] Verdict rejected. Sender '{msg.sender}' does NOT hold the exclusive approver role."
                )
                return

            try:
                verdict = VerdictParser.parse_command(content, judge_name=msg.sender)
                VerdictParser.apply_verdict(self.current_case, verdict)
                self.room.record_decision(self.current_case.case_id, verdict)
                self.room.tasks.extend(self.current_case.tasks)

                brief = ReleaseBriefGenerator.generate_markdown(self.current_case, room_name=f"#{self.room.room_name}")
                self.current_case.release_brief = brief

                task_summary = "\n".join([f"{i}. {t.description} -- owner: {t.owner}" for i, t in enumerate(self.current_case.tasks, 1)])
                verdict_announcement = (
                    f"FINAL COURT JUDGMENT RENDERED: {verdict.type.value}.\n"
                    f"Binding operational tasks created in Switch:\n{task_summary}\n\n"
                    f"Signed Release Brief published:\n\n{brief}"
                )
                self.room.post_message(self.name, verdict_announcement)
            except Exception as e:
                self.room.post_message(self.name, f"Error processing verdict: {e}")

class IncidentHistorianAgent:
    def __init__(self, room: SwitchRoom, case_manager: CaseManager):
        self.room = room
        self.mgr = case_manager
        self.alias = "historian"
        self.name = "incident-historian"

    def on_message(self, msg: RoomMessage):
        if msg.sender == "court-clerk" and "@historian" in msg.content:
            precedents = self.mgr.evidence_collector.search_incidents("checkout-service")
            if precedents:
                p = precedents[0]
                reply = (
                    f"[FORENSIC INCIDENT SUBPOENA] Incident Precedent Exhumed: {p['incident_id']} (Severity 1 Outage)\n"
                    f"HISTORICAL EVENT: A {p['change_type']}-related change on {p['date']} triggered {p['symptom']}.\n"
                    f"IMPACT & BLAST RADIUS: {p['impact']}. ROOT CAUSE: {p['root_cause']}.\n"
                    f"MANDATORY REMEDIATION PRECEDENT: {p['lesson']}.\n"
                    f"EMERGENCY REVERSAL: Reverted to {p.get('rollback', 'v1.88.4')} under crisis conditions.\n"
                    f"@prosecutor: The corporate failure graveyard is open. Indict this pull request with maximum adversarial scrutiny!"
                )
            else:
                reply = "No relevant precedent found in incident memory. @prosecutor: Review PR diff with unyielding rigor."
            self.room.post_message(self.name, reply)

class ProsecutorAgent:
    def __init__(self, room: SwitchRoom, case_manager: CaseManager):
        self.room = room
        self.mgr = case_manager
        self.alias = "prosecutor"
        self.name = "prosecutor"

    def on_message(self, msg: RoomMessage):
        if msg.sender == "incident-historian" and "@prosecutor" in msg.content:
            meta = self.mgr.evidence_collector.fetch_pr_evidence("https://github.com/acme/shop/pull/482")
            precedents = self.mgr.evidence_collector.search_incidents("checkout-service")
            objections = self.mgr.prosecutor_rules.generate_objections(meta, precedents)
            
            # Save objections to active case
            clerk = next((l.__self__ for l in self.room.message_listeners if isinstance(getattr(l, '__self__', None), CourtClerkAgent)), None)
            if clerk and clerk.current_case:
                clerk.current_case.objections = objections

            lines = [
                "[PROSECUTION INDICTMENT] MOTION TO PERMANENTLY BAR RELEASE:",
                "The Prosecution has completed deep forensic static and architectural inspection of PR #482.",
                "This deployment demonstrates dangerous vulnerabilities that threaten production reliability:",
            ]
            for o in objections:
                lines.append(f"  - [{o.classification.value}] {o.id}: {o.claim} Evidence: {o.evidence}")
            lines.append(
                "STATUTORY WARNING: Passing CI tests is INSUFFICIENT evidence for high-risk checkout mutations.\n"
                "@defender: You stand accused of introducing unmitigated production hazard. Rebut each charge or enter an explicit CONCESSION!"
            )
            self.room.post_message(self.name, "\n".join(lines))

class DefenderAgent:
    def __init__(self, room: SwitchRoom, case_manager: CaseManager):
        self.room = room
        self.mgr = case_manager
        self.alias = "defender"
        self.name = "defender"

    def on_message(self, msg: RoomMessage):
        if msg.sender == "prosecutor" and "@defender" in msg.content:
            clerk = next((l.__self__ for l in self.room.message_listeners if isinstance(getattr(l, '__self__', None), CourtClerkAgent)), None)
            meta = self.mgr.evidence_collector.fetch_pr_evidence("https://github.com/acme/shop/pull/482")
            objections = clerk.current_case.objections if (clerk and clerk.current_case) else []
            defenses = self.mgr.defender_rules.answer_objections(objections, meta)
            
            if clerk and clerk.current_case:
                clerk.current_case.defenses = defenses

            lines = [
                "[DEFENSE COMBATIVE REBUTTAL] COUNTER-EVIDENCE & CONCESSION RECORD:",
                "The Defense refuses to allow business progress to be suffocated by alarmist obstruction.",
                "Here is our factual technical defense, answering every objection in strict sequence:",
            ]
            for d in defenses:
                badge = "[EXPLICIT CONCESSION]" if d.is_conceded else "[REBUTTED & MITIGATED]"
                lines.append(f"  - {badge} For {d.objection_id}: {d.claim} ({d.evidence})")
            lines.append(
                "@rollback: Step into the arena! Interrogate our operational reversibility and demonstrate our fail-safe decapitation mechanism!"
            )
            self.room.post_message(self.name, "\n".join(lines))

class RollbackEngineerAgent:
    def __init__(self, room: SwitchRoom, case_manager: CaseManager):
        self.room = room
        self.mgr = case_manager
        self.alias = "rollback"
        self.name = "rollback-engineer"

    def on_message(self, msg: RoomMessage):
        if msg.sender == "defender" and "@rollback" in msg.content:
            clerk = next((l.__self__ for l in self.room.message_listeners if isinstance(getattr(l, '__self__', None), CourtClerkAgent)), None)
            plan = self.mgr.rollback_engine.generate_plan("checkout-service", requested_owner="Priya")
            self.mgr.rollback_engine.validate_plan(plan)

            if clerk and clerk.current_case:
                clerk.current_case.rollback_plan = plan

            reply = (
                f"[SRE ROLLBACK AUDIT] REVERSIBILITY INTERROGATION:\n"
                f"The Site Reliability division permits zero deployments without guaranteed instantaneous recovery.\n"
                f"  - Target Baseline: {plan.target_version} (Current: {plan.current_version})\n"
                f"  - Automated Decapitation Command: {plan.command}\n"
                f"  - Automated Health Probes: {', '.join(plan.health_checks)}\n"
                f"  - Designated Rollback Commander: {plan.rollback_owner} (Status: {plan.execution_status.value})\n"
                f"  - [SAFETY GATE] Rollback requires explicit human authorization; auto-execution is strictly disabled.\n"
                f"@clerk: All adversarial arguments have been fought to the limit. Convene the Human Release Judge!"
            )
            self.room.post_message(self.name, reply)

            # Trigger Clerk's final verdict invitation
            if clerk:
                unresolved = [o for o in clerk.current_case.objections if o.classification == ObjectionSeverity.BLOCKING]
                clerk_msg = (
                    f"[CROSS-EXAMINATION CONCLUDED] The combatants have exhausted their arguments.\n"
                    f"UNRESOLVED BLOCKING DEFECTS: {len(unresolved)} item(s) (pricing mismatch alert missing).\n"
                    f"Under exclusive approver law, AI agents are stripped of authority to approve. Only the Human Release Judge (@Priya / @judge) holds the gavel.\n"
                    f"Awaiting binding judgment: APPROVE, BLOCK, or CONDITIONS."
                )
                self.room.post_message(clerk.name, clerk_msg)
