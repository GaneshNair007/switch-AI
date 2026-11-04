"""Ship Court entry point and Switch webhook listener."""
import sys, argparse
from .case_manager import CaseManager

def run_demo():
    print("=" * 70)
    print("SHIP COURT: No Deploy Survives Cross-Examination")
    print("Flip the Switch Hackathon (Track 01: Best Business Workflow)")
    print("=" * 70 + "\n")

    manager = CaseManager()
    pr_url = "https://github.com/acme/shop/pull/482"
    
    print("[1] Developer in #ship-court:")
    print(f"    @court-clerk open case {pr_url}\n")
    
    case = manager.open_case(pr_url, custom_case_id="SC-0482")
    print(f"[2] Court Clerk:\n    Case {case.case_id} opened.")
    print(f"    Change: dynamic checkout pricing.")
    print(f"    Affected services: {', '.join(case.affected_services)}.")
    print(f"    CI: {case.ci_status}.")
    print(f"    Deployment: {case.deployment_target}.")
    print("    Requesting precedent from Incident Historian...\n")

    result = manager.run_procedural_pipeline(case.case_id, rollback_owner="Priya")
    
    precedents = result["precedents"]
    if precedents:
        p = precedents[0]
        print(f"[3] Incident Historian:\n    Relevant precedent found: {p['incident_id']}.")
        print(f"    A {p['change_type']}-related change on {p['date']} caused {p['symptom']}.")
        print(f"    Impact: {p['impact']}. Required lesson: {p['lesson']}.\n")

    print("[4] Prosecutor (Adversarial Agent):")
    for obj in case.objections:
        print(f"    {obj.id} - {obj.classification.value}: {obj.claim} Evidence: {obj.evidence}")
    print()

    print("[5] Defender:")
    for defn in case.defenses:
        print(f"    For {defn.objection_id}: {defn.claim}")
    print()

    print("[6] Rollback Engineer:")
    rb = case.rollback_plan
    print(f"    Rollback target: {rb.target_version}.")
    print(f"    Command: {rb.command}")
    print(f"    Health checks: {', '.join(rb.health_checks)}.")
    print(f"    Rollback owner: {rb.rollback_owner} (Status: {rb.execution_status.value})\n")

    print("[7] Court Clerk:\n    Case ready for verdict. Unresolved blocking condition: pricing mismatch alert.\n")

    print("[8] Human Release Judge (Exclusive Approver Role):")
    judge_cmd = "@court-clerk verdict CONDITIONS add pricing-mismatch alert; canary 5%; Priya owns rollback"
    print(f"    Priya: {judge_cmd}\n")

    brief = manager.record_verdict(case.case_id, judge_cmd, judge="Priya", is_human=True)
    
    print("[9] Court Clerk:")
    print("    Verdict recorded: SHIP WITH CONDITIONS.")
    print("    Tasks created:")
    for idx, task in enumerate(case.tasks, start=1):
        print(f"    {idx}. {task.description} - owner: {task.owner}")
    print("\n" + "=" * 70)
    print("FINAL RELEASE BRIEF ARTIFACT:")
    print("=" * 70)
    print(brief)
    print("=" * 70)
    print("\nCase status:", case.state.value)

def main():
    parser = argparse.ArgumentParser(description="Ship Court Multi-Agent Release Governance")
    parser.add_argument("--demo", action="store_true", help="Run full example case SC-0482 simulation")
    parser.add_argument("--open-case", type=str, help="Open a specific PR URL")
    args = parser.parse_args()

    if args.demo or not args.open_case:
        run_demo()
    else:
        mgr = CaseManager()
        c = mgr.open_case(args.open_case)
        res = mgr.run_procedural_pipeline(c.case_id)
        print(f"Opened case {c.case_id} across {res['round_count']} procedural rounds.")

if __name__ == "__main__":
    main()
