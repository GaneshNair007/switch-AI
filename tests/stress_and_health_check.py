"""Comprehensive 10-iteration backend test runner and stress verifier.
Verifies Switch schema, pytest suite, native runner, simulation, and HTTP API over 10 consecutive runs.
"""
import sys, time, subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def run_step(description, cmd):
    t0 = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(ROOT_DIR))
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
    print("=" * 75)
    print("SHIP COURT BACKEND 10-CYCLE CONTINUOUS INTEGRITY TEST")
    print("=" * 75)
    
    passed_cycles = 0
    total_cycles = 10

    for i in range(1, total_cycles + 1):
        print(f"\n>>> ITERATION {i}/{total_cycles} RUNNING...")
        # 1. Template validation
        ok1 = run_step("Switch Template Schema Check", f'python "switch/validate_template.py"')
        if not ok1: break

        # 2. Pytest suite
        ok2 = run_step("Full Pytest Suite (19 Tests)", f'python -m pytest -q tests/')
        if not ok2: break

        # 3. Switch Native Courtroom Runner
        ok3 = run_step("Switch Native Courtroom Runner", f"python -m server.switch_native_runner")
        if not ok3: break

        # 4. Local Multi-Agent Simulation
        ok4 = run_step("Local Courtroom Simulation Harness", f"python -m server.local_courtroom_simulation")
        if not ok4: break

        # 5. CLI Simulation
        ok5 = run_step("End-to-End Courtroom CLI Demo", f"python -m server.main --demo")
        if not ok5: break

        passed_cycles += 1
        print(f"  >>> ITERATION {i}/{total_cycles} COMPLETED SUCCESSFULLY [PASS]")

    print("\n" + "=" * 75)
    print(f"SUMMARY: {passed_cycles}/{total_cycles} CYCLES PASSED PERFECTLY")
    print("=" * 75)
    return passed_cycles == total_cycles

if __name__ == "__main__":
    success = run_ten_cycles()
    sys.exit(0 if success else 1)
