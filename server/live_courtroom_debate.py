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
import urllib.request
from typing import Dict, Any, List, Optional

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
                        os.environ.setdefault(k.strip(), v.strip())

    def _call_llm(self, api_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 400, temperature: float = 0.7) -> str:
        import time
        url = "https://api.groq.com/openai/v1/chat/completions"
        candidate_models = [self.model, "allam-2-7b", "openai/gpt-oss-20b"]

        for m in candidate_models:
            payload = json.dumps({
                "model": m,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ShipCourt/1.0"
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            except Exception:
                # Try fallback across available keys
                for fb_key in [self.k_prosecutor, self.k_defender, self.k_judge]:
                    if fb_key != api_key:
                        try:
                            req = urllib.request.Request(
                                url,
                                data=payload,
                                headers={
                                    "Authorization": f"Bearer {fb_key}",
                                    "Content-Type": "application/json",
                                    "User-Agent": "ShipCourt/1.0"
                                }
                            )
                            with urllib.request.urlopen(req, timeout=15) as resp:
                                data = json.loads(resp.read().decode("utf-8"))
                                content = data["choices"][0]["message"]["content"].strip()
                                if content:
                                    return content
                        except Exception:
                            continue
            time.sleep(0.3)

        return "[LLM GENERATION FAILED: Rate limit or network timeout. Please retry in a moment.]"

    def run_live_trial(self, task_description: str, repo: str = "acme/shop", pr_number: str = "482", judge_name: str = "Priya") -> Dict[str, Any]:
        """Orchestrates the live 3-bot fight and adjudication."""

        # -------------------------------------------------------------
        # BOT 1: PROSECUTOR (Attack)
        # -------------------------------------------------------------
        pros_system = (
            "You are the ruthless Prosecutor in Ship Court, an adversarial release courtroom. "
            "Your job is to fiercely attack the proposed deployment. Indict this pull request with ruthless technical scrutiny. "
            "Identify 2-3 specific architectural hazards, potential outage modes (locks, timeouts, race conditions, schema locks, unhandled exceptions), "
            "and cite the danger to production reliability. Be aggressive, precise, and combative. Format with clear bullet points."
        )
        pros_prompt = f"PROPOSED DEPLOYMENT PETITION:\nRepository: {repo} (PR #{pr_number})\nChange / Proposal: {task_description}\n\nProsecutor, present your formal indictment!"
        prosecutor_output = self._call_llm(self.k_prosecutor, pros_system, pros_prompt, max_tokens=450, temperature=0.7)

        # -------------------------------------------------------------
        # BOT 2: DEFENDER (Rebuttal & Fight Back)
        # -------------------------------------------------------------
        def_system = (
            "You are the brilliant, combative Defense Counsel in Ship Court. "
            "Your job is to fight back against the Prosecutor's indictment and defend the release. "
            "Address each of the Prosecutor's charges with concrete technical mitigations: rollback safety, automated tests, "
            "canary stepping, transactional guarantees, or graceful degradation. "
            "If an objection is undeniably valid, make an explicit tactical concession while offering an immediate mitigation. "
            "Fight fiercely for engineering progress and velocity without compromising safety."
        )
        def_prompt = (
            f"PROPOSED DEPLOYMENT PETITION:\nChange / Proposal: {task_description}\n\n"
            f"PROSECUTOR'S INDICTMENT:\n{prosecutor_output}\n\n"
            "Defense Counsel, rebut the Prosecutor point by point and defend the deployment!"
        )
        defender_output = self._call_llm(self.k_defender, def_system, def_prompt, max_tokens=450, temperature=0.7)

        # -------------------------------------------------------------
        # BOT 3: JUDGE (Evaluation & Binding Verdict)
        # -------------------------------------------------------------
        judge_system = (
            "You are the Chief Magistrate Judge in Ship Court, presiding over an adversarial software release trial. "
            "You must objectively evaluate the debate between the Prosecutor and Defender. "
            "Determine who made the more technically sound argument. "
            "You MUST output your ruling in the following structured format:\n\n"
            "PROSECUTION POWER: <score 0-100>\n"
            "DEFENSE POWER: <score 0-100>\n"
            "WINNER: <PROSECUTION or DEFENSE or TIE>\n"
            "VERDICT: <APPROVE or BLOCK or CONDITIONS>\n"
            "RATIONALE: <2-3 sentences explaining who won and why>\n"
            "TASKS:\n"
            "- <Action item 1 with Owner>\n"
            "- <Action item 2 with Owner>\n\n"
            "Guidelines:\n"
            "- If the change bypasses staging or has catastrophic unmitigated risks, VERDICT must be BLOCK.\n"
            "- If risks exist but can be guarded by canary/alerts, VERDICT should be CONDITIONS.\n"
            "- If defense decisively mitigated all hazards, VERDICT can be APPROVE."
        )
        judge_prompt = (
            f"PROPOSAL ON TRIAL:\n{task_description}\n\n"
            f"PROSECUTION CASE:\n{prosecutor_output}\n\n"
            f"DEFENSE REBUTTAL:\n{defender_output}\n\n"
            f"Presiding Judge (@{judge_name}), evaluate the evidence, assign power scores, and render your binding judgment!"
        )
        judge_output = self._call_llm(self.k_judge, judge_system, judge_prompt, max_tokens=450, temperature=0.3)

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

        # Extract tasks
        tasks = []
        in_tasks = False
        for line in judge_output.splitlines():
            line_str = line.strip()
            if "TASKS:" in line_str.upper():
                in_tasks = True
                continue
            if in_tasks and line_str.startswith("-"):
                tasks.append(line_str.lstrip("-").strip())
        if not tasks:
            if verdict == "BLOCK":
                tasks = [
                    f"Refactor architectural flaw identified by Prosecution (Owner: Developer)",
                    f"Deploy to staging replica and verify under load (Owner: QA)"
                ]
            elif verdict == "CONDITIONS":
                tasks = [
                    f"Deploy to canary capped at 5% traffic for 30m (Owner: {judge_name})",
                    f"Arm real-time mismatch alarm and SRE rollback trigger (Owner: SRE-Team)"
                ]
            else:
                tasks = [
                    f"Execute production deployment (Owner: {judge_name})",
                    f"Monitor health metrics for 60m post-rollout (Owner: SRE-Team)"
                ]

        import time
        now = time.time()
        messages = [
            {
                "sender": "court-clerk",
                "content": f"[COURT IN SESSION] DOCKET CASE SC-{pr_number}: Petition to deploy '{task_description}' on {repo}.\nAdversarial cross-examination convened between Prosecutor, Defender, and Chief Magistrate Judge.\nRubber-stamping is strictly prohibited under penalty of contempt.",
                "timestamp": now - 3
            },
            {
                "sender": "prosecutor",
                "content": prosecutor_output,
                "timestamp": now - 2
            },
            {
                "sender": "defender",
                "content": defender_output,
                "timestamp": now - 1
            },
            {
                "sender": f"judge-{judge_name}",
                "content": judge_output,
                "timestamp": now
            }
        ]

        return {
            "case_id": f"SC-{pr_number}",
            "task": task_description,
            "repo": repo,
            "judge": judge_name,
            "prosecution_power": pros_score,
            "defense_power": def_score,
            "winner": winner,
            "verdict": verdict,
            "priority": f"{verdict} ({winner} WON THE DEBATE)",
            "prosecutor_indictment": prosecutor_output,
            "defender_rebuttal": defender_output,
            "judge_verdict": judge_output,
            "tasks": tasks,
            "messages": messages
        }
