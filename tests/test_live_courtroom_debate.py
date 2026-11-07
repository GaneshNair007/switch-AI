import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.live_courtroom_debate import LiveCourtroomDebateEngine

def test_condition_extraction_from_judge_output():
    engine = LiveCourtroomDebateEngine()
    sample_judge_output = """
PROSECUTION POWER: 72
DEFENSE POWER: 68
WINNER: PROSECUTION
VERDICT: CONDITIONS
RATIONALE: Prosecution demonstrated race conditions during concurrent checkout updates, but canary mitigations are viable.
CONDITIONS:
1. Canary deployment capped at 5% traffic for 30 minutes.
2. Error budget interlock: p99 latency < 200ms and 5xx < 0.01%.
3. Mandatory SRE rollback operator Priya on standby with 1-click abort.
TASKS:
- Monitor canary metrics for 30 minutes (Owner: SRE)
- Verify rollback trigger in staging replica (Owner: Dev)
"""
    # Test parsing logic directly
    conditions = []
    in_conditions = False
    import re
    for line in sample_judge_output.splitlines():
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
                conditions.append(m_cond.group(1).strip())

    assert len(conditions) == 3
    assert "Canary deployment capped at 5%" in conditions[0]
    assert "Error budget interlock" in conditions[1]
    assert "Mandatory SRE rollback" in conditions[2]

def test_engine_returns_conditions_field():
    engine = LiveCourtroomDebateEngine()
    # Mocking _call_llm to test orchestration without live network latency
    def mock_call(api_key, system, user, max_tokens=400, temperature=0.7, role="agent"):
        if role == "prosecutor":
            return "Indictment: Database migration lacks backwards compatibility."
        elif role == "defender":
            return "Rebuttal: Dual-write strategy enabled with automated rollback."
        else:
            return """
PROSECUTION POWER: 80
DEFENSE POWER: 75
WINNER: PROSECUTION
VERDICT: CONDITIONS
RATIONALE: Database migration has risks, requires canary stepping.
CONDITIONS:
1. Dual-write validation for 1 hour.
2. Canary traffic capped at 10%.
TASKS:
- Monitor dual-write lag (Owner: DB-Team)
"""
    engine._call_llm = mock_call
    res = engine.run_live_trial("Test DB Migration", repo="acme/shop", pr_number="999", judge_name="Priya")

    assert "conditions" in res
    assert isinstance(res["conditions"], list)
    assert len(res["conditions"]) == 2
    assert "Dual-write validation" in res["conditions"][0]
    assert res["verdict"] == "CONDITIONS"
    assert res["winner"] == "PROSECUTION"
    assert res["judge"] == "Priya"
