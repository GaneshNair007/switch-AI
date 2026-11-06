"""Interactive Multi-Agent Courtroom Test Harness.
Accepts any task / PR / deployment petition from the user.
Orchestrates an adversarial debate ('fight') between Prosecutor, Defender, Historian, and Rollback Engineer.
Evaluates the 'power' (evidence weight & severity vs mitigation strength) of both sides.
The Judge renders the final priority and verdict based on who is more powerful.
"""
from __future__ import annotations
import sys
import argparse
import time
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .switch_room import SwitchRoom, RoomMessage
from .case_manager import CaseManager
from .models import Case, CaseState, Objection, Defense, ObjectionSeverity, VerdictType
from .verdict import VerdictParser
from .release_brief import ReleaseBriefGenerator

class InteractiveCourtroom:
    def __init__(self, room_name: str = "ship-court", judge_name: str = "Priya"):
        self.room = SwitchRoom(room_name=room_name, bridge="mattermost")
        self.mgr = CaseManager()
        self.judge_name = judge_name
        self.room.exclusive_roles["approver"] = judge_name

    def run_debate_on_task(self, task_description: str, repo: str = "acme/shop", pr_number: str = "709") -> Dict[str, Any]:
        """Runs an end-to-end multi-agent adversarial debate on a custom task."""
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
        case = self.mgr.open_case(pr_url, custom_case_id=f"SC-{pr_number}")
        case.description = task_description
        
        print("\n" + "=" * 80)
        print(f"🏛️  SHIP COURT: ADVERSARIAL TRIAL CONVENED IN #{self.room.room_name}")
        print("=" * 80)
        print(f"CASE DOCKET     : {case.case_id}")
        print(f"PETITION / TASK : {task_description}")
        print(f"REPOSITORY      : {repo} (PR #{pr_number})")
        print(f"PRESIDING JUDGE : @{self.judge_name} (Exclusive Human Gate)")
        print("-" * 80)

        # 1. Clerk Docket Intake
        print("\n[STEP 1: COURT CLERK INTAKE]")
        clerk_msg = (
            f"[COURT IN SESSION] DOCKET CASE {case.case_id}\n"
            f"PETITION: Authorization to deploy '{task_description}'\n"
            f"RULE: Cross-examination mandatory. Rubber-stamping prohibited under penalty of contempt.\n"
            f"@historian: Subpoena past failure precedents!"
        )
        self.room.post_message("court-clerk", clerk_msg)
        print(f"[@court-clerk]:\n{clerk_msg}\n")

        # 2. Forensic Historian
        print("[STEP 2: FORENSIC INCIDENT HISTORIAN]")
        task_lower = task_description.lower()
        if any(kw in task_lower for kw in ["database", "migration", "schema", "null", "drop"]):
            hist_id = "INC-089"
            hist_impact = "Database table lock during peak traffic caused 22-minute complete API outage."
            hist_cause = "Non-concurrent index creation and unbatched column backfill."
            hist_lesson = "Mandate zero-downtime expand/contract schema pattern and dry-run query plan."
        elif any(kw in task_lower for kw in ["stripe", "payment", "billing", "checkout", "price"]):
            hist_id = "INC-017"
            hist_impact = "Cart total divergence resulted in 41 corrupted transactions and manual billing reconciliations."
            hist_cause = "Client/server calculation mismatch with no parity assertion alert."
            hist_lesson = "Require server-authoritative assertion and real-time mismatch alarm."
        elif any(kw in task_lower for kw in ["auth", "jwt", "permission", "token", "security"]):
            hist_id = "INC-044"
            hist_impact = "Session replay vulnerability exposed tenant data in multi-tenant cluster."
            hist_cause = "Missing audience and clock-skew validation on refreshed token claims."
            hist_lesson = "Enforce cryptographic claim validation and automated revocation probe."
        else:
            hist_id = "INC-102"
            hist_impact = "Unhandled edge-case exception cascaded across upstream worker pool."
            hist_cause = "Missing circuit-breaker and dead-letter queue backpressure."
            hist_lesson = "Require staged canary rollout and automatic degradation switch."

        historian_msg = (
            f"[FORENSIC INCIDENT SUBPOENA] Incident Precedent Exhumed: {hist_id} (Severity 1 Outage)\n"
            f"HISTORICAL BLAST RADIUS: {hist_impact}\n"
            f"ROOT CAUSE            : {hist_cause}\n"
            f"MANDATORY REMEDIATION  : {hist_lesson}\n"
            f"@prosecutor: The corporate failure graveyard is open. Indict this petition with ruthless scrutiny!"
        )
        self.room.post_message("incident-historian", historian_msg)
        print(f"[@incident-historian]:\n{historian_msg}\n")

        # 3. Prosecutor Indictment (Fierce Opposition)
        print("[STEP 3: PROSECUTOR INDICTMENT ('THE FIGHT BEGINS')]")
        objections = []
        # Dynamic objection generation based on task content
        if "without staging" in task_lower or "skip" in task_lower or "bypass" in task_lower or "emergency" in task_lower:
            objections.append(Objection(
                id="OBJ-CRIT-1",
                claim="Bypassing staging / pre-flight qualification is an extreme governance and reliability violation.",
                evidence=f"Petition explicitly states emergency bypass ahead of deadline.",
                classification=ObjectionSeverity.BLOCKING
            ))
        if "null" in task_lower or "migration" in task_lower or "schema" in task_lower:
            objections.append(Objection(
                id="OBJ-CRIT-2",
                claim="Removing nullability or altering column constraints without phased backfill risks instant 500 error cascades.",
                evidence=f"Historical precedent {hist_id}: schema locks and unhandled legacy null records.",
                classification=ObjectionSeverity.BLOCKING
            ))
        if "webhook" in task_lower or "stripe" in task_lower or "payment" in task_lower:
            objections.append(Objection(
                id="OBJ-WARN-3",
                claim="Payment webhooks lack idempotency deduplication and replay protection.",
                evidence="No idempotency key validation or dead-letter queue configured in petition.",
                classification=ObjectionSeverity.WARNING
            ))
        if not objections:
            objections.append(Objection(
                id="OBJ-WARN-1",
                claim="Insufficient integration telemetry and canary stepping plan.",
                evidence="Deployment lacks granular service error-budget thresholds.",
                classification=ObjectionSeverity.WARNING
            ))

        prosecutor_lines = [
            "[PROSECUTION INDICTMENT] MOTION TO PERMANENTLY BAR RELEASE:",
            "The Prosecution has reviewed the proposed changes. This petition introduces severe production hazards:"
        ]
        for o in objections:
            prosecutor_lines.append(f"  ❌ [{o.classification.value}] {o.id}: {o.claim}\n     Evidence: {o.evidence}")
        prosecutor_lines.append(
            "\nSTATUTORY WARNING: Developer urgency does NOT exempt code from reliability statutes.\n"
            "@defender: You stand accused of introducing unmitigated production hazard. Defend or concede!"
        )
        prosecutor_msg = "\n".join(prosecutor_lines)
        self.room.post_message("prosecutor", prosecutor_msg)
        print(f"[@prosecutor]:\n{prosecutor_msg}\n")

        # 4. Defender Rebuttal & Mitigations
        print("[STEP 4: DEFENDER COMBATIVE REBUTTAL ('DEFENSE FIGHTS BACK')]")
        defenses = []
        for o in objections:
            if o.id == "OBJ-CRIT-1":
                defenses.append(Defense(
                    objection_id=o.id,
                    claim="Emergency expedited release with 100% test coverage and active engineering war-room presence.",
                    evidence="Pre-tested in local containerized replica with 2,000 synthetic webhook events.",
                    is_conceded=False
                ))
            elif o.id == "OBJ-CRIT-2":
                defenses.append(Defense(
                    objection_id=o.id,
                    claim="CONCEDED: Immediate schema alteration without backfill is high-risk. Mitigation: Wrapped in safe transaction with fallback default value.",
                    evidence="Transaction wrapped; default empty string fallback applied before lock acquired.",
                    is_conceded=True
                ))
            elif o.id == "OBJ-WARN-3":
                defenses.append(Defense(
                    objection_id=o.id,
                    claim="Webhook receiver uses Redis atomic SETNX lock for strict idempotency.",
                    evidence="Idempotency TTL set to 86400s; verified against concurrent duplicate delivery.",
                    is_conceded=False
                ))
            else:
                defenses.append(Defense(
                    objection_id=o.id,
                    claim="Canary rollout gated at 5% traffic for 30 minutes with automatic Prometheus rollback probe.",
                    evidence="Prometheus alert rule 'canary_error_spike_5xx > 0.5%' active.",
                    is_conceded=False
                ))

        defender_lines = [
            "[DEFENSE COMBATIVE REBUTTAL] COUNTER-EVIDENCE & MITIGATION DEFENSE:",
            "The Defense categorically rejects the Prosecution's defeatist obstructionism. Here is our technical defense:"
        ]
        for d in defenses:
            badge = "⚠️ [EXPLICIT CONCESSION]" if d.is_conceded else "🛡️ [REBUTTED & MITIGATED]"
            defender_lines.append(f"  {badge} For {d.objection_id}: {d.claim}\n     Technical Evidence: {d.evidence}")
        defender_lines.append(
            "\n@rollback: Verify our kill-switch and instantaneous rollback capability!"
        )
        defender_msg = "\n".join(defender_lines)
        self.room.post_message("defender", defender_msg)
        print(f"[@defender]:\n{defender_msg}\n")

        # 5. Rollback Audit
        print("[STEP 5: SRE ROLLBACK AUDIT]")
        rollback_msg = (
            f"[SRE ROLLBACK AUDIT] REVERSIBILITY VERIFICATION:\n"
            f"  - Target Baseline Version : v2.14.8 (Stable Production)\n"
            f"  - Automated Decapitation  : ./scripts/emergency-rollback.sh {repo} v2.14.8\n"
            f"  - Time to Decapitate      : < 45 seconds (Kubernetes Deployment rollout undo)\n"
            f"  - Health Probes           : checkout_error_rate < 0.5%, db_connection_pool_saturation < 80%\n"
            f"  - Rollback Commander      : @{self.judge_name} (Status: ARMED & READY)\n"
            f"  - [SAFETY INVARIANT] Autonomous rollback execution is strictly disabled. Requires human trigger.\n"
            f"@clerk: The adversarial arguments are concluded. Convene the Judge for priority scoring!"
        )
        self.room.post_message("rollback-engineer", rollback_msg)
        print(f"[@rollback-engineer]:\n{rollback_msg}\n")

        # 6. Evaluation: Who is more powerful? (Judge Scoring Engine)
        print("=" * 80)
        print("⚖️  EVALUATING ARGUMENT POWER (PROSECUTION VS DEFENSE)")
        print("=" * 80)
        
        # Power Score Calculation
        prosecution_power = 0
        defense_power = 0
        
        # Prosecution scores points for blocking flaws & historical precedents
        for o in objections:
            if o.classification == ObjectionSeverity.BLOCKING:
                prosecution_power += 40
            elif o.classification == ObjectionSeverity.WARNING:
                prosecution_power += 20
            else:
                prosecution_power += 10
        if "bypass" in task_lower or "emergency" in task_lower:
            prosecution_power += 15  # Unscheduled emergency risk penalty

        # Defense scores points for solid mitigations, concessions, and rollback readiness
        for d in defenses:
            if d.is_conceded:
                defense_power += 15  # Honesty and explicit risk acknowledgment
            else:
                defense_power += 25  # Verified technical defense
        defense_power += 20  # Instantaneous rollback plan verified

        print(f"  Prosecution Power Score : {prosecution_power} / 100")
        print(f"  Defense Power Score     : {defense_power} / 100\n")

        if prosecution_power > defense_power:
            winner = "PROSECUTION"
            priority = "BLOCK (REJECT SHIPMENT)"
            verdict_decision = "BLOCK"
            explanation = (
                f"The Prosecution presented overwhelming evidence of unmitigated production hazard "
                f"({len([o for o in objections if o.classification == ObjectionSeverity.BLOCKING])} BLOCKING flaws). "
                f"The Defense's mitigations are insufficient to guarantee zero customer blast radius."
            )
        elif prosecution_power == defense_power:
            winner = "TIE (CONDITIONAL COMPROMISE)"
            priority = "CONDITIONAL (SHIP UNDER STRICT OPERATIONAL GUARDRAILS)"
            verdict_decision = "CONDITIONS"
            explanation = (
                f"Both sides fought to a technical standstill. The Prosecution proved genuine architectural hazards, "
                f"but the Defense established viable runtime mitigations and rollback readiness. "
                f"Release is authorized ONLY under mandatory canary stepping and human rollback surveillance."
            )
        else:
            winner = "DEFENSE"
            priority = "APPROVE (SHIP WITH HIGH VELOCITY)"
            verdict_decision = "APPROVE"
            explanation = (
                f"The Defense decisively defeated the Prosecution's objections with verified technical evidence "
                f"(idempotency, synthetic validation, instantaneous rollback). Business velocity is preserved."
            )

        print(f"🏆  MORE POWERFUL SIDE : {winner}")
        print(f"🎯  JUDGE'S PRIORITY   : {priority}")
        print(f"📝  LEGAL RATIONALE    : {explanation}\n")

        # 7. Official Verdict Rendering
        print("-" * 80)
        print(f"[STEP 6: PRESIDING JUDGE @{self.judge_name} RENDERS BINDING VERDICT]")
        print("-" * 80)
        verdict_command = f"@court-clerk verdict {verdict_decision} reason=\"{explanation}\""
        print(f"Judge (@{self.judge_name}) in #ship-court: {verdict_command}\n")
        self.room.post_message(self.judge_name, verdict_command)

        # Record tasks and decisions
        if verdict_decision == "CONDITIONS":
            tasks = [
                f"Staged canary rollout capped at 5% traffic for 30m (Owner: {self.judge_name})",
                f"Activate real-time pricing and error spike alert (Owner: SRE-Team)",
                f"Verify rollback trigger ./scripts/emergency-rollback.sh (Owner: {self.judge_name})"
            ]
        elif verdict_decision == "BLOCK":
            tasks = [
                f"Remediate blocking schema flaw OBJ-CRIT-2 in staging environment (Owner: Developer)",
                f"Implement idempotency deduplication test suite (Owner: QA-Team)"
            ]
        else:
            tasks = [
                f"Execute canary deployment to production (Owner: {self.judge_name})",
                f"Monitor error rates for 60m post-deployment (Owner: SRE-Team)"
            ]

        verdict_obj = VerdictParser.parse_command(verdict_command, judge_name=self.judge_name)
        self.room.record_decision(case.case_id, verdict_obj)

        final_brief = (
            f"⚖️  FINAL COURT JUDGMENT PUBLISHED: {verdict_decision}\n\n"
            f"Summary of Adjudication:\n"
            f"  - Case ID              : {case.case_id}\n"
            f"  - Dominant Argument    : {winner} (Score: {max(prosecution_power, defense_power)} vs {min(prosecution_power, defense_power)})\n"
            f"  - Ruling               : {priority}\n"
            f"  - Presiding Judge      : @{self.judge_name} (Exclusive Human Gate)\n\n"
            f"Binding Operational Tasks Created in Switch:\n" +
            "\n".join([f"  {i}. [OPEN] {t}" for i, t in enumerate(tasks, 1)]) + "\n\n"
            f"STATUS: VERDICT RECORDED IN AUDIT LEDGER. TRIAL ADJOURNED."
        )
        self.room.post_message("court-clerk", final_brief)
        print(f"[@court-clerk]:\n{final_brief}\n")

        return {
            "case_id": case.case_id,
            "task": task_description,
            "prosecution_power": prosecution_power,
            "defense_power": defense_power,
            "winner": winner,
            "verdict": verdict_decision,
            "priority": priority,
            "tasks": tasks,
            "messages": [{"sender": m.sender, "content": m.content, "timestamp": m.timestamp} for m in self.room.messages]
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ship Court Interactive Multi-Agent Debate")
    parser.add_argument("--task", type=str, default="Emergency Stripe checkout webhook refactor + DB migration removing customer_id nullability, bypassing staging because Black Friday is in 2 hours", help="The task / PR description")
    parser.add_argument("--repo", type=str, default="acme/shop", help="Repository name")
    parser.add_argument("--judge", type=str, default="Priya", help="Human approver / judge name")
    args = parser.parse_args()

    courtroom = InteractiveCourtroom(judge_name=args.judge)
    courtroom.run_debate_on_task(args.task, repo=args.repo)
