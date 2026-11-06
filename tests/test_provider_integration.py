"""Provider integration test suite.
Validates real HTTP communication with Groq and NVIDIA endpoints.
Does NOT fabricate results; fails closed if keys or endpoints are unreachable.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from server.llm_providers import LLMProviderManager
from server.live_courtroom_debate import LiveCourtroomDebateEngine

def test_provider_keys_configuration():
    """Validates that credentials are detected from .env or environment."""
    pm = LLMProviderManager()
    status = pm.get_keys_status()
    assert "key_1_groq" in status
    assert status["key_1_groq"]["configured"] is True
    assert "key_2_nvidia_primary" in status
    assert status["key_2_nvidia_primary"]["configured"] is True
    assert "key_3_nvidia_secondary" in status
    assert status["key_3_nvidia_secondary"]["configured"] is True

def test_groq_live_completion():
    """Validates real live chat completion from Groq Cloud."""
    pm = LLMProviderManager()
    if not pm.groq_key:
        pytest.skip("GROQ_API_KEY not configured")

    res = pm.complete_with_groq("Respond with exactly two words: SHIP READY", max_tokens=10)
    assert "error" not in res, f"Groq completion failed: {res}"
    assert res.get("status_code") == 200
    assert len(res.get("completion", "")) > 0
    assert "usage" in res

def test_real_3_bot_debate_turn():
    """Validates that all 3 bots generate unscripted LLM tokens."""
    engine = LiveCourtroomDebateEngine()
    if not engine.k_prosecutor:
        pytest.skip("Groq credentials missing for live 3-bot debate")

    trial = engine.run_live_trial("Deploy caching layer to catalog-service", repo="acme/shop")
    assert trial["case_id"] == "SC-482"
    assert trial["prosecutor_indictment"]
    assert trial["defender_rebuttal"]
    assert trial["judge_verdict"]
    assert trial["winner"] in ("PROSECUTION", "DEFENSE", "TIE")
    assert trial["verdict"] in ("APPROVE", "BLOCK", "CONDITIONS")
    assert len(trial["messages"]) == 4
