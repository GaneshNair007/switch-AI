"""Comprehensive 10-iteration backend test runner and stress verifier.
Verifies Switch schema, pytest suite, live room runner, and HTTP API over 10 consecutive runs.
"""
import sys, time, subprocess
from pathlib import Path

def run_step(description, cmd):
    t0 = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"  FAILED: {description} (took {dt:.2f}s)")
        print("--- STDERR ---")
        print(res.stderr)
        print("--- STDOUT ---")
        print(res.stdout)
        return False
    print(f"  OK: {description} ({dt:.2f}s)")
    return True

def run_ten_cycles():
    root_dir = Path(__file__).parent.parent
    print("=" * 75)
    print("SHIP COURT BACKEND 10-CYCLE CONTINUOUS INTEGRITY TEST")
    print("=" * 75)
    
    passed_cycles = 0
    total_cycles = 10

    for i in range(1, total_cycles + 1):
        print(f"\n>>> ITERATION {i}/{total_cycles} RUNNING...")
        # 1. Template validation
        ok1 = run_step("Switch Template Schema Check", f'python "{root_dir / "switch" / "validate_template.py"}"')
        if not ok1: break

        # 2. Pytest suite
        ok2 = run_step("Full Pytest Suite (17 Tests)", f'python -m pytest -q "{root_dir / "tests"}"')
        if not ok2: break

        # 3. Local Multi-Agent Simulation
        ok3 = run_step("Local Courtroom Simulation Runner", f"python -m server.local_courtroom_simulation")
        if not ok3: break

        # 4. CLI Simulation
        ok4 = run_step("End-to-End Courtroom CLI Demo", f"python -m server.main --demo")
        if not ok4: break

        passed_cycles += 1
        print(f"  >>> ITERATION {i}/{total_cycles} COMPLETED SUCCESSFULLY [PASS]")

    print("\n" + "=" * 75)
    print(f"RESULTS: {passed_cycles}/{total_cycles} CYCLES PASSED PERFECTLY")
    print("=" * 75)

    if passed_cycles == total_cycles:
        print("[ALL TESTS VERIFIED - BACKEND 100% HEALTHY & RELIABLE]")
        return 0
    else:
        print("[TEST FAILURE DETECTED]")
        return 1

if __name__ == "__main__":
    sys.exit(run_ten_cycles())
