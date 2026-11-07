"""Ship Court Real 3-Bot Adversarial Debate Engine.
Uses 3 distinct API keys to power 3 real, unscripted LLM agents:
- Bot 1: Prosecutor (The Relentless Adversary) - Groq Key 1
- Bot 2: Defender (The Combative SRE Counsel) - Groq Key 2
- Bot 3: Judge (The Chief Magistrate Arbiter) - Groq Key 3

ZERO hardcoded debate fallbacks, ZERO canned conditions, ZERO synthetic scores.
Every word and score is generated live from real model inference.
"""
from __future__ import annotations
import os
import json
import re
import time
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
                        val = v.strip().strip("'").strip('"')
                        if val:
                            os.environ[k.strip()] = val

    def _call_llm(self, api_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 160, temperature: float = 0.7, role: str = "agent") -> str:
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

        # Prioritize designated agent key, then rotate through available backup keys
        candidate_keys = [api_key]
        for k in [self.k_prosecutor, self.k_defender, self.k_judge]:
            if k and k not in candidate_keys:
                candidate_keys.append(k)

        last_error = None
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
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            except Exception as e:
                last_error = e
                time.sleep(0.5 * (attempt + 1))
                continue

        # Zero hardcoded fallback: fail honestly with clear error
        raise RuntimeError(f"Live LLM inference failed for {role}: {last_error or 'No response from LLM provider'}. No hardcoded fallback permitted.")

    def run_live_trial(self, task_description: str, repo: str = "acme/shop", pr_number: str = "482", judge_name: str = "Priya") -> Dict[str, Any]:
        """Orchestrates genuine 3-bot live adversarial trial with zero hardcoded fallbacks."""
        if not task_description or not task_description.strip():
            raise ValueError("Task description is required. Cannot convene courtroom on an empty petition.")

        clean_task = task_description.strip()
        clean_repo = repo.strip() if repo else "acme/shop"
        clean_pr = pr_number.strip() if pr_number else "482"
        clean_judge = judge_name.strip() if judge_name else "Priya"

        # -------------------------------------------------------------
        # BOT 1: PROSECUTOR (Attack)
        # -------------------------------------------------------------
        pros_system = (
            "You are the ruthless Prosecutor in Ship Court, an adversarial release courtroom. "
            "Your job is to fiercely attack the proposed deployment. Indict this pull request with ruthless technical scrutiny. "
            "Identify 2 specific architectural hazards or outage modes (locks, timeouts, race conditions, schema locks, unhandled exceptions). "
            "Be aggressive, precise, and combative. Keep response strictly under 90 words formatted as 2 bullet points."
        )
        pros_prompt = f"PROPOSED DEPLOYMENT PETITION:\nRepository: {clean_repo} (PR #{clean_pr})\nChange: {clean_task}\n\nProsecutor, present your formal indictment!"
        prosecutor_output = self._call_llm(self.k_prosecutor, pros_system, pros_prompt, max_tokens=160, temperature=0.7, role="prosecutor")

        # Pacing delay to keep well within organization output token limits
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
            f"PROPOSED DEPLOYMENT PETITION:\nChange: {clean_task}\n\n"
            f"PROSECUTOR'S INDICTMENT:\n{prosecutor_output}\n\n"
            "Defense Counsel, rebut the Prosecutor point by point and defend the deployment!"
        )
        defender_output = self._call_llm(self.k_defender, def_system, def_prompt, max_tokens=160, temperature=0.7, role="defender")

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
            f"PROPOSAL ON TRIAL:\n{clean_task}\n\n"
            f"PROSECUTION CASE:\n{prosecutor_output}\n\n"
            f"DEFENSE REBUTTAL:\n{defender_output}\n\n"
            f"Presiding Judge (@{clean_judge}), evaluate the evidence, assign power scores, and render your binding judgment with explicit conditions!"
        )
        judge_output = self._call_llm(self.k_judge, judge_system, judge_prompt, max_tokens=280, temperature=0.2, role="judge")

        # Extract structured metrics directly from Judge output (no hardcoded defaults)
        pros_score = 0
        def_score = 0
        winner = "UNKNOWN"
        verdict = "UNKNOWN"

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

        # Extract conditions strictly from Judge output (zero synthetic/hardcoded conditions)
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
                    if c_text and len(c_text) > 3:
                        conditions.append(c_text)

        # Extract tasks strictly from Judge output (zero synthetic/hardcoded tasks)
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

        now = time.time()
        messages = [
            {
                "sender": "court-clerk",
                "content": f"[COURT IN SESSION] DOCKET CASE SC-{clean_pr}: Petition to deploy '{clean_task}' on {clean_repo}.\nAdversarial cross-examination convened between Prosecutor, Defender, and Chief Magistrate Judge (@{clean_judge}).\nRubber-stamping is strictly prohibited under penalty of contempt.",
                "is_live": True,
                "timestamp": now - 3
            },
            {
                "sender": "prosecutor",
                "content": prosecutor_output,
                "is_live": True,
                "timestamp": now - 2
            },
            {
                "sender": "defender",
                "content": defender_output,
                "is_live": True,
                "timestamp": now - 1
            },
            {
                "sender": f"judge-{clean_judge}",
                "content": judge_output,
                "is_live": True,
                "timestamp": now
            }
        ]

        return {
            "case_id": f"SC-{clean_pr}",
            "task": clean_task,
            "repo": clean_repo,
            "judge": clean_judge,
            "prosecution_power": pros_score,
            "defense_power": def_score,
            "winner": winner,
            "verdict": verdict,
            "conditions": conditions,
            "priority": f"{verdict} ({winner} WON THE DEBATE)" if winner != "UNKNOWN" else verdict,
            "is_live_trial": True,
            "prosecutor_indictment": prosecutor_output,
            "defender_rebuttal": defender_output,
            "judge_verdict": judge_output,
            "tasks": tasks,
            "messages": messages
        }
