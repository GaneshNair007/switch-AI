"""Ship Court Real 3-Bot Adversarial Debate Engine.
Uses 3 distinct API keys to power 3 real, unscripted LLM agents:
- Bot 1: Prosecutor (The Relentless Adversary) - Groq Key 1
- Bot 2: Defender (The Combative SRE Counsel) - Groq Key 2
- Bot 3: Judge (The Chief Magistrate Arbiter) - Groq Key 3
"""
from __future__ import annotations
import os
import json
import re
import time
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

class LiveCourtroomDebateEngine:
    def __init__(self, env_path: Optional[str] = None):
        self._load_env(env_path)
        self.k_prosecutor = os.environ.get("GROQ_API_KEY", "")
        self.k_defender = os.environ.get("GROQ_API_KEY_FALLBACK_1", self.k_prosecutor)
        self.k_judge = os.environ.get("GROQ_API_KEY_FALLBACK_2", self.k_prosecutor)
        self.model = os.environ.get("DEFAULT_GROQ_MODEL", "qwen/qwen3.8-27b")

    def _load_env(self, env_path: Optional[str] = None):
        if not env_path:
            possible_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(possible_path):
                env_path = possible_path
        if env_path and os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        val = v.strip().strip("'").strip('"')
                        if val:
                            os.environ[k.strip()] = val

    def _call_llm(self, api_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 160, temperature: float = 0.7, role: str = "agent", task_context: str = "") -> Tuple[str, bool]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }).encode("utf-8")

        # Build candidate key list prioritizing the designated agent's key, then fallbacks
        candidate_keys = [api_key]
        for k in [self.k_prosecutor, self.k_defender, self.k_judge]:
            if k and k not in candidate_keys:
                candidate_keys.append(k)

        for attempt, key in enumerate(candidate_keys):
            if not key:
                continue
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ShipCourt/1.0"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        return content, True
            except Exception as e:
                # Brief backoff before rotating to next key
                time.sleep(0.4 * (attempt + 1))
                continue

        # Dynamic fallback tailored to the task context if network/API is completely offline
        task_lower = task_context.lower()
        is_destructive = any(w in task_lower for w in ["drop", "delete", "bypass", "emergency", "destroy", "truncate"])
        is_low_risk = any(w in task_lower for w in ["css", "ui", "typo", "readme", "cache", "redis", "doc"])

        if role == "prosecutor":
            if is_destructive:
                return (
                    f"**PROSECUTION INDICTMENT (Procedural Analysis):**\n"
                    f"* Critical hazard in '{task_context}': Destructive operations risk unrecoverable state loss and downtime.\n"
                    f"* Bypasses standard verification cycles, creating immediate incident severity level 1 risk.\n"
                    f"I move for a strict BLOCK on this petition.", False
                )
            elif is_low_risk:
                return (
                    f"**PROSECUTION INDICTMENT (Procedural Analysis):**\n"
                    f"* While change '{task_context}' is low blast-radius, cache inconsistencies or stale reads could affect downstream consumers.\n"
                    f"* Recommend verifying fallback behavior under simulated cache exhaustion.", False
                )
            else:
                return (
                    f"**PROSECUTION INDICTMENT (Procedural Analysis):**\n"
                    f"* Deployment '{task_context}' introduces architectural concurrency risks and potential connection starvation.\n"
                    f"* Rollback triggers are not pre-tested in staging under production traffic loads.\n"
                    f"Recommend hard canary constraints before rollout.", False
                )
        elif role == "defender":
            if is_destructive:
                return (
                    f"**DEFENSE REBUTTAL (Procedural Analysis):**\n"
                    f"* Concede that destructive changes carry extreme risk; propose taking full point-in-time snapshot before executing.\n"
                    f"* Request conditional window during off-peak scheduled maintenance.", False
                )
            elif is_low_risk:
                return (
                    f"**DEFENSE REBUTTAL (Procedural Analysis):**\n"
                    f"* The proposed change has negligible blast radius and is backed by automatic circuit breaking and graceful fallback.\n"
                    f"* Unit and integration suites pass 100%; velocity should not be artificially bottlenecked.", False
                )
            else:
                return (
                    f"**DEFENSE REBUTTAL (Procedural Analysis):**\n"
                    f"* Concede the blast radius concerns raised by Prosecution; we mitigate via a 5% canary soak for 30 minutes.\n"
                    f"* Automated health probes and 1-click rollback killswitches are primed and verified.", False
                )
        else:
            if is_destructive:
                return (
                    f"PROSECUTION POWER: 95\n"
                    f"DEFENSE POWER: 25\n"
                    f"WINNER: PROSECUTION\n"
                    f"VERDICT: BLOCK\n"
                    f"RATIONALE: Destructive actions on '{task_context}' present unmitigated catastrophic risk to production.\n"
                    f"CONDITIONS:\n"
                    f"1. Mandatory off-peak maintenance window approval from VP of Engineering.\n"
                    f"2. Point-in-time database snapshot verified before any schema execution.\n"
                    f"TASKS:\n"
                    f"- Schedule RFC review for maintenance window (Owner: Architect)\n"
                    f"- Validate backup recovery replica (Owner: DBA-Lead)", False
                )
            elif is_low_risk:
                return (
                    f"PROSECUTION POWER: 30\n"
                    f"DEFENSE POWER: 85\n"
                    f"WINNER: DEFENSE\n"
                    f"VERDICT: APPROVE\n"
                    f"RATIONALE: The Defense decisively demonstrated safety and low blast radius for '{task_context}'.\n"
                    f"CONDITIONS:\n"
                    f"1. Standard canary deployment with 15-minute telemetry soak.\n"
                    f"2. Automated error budget check: 5xx rate < 0.01%.\n"
                    f"TASKS:\n"
                    f"- Deploy to production pipeline (Owner: Priya)\n"
                    f"- Confirm telemetry dashboard green for 30m (Owner: SRE-Team)", False
                )
            else:
                return (
                    f"PROSECUTION POWER: 70\n"
                    f"DEFENSE POWER: 75\n"
                    f"WINNER: DEFENSE\n"
                    f"VERDICT: CONDITIONS\n"
                    f"RATIONALE: Prosecution highlighted real latency hazards, but Defense canary stepping makes safe release possible.\n"
                    f"CONDITIONS:\n"
                    f"1. Canary traffic strictly capped at 5% for 30 minutes before progressive ramp-up.\n"
                    f"2. Automated metric interlock: p99 latency < 250ms and 5xx error rate < 0.01%.\n"
                    f"3. Designated rollback officer on standby with automated 1-click abort trigger.\n"
                    f"TASKS:\n"
                    f"- Deploy to canary replica capped at 5% (Owner: SRE-Team)\n"
                    f"- Arm real-time anomaly alarm and rollback killswitch (Owner: Platform-Ops)", False
                )

    def run_live_trial(self, task_description: str, repo: str = "acme/shop", pr_number: str = "482", judge_name: str = "Priya") -> Dict[str, Any]:
        """Orchestrates the live 3-bot fight, condition synthesis, and adjudication."""

        # -------------------------------------------------------------
        # BOT 1: PROSECUTOR (Attack)
        # -------------------------------------------------------------
        pros_system = (
            "You are the ruthless Prosecutor in Ship Court, an adversarial release courtroom. "
            "Your job is to fiercely attack the proposed deployment. Indict this pull request with ruthless technical scrutiny. "
            "Identify 2 specific architectural hazards or outage modes (locks, timeouts, race conditions, schema locks, unhandled exceptions). "
            "Be aggressive, precise, and combative. Keep response strictly under 90 words formatted as 2 bullet points."
        )
        pros_prompt = f"PROPOSED DEPLOYMENT PETITION:\nRepository: {repo} (PR #{pr_number})\nChange: {task_description}\n\nProsecutor, present your formal indictment!"
        prosecutor_output, pros_live = self._call_llm(self.k_prosecutor, pros_system, pros_prompt, max_tokens=160, temperature=0.7, role="prosecutor", task_context=task_description)

        # Pacing delay to stay well under Groq free-tier OTPM rate limit
        time.sleep(0.8)

        # -------------------------------------------------------------
        # BOT 2: DEFENDER (Rebuttal & Fight Back)
        # -------------------------------------------------------------
        def_system = (
            "You are the brilliant, combative Defense Counsel in Ship Court. "
            "Your job is to fight back against the Prosecutor's indictment and defend the release. "
            "Address the Prosecutor's charges with concrete technical mitigations: rollback safety, automated tests, "
            "canary stepping, transactional guarantees, or graceful degradation. "
            "If an objection is undeniably valid, make an explicit concession while offering an immediate mitigation. "
            "Keep response strictly under 90 words formatted as 2 numbered points."
        )
        def_prompt = (
            f"PROPOSED DEPLOYMENT PETITION:\nChange: {task_description}\n\n"
            f"PROSECUTOR'S INDICTMENT:\n{prosecutor_output}\n\n"
            "Defense Counsel, rebut the Prosecutor point by point and defend the deployment!"
        )
        defender_output, def_live = self._call_llm(self.k_defender, def_system, def_prompt, max_tokens=160, temperature=0.7, role="defender", task_context=task_description)

        # Pacing delay
        time.sleep(0.8)

        # -------------------------------------------------------------
        # BOT 3: JUDGE (Evaluation & Binding Verdict)
        # -------------------------------------------------------------
        judge_system = (
            "You are the Chief Magistrate Judge in Ship Court, presiding over an adversarial software release trial. "
            "You must objectively evaluate the debate between Prosecutor and Defender. "
            "You MUST output your ruling in the exact following structured format:\n\n"
            "PROSECUTION POWER: <score 0-100>\n"
            "DEFENSE POWER: <score 0-100>\n"
            "WINNER: <PROSECUTION or DEFENSE or TIE>\n"
            "VERDICT: <APPROVE or BLOCK or CONDITIONS>\n"
            "RATIONALE: <1 concise sentence explaining who won and why>\n"
            "CONDITIONS:\n"
            "1. <Specific, measurable operational rollout condition>\n"
            "2. <Specific, measurable operational rollout condition>\n"
            "TASKS:\n"
            "- <Action item 1 with Owner>\n"
            "- <Action item 2 with Owner>\n\n"
            "Rules:\n"
            "- If change has unmitigated catastrophic risks, VERDICT must be BLOCK.\n"
            "- If risks can be guarded by canary/alerts/traffic limits, VERDICT must be CONDITIONS.\n"
            "- If defense decisively mitigated all hazards, VERDICT can be APPROVE."
        )
        judge_prompt = (
            f"PROPOSAL ON TRIAL:\n{task_description}\n\n"
            f"PROSECUTION CASE:\n{prosecutor_output}\n\n"
            f"DEFENSE REBUTTAL:\n{defender_output}\n\n"
            f"Presiding Judge (@{judge_name}), evaluate the evidence, assign power scores, and render your binding judgment with explicit conditions!"
        )
        judge_output, judge_live = self._call_llm(self.k_judge, judge_system, judge_prompt, max_tokens=280, temperature=0.2, role="judge", task_context=task_description)

        # Extract structured metrics from Judge
        pros_score = 50
        def_score = 50
        winner = "TIE"
        verdict = "CONDITIONS"

        m_pros = re.search(r"PROSECUTION POWER:\s*(\d+)", judge_output, re.IGNORECASE)
        if m_pros:
            pros_score = int(m_pros.group(1))

        m_def = re.search(r"DEFENSE POWER:\s*(\d+)", judge_output, re.IGNORECASE)
        if m_def:
            def_score = int(m_def.group(1))

        m_winner = re.search(r"WINNER:\s*([A-Za-z]+)", judge_output, re.IGNORECASE)
        if m_winner:
            winner = m_winner.group(1).upper()

        m_verdict = re.search(r"VERDICT:\s*([A-Za-z]+)", judge_output, re.IGNORECASE)
        if m_verdict:
            verdict = m_verdict.group(1).upper()
            if verdict not in ("APPROVE", "BLOCK", "CONDITIONS"):
                verdict = "CONDITIONS"

        # -------------------------------------------------------------
        # Extract explicit CONDITIONS
        # -------------------------------------------------------------
        conditions: List[str] = []
        in_conditions = False
        for line in judge_output.splitlines():
            line_str = line.strip()
            if re.match(r"^CONDITIONS:", line_str, re.IGNORECASE):
                in_conditions = True
                continue
            if in_conditions:
                if re.match(r"^(TASKS:|RATIONALE:|WINNER:|VERDICT:|PROSECUTION POWER:)", line_str, re.IGNORECASE):
                    in_conditions = False
                    continue
                m_cond = re.match(r"^(?:\d+[\.\)]|\-|\*)\s*(.+)$", line_str)
                if m_cond:
                    c_text = m_cond.group(1).strip()
                    c_text = re.sub(r"^\*\*(.+?)\*\*:\s*", r"\1: ", c_text)
                    c_text = re.sub(r"^\*(.+?)\*:\s*", r"\1: ", c_text)
                    if c_text and len(c_text) > 5:
                        conditions.append(c_text)

        # Fallback condition synthesis if LLM returned empty or verdict-specific
        if verdict == "CONDITIONS" and not conditions:
            conditions = [
                "Canary traffic strictly capped at 5% for 30 minutes before progressive ramp-up",
                "Automated metric interlock: p99 latency < 250ms and 5xx error rate < 0.01%",
                f"Designated rollback officer @{judge_name} on standby with automated 1-click abort trigger"
            ]
        elif verdict == "BLOCK" and not conditions:
            conditions = [
                "STRICT BLOCK: Do not deploy to staging or production",
                "Remediate critical architecture hazards identified in Prosecutor's indictment",
                "Re-submit to Ship Court for full cross-examination after fixes pass CI"
            ]
        elif verdict == "APPROVE" and not conditions:
            conditions = [
                "Proceed with standard production release pipeline",
                "Maintain 30-minute post-deployment automated health telemetry monitoring"
            ]

        # Extract tasks
        tasks = []
        in_tasks = False
        for line in judge_output.splitlines():
            line_str = line.strip()
            if re.match(r"^TASKS:", line_str, re.IGNORECASE):
                in_tasks = True
                continue
            if in_tasks:
                if re.match(r"^(CONDITIONS:|RATIONALE:|WINNER:|VERDICT:)", line_str, re.IGNORECASE):
                    in_tasks = False
                    continue
                if line_str.startswith("-") or line_str.startswith("*") or re.match(r"^\d+[\.\)]", line_str):
                    t_text = re.sub(r"^(?:[\-\*]|\d+[\.\)])\s*", "", line_str).strip()
                    if t_text:
                        tasks.append(t_text)

        if not tasks:
            if verdict == "BLOCK":
                tasks = [
                    "Refactor architectural flaw identified by Prosecution (Owner: Developer)",
                    "Deploy to staging replica and verify under load (Owner: QA)"
                ]
            elif verdict == "CONDITIONS":
                tasks = [
                    f"Deploy to canary capped at 5% traffic for 30m (Owner: {judge_name})",
                    "Arm real-time mismatch alarm and SRE rollback trigger (Owner: SRE-Team)"
                ]
            else:
                tasks = [
                    f"Execute production deployment (Owner: {judge_name})",
                    "Monitor health metrics for 60m post-rollout (Owner: SRE-Team)"
                ]

        now = time.time()
        messages = [
            {
                "sender": "court-clerk",
                "content": f"[COURT IN SESSION] DOCKET CASE SC-{pr_number}: Petition to deploy '{task_description}' on {repo}.\nAdversarial cross-examination convened between Prosecutor, Defender, and Chief Magistrate Judge.\nRubber-stamping is strictly prohibited under penalty of contempt.",
                "is_live": True,
                "timestamp": now - 3
            },
            {
                "sender": "prosecutor",
                "content": prosecutor_output,
                "is_live": pros_live,
                "timestamp": now - 2
            },
            {
                "sender": "defender",
                "content": defender_output,
                "is_live": def_live,
                "timestamp": now - 1
            },
            {
                "sender": f"judge-{judge_name}",
                "content": judge_output,
                "is_live": judge_live,
                "timestamp": now
            }
        ]

        all_live = bool(pros_live and def_live and judge_live)

        return {
            "case_id": f"SC-{pr_number}",
            "task": task_description,
            "repo": repo,
            "judge": judge_name,
            "prosecution_power": pros_score,
            "defense_power": def_score,
            "winner": winner,
            "verdict": verdict,
            "conditions": conditions,
            "priority": f"{verdict} ({winner} WON THE DEBATE)",
            "is_live_trial": all_live,
            "prosecutor_is_live": pros_live,
            "defender_is_live": def_live,
            "judge_is_live": judge_live,
            "prosecutor_indictment": prosecutor_output,
            "defender_rebuttal": defender_output,
            "judge_verdict": judge_output,
            "tasks": tasks,
            "messages": messages
        }
