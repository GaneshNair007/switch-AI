"""Automated Verification Harness for Dynamic Live Courtroom Debate.
Validates that multiple distinct petitions yield diverse, live unscripted LLM generations
and that no static fallback is masking execution.
"""
import os
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.live_courtroom_debate import LiveCourtroomDebateEngine

def main():
    print("=" * 75)
    print("[SHIP COURT] DYNAMIC LIVE COURTROOM VERIFICATION HARNESS")
    print("=" * 75)

    engine = LiveCourtroomDebateEngine()
    print(f"Engine Model: {engine.model}")
    print(f"Key 1 Configured: {bool(engine.k_prosecutor)} (Groq Key 1)")
    print(f"Key 2 Configured: {bool(engine.k_defender)} (Groq Key 2)")
    print(f"Key 3 Configured: {bool(engine.k_judge)} (Groq Key 3)")
    print("-" * 75)

    test_cases = [
        {
            "id": "CASE-1-DESTRUCTIVE",
            "task": "Drop database table user_sessions during active peak hours without backup",
            "repo": "acme/auth-service",
            "expected_verdict": "BLOCK"
        },
        {
            "id": "CASE-2-OPTIMIZED",
            "task": "Add Redis caching to product search queries with 60s TTL and automatic fallback to SQL database",
            "repo": "acme/search-api",
            "expected_verdict": "APPROVE"
        },
        {
            "id": "CASE-3-RISKY-CANARY",
            "task": "Dynamic checkout pricing rollout with ML price optimization model",
            "repo": "acme/checkout-service",
            "expected_verdict": "CONDITIONS"
        }
    ]

    results = []

    for i, tc in enumerate(test_cases, 1):
        print(f"\n[{i}/3] Running Live Trial for: '{tc['task']}'")
        t0 = time.time()
        res = engine.run_live_trial(tc["task"], repo=tc["repo"], pr_number=str(100 + i), judge_name="Priya")
        elapsed = round(time.time() - t0, 2)

        print(f"      Completed in {elapsed}s")
        print(f"      Verdict: {res['verdict']} | Winner: {res['winner']}")
        print(f"      Prosecution Power: {res['prosecution_power']} | Defense Power: {res['defense_power']}")
        print(f"      Live LLM Status: {res.get('is_live_trial', True)}")
        print(f"      Conditions ({len(res['conditions'])}):")
        for c in res['conditions']:
            print(f"        - {c}")

        results.append(res)
        time.sleep(1.0)

    print("\n" + "=" * 75)
    print("VERIFICATION CHECKS:")
    print("=" * 75)

    # Check 1: Live execution
    all_live = all(r["is_live_trial"] for r in results)
    print(f"1. 100% Live LLM Generation: {'[PASSED]' if all_live else '[FAILED]'}")

    # Check 2: Distinct power scores across different cases (not static 75/78)
    scores = [(r["prosecution_power"], r["defense_power"]) for r in results]
    unique_scores = set(scores)
    diverse_scores = len(unique_scores) > 1
    print(f"2. Diverse Power Scores Across Cases: {'[PASSED]' if diverse_scores else '[FAILED]'} (Scores: {scores})")

    # Check 3: Distinct conditions across cases
    cond_sets = [" ".join(r["conditions"][:2]) for r in results]
    unique_conds = set(cond_sets)
    diverse_conds = len(unique_conds) > 1
    print(f"3. Distinct Tailored Conditions: {'[PASSED]' if diverse_conds else '[FAILED]'}")

    # Check 4: No static fallback strings in any output
    no_fallback = not any("Deterministic Fallback" in r["prosecutor_indictment"] for r in results)
    print(f"4. Zero Static Fallbacks: {'[PASSED]' if no_fallback else '[FAILED]'}")

    print("=" * 75)
    if all_live and diverse_scores and diverse_conds and no_fallback:
        print("[SUCCESS] ALL DYNAMIC COURTROOM BENCHMARKS PASSED! Engine is 100% verified live.")
        sys.exit(0)
    else:
        print("[WARNING] Some checks failed. Review logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
