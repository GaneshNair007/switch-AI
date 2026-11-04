"""Autonomous Courtroom Agent Sessions running over the Switch Room Bus.
Implements the 5 distinct roles: Clerk, Historian, Prosecutor, Defender, and Rollback Engineer.
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
                f"Case {case.case_id} opened.\n"
                f"Change: dynamic checkout pricing. Affected services: {', '.join(case.affected_services)}.\n"
                f"CI: {case.ci_status}. Deployment: {case.deployment_target}.\n"
                f"@historian: Please search incident memory for relevant precedent."
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
                    f"Verdict recorded: {verdict.type.value}.\n"
                    f"Tasks created in Switch:\n{task_summary}\n\n"
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
                    f"Relevant precedent found: {p['incident_id']}. "
                    f"A {p['change_type']}-related change on {p['date']} caused {p['symptom']}. "
                    f"Impact: {p['impact']}. Required lesson: {p['lesson']}.\n"
                    f"@prosecutor: Please formulate evidence-based objections based on this precedent and PR diff."
                )
            else:
                reply = "No relevant precedent found in incident memory. @prosecutor: Review PR diff."
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

            lines = ["Prosecution Objections:"]
            for o in objections:
                lines.append(f"  - {o.id} -- {o.classification.value}: {o.claim} Evidence: {o.evidence}")
            lines.append("@defender: Please address each objection in order or concede.")
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

            lines = ["Defense Responses:"]
            for d in defenses:
                lines.append(f"  - For {d.objection_id}: {d.claim} ({d.evidence})")
            lines.append("@rollback: Please produce validated rollback plan and runbook checks.")
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
                f"Rollback plan verified: target version: {plan.target_version}.\n"
                f"Command: {plan.command}\n"
                f"Health checks: {', '.join(plan.health_checks)}.\n"
                f"Rollback owner: {plan.rollback_owner} (Status: {plan.execution_status.value})\n"
                f"[SAFETY] Rollback requires explicit human approval; auto-execution is disabled.\n"
                f"@clerk: Case evidence, defense, and rollback plan ready for Release Judge."
            )
            self.room.post_message(self.name, reply)

            # Trigger Clerk's final verdict invitation
            if clerk:
                unresolved = [o for o in clerk.current_case.objections if o.classification == ObjectionSeverity.BLOCKING]
                clerk_msg = (
                    f"Case ready for verdict. Unresolved blocking condition: {len(unresolved)} item(s) (pricing mismatch alert).\n"
                    f"Awaiting binding verdict from Human Release Judge (@Priya): APPROVE, BLOCK, or CONDITIONS."
                )
                self.room.post_message(clerk.name, clerk_msg)
