"""Ship Court entry point, CLI runner, and HTTP API server."""
import sys, argparse, json
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from .case_manager import CaseManager
from .local_courtroom_simulation import setup_live_courtroom

class ShipCourtHTTPHandler(BaseHTTPRequestHandler):
    room = None
    mgr = None

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "ship-court-backend",
                "agents_online": len(self.room.sessions) if self.room else 5,
                "version": "1.0.0"
            }).encode("utf-8"))
        elif self.path == "/status":
            self._set_headers(200, "text/plain")
            status_text = self.room.handle_command("!agents-status", "http_client") if self.room else "Room not initialized"
            self.wfile.write(status_text.encode("utf-8"))
        elif self.path == "/tasks":
            self._set_headers(200, "text/plain")
            tasks_text = self.room.handle_command("!tasks", "http_client") if self.room else "No tasks"
            self.wfile.write(tasks_text.encode("utf-8"))
        elif self.path == "/decisions":
            self._set_headers(200, "text/plain")
            dec_text = self.room.handle_command("!decisions", "http_client") if self.room else "No decisions"
            self.wfile.write(dec_text.encode("utf-8"))
        elif self.path == "/metrics":
            self._set_headers(200, "text/plain; version=0.0.4; charset=utf-8")
            cases_count = len(self.mgr.active_cases) if self.mgr else 0
            verdicts_approved = sum(1 for c in self.mgr.active_cases.values() if c.state.value == "APPROVED") if self.mgr else 0
            verdicts_rejected = sum(1 for c in self.mgr.active_cases.values() if c.state.value == "REJECTED") if self.mgr else 0
            sessions_count = len(self.room.sessions) if self.room else 5
            metrics_payload = (
                "# HELP shipcourt_agents_online Total registered AI courtroom agents\n"
                "# TYPE shipcourt_agents_online gauge\n"
                f"shipcourt_agents_online {sessions_count}\n"
                "# HELP shipcourt_cases_total Total courtroom cases handled\n"
                "# TYPE shipcourt_cases_total counter\n"
                f"shipcourt_cases_total {cases_count}\n"
                "# HELP shipcourt_verdicts_total Total verdicts rendered by status\n"
                "# TYPE shipcourt_verdicts_total counter\n"
                f'shipcourt_verdicts_total{{status="APPROVED"}} {verdicts_approved}\n'
                f'shipcourt_verdicts_total{{status="REJECTED"}} {verdicts_rejected}\n'
                "# HELP shipcourt_server_healthy Service health indicator (1 is healthy)\n"
                "# TYPE shipcourt_server_healthy gauge\n"
                "shipcourt_server_healthy 1\n"
            )
            self.wfile.write(metrics_payload.encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if self.path == "/api/case/open":
            pr_url = body.get("pr_url", "https://github.com/acme/shop/pull/482")
            case = self.mgr.open_case(pr_url)
            res = self.mgr.run_procedural_pipeline(case.case_id)
            self._set_headers(200)
            self.wfile.write(json.dumps({"case_id": case.case_id, "state": case.state.value, "pipeline": res}).encode("utf-8"))
        elif self.path == "/api/case/verdict":
            case_id = body.get("case_id")
            command = body.get("command", "")
            judge = body.get("judge", "Priya")
            is_human = body.get("is_human", True)
            try:
                brief = self.mgr.record_verdict(case_id, command, judge=judge, is_human=is_human)
                self._set_headers(200)
                self.wfile.write(json.dumps({"case_id": case_id, "release_brief": brief}).encode("utf-8"))
            except PermissionError as pe:
                self._set_headers(403)
                self.wfile.write(json.dumps({"error": str(pe)}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif self.path == "/webhook":
            sender = body.get("user_name", body.get("sender", "developer"))
            text = body.get("text", body.get("content", ""))
            self.room.post_message(sender, text)
            last_msg = self.room.messages[-1].content if self.room.messages else "ok"
            self._set_headers(200)
            self.wfile.write(json.dumps({"reply": last_msg}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP logs
        return

class ShipCourtServer(ThreadingHTTPServer):
    request_queue_size = 512
    daemon_threads = True

def start_server(host="127.0.0.1", port=8080):
    room = setup_live_courtroom()
    mgr = CaseManager()
    ShipCourtHTTPHandler.room = room
    ShipCourtHTTPHandler.mgr = mgr
    httpd = ShipCourtServer((host, port), ShipCourtHTTPHandler)
    print(f"[SERVER ONLINE] Ship Court HTTP API listening on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER STOPPED]")
        httpd.server_close()

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

def run_interactive_courtroom(initial_task=None):
    from .models import ObjectionSeverity
    print("=" * 75)
    print("⚖️  SHIP COURT: ADVERSARIAL RELEASE ARENA (INTERACTIVE MODE)")
    print("    'No Deploy Survives Cross-Examination'")
    print("    Flip the Switch Hackathon (Track 01: Best Business Workflow)")
    print("=" * 75 + "\n")

    task_desc = initial_task
    if not task_desc:
        print("Enter the proposed change or deployment task to put on trial.")
        print("Examples:")
        print("  1. Dynamic checkout pricing (High risk, pricing mismatch risk)")
        print("  2. Deploy Redis caching layer to cart-service (Cache invalidation risk)")
        print("  3. Database migration on pricing-worker (Worker queue deadlock risk)")
        print("  4. Or type your own custom deployment task!\n")
        try:
            task_desc = input("Task / Proposal [Press Enter for option 1]: ").strip()
        except EOFError:
            task_desc = ""

    if not task_desc or task_desc == "1":
        task_desc = "Dynamic checkout pricing rollout"
    elif task_desc == "2":
        task_desc = "Deploy Redis caching layer to cart-service"
    elif task_desc == "3":
        task_desc = "Database migration on pricing-worker"

    print(f"\n[DOCKETING PROPOSAL]: '{task_desc}'")
    print("-" * 75 + "\n")

    manager = CaseManager()
    pr_url = "https://github.com/acme/shop/pull/482"
    case = manager.open_case(pr_url, task_description=task_desc)

    print(f"📜 [1] COURT CLERK (@clerk):")
    print(f"     Case {case.case_id} docketed on #ship-court.")
    print(f"     Target: {case.change_summary} ({', '.join(case.affected_services)}).")
    print(f"     CI Status: {case.ci_status} | Deployment: {case.deployment_target}.")
    print(f"     @historian: Subpoena historical incident precedent immediately!\n")

    result = manager.run_procedural_pipeline(case.case_id, rollback_owner="Priya")
    precedents = result["precedents"]

    print(f"🏛️ [2] INCIDENT HISTORIAN (@historian):")
    if precedents:
        p = precedents[0]
        print(f"     Forensic Precedent Found: {p['incident_id']} (Severity 1 Outage on {p['date']}).")
        print(f"     Symptom: {p['symptom']} | Blast Radius: {p['impact']}.")
        print(f"     Root Cause: {p['root_cause']}.")
        print(f"     Mandatory Lesson: {p['lesson']}.")
    else:
        print("     No identical precedent found; proceed with heightened adversarial scrutiny.")
    print(f"     @prosecutor: Indict this proposal with maximum scrutiny!\n")

    print(f"⚔️ [3] PROSECUTOR (@prosecutor):")
    print("     The Prosecution moves to permanently bar this release under the following charges:")
    for obj in case.objections:
        print(f"     • [{obj.classification.value}] {obj.id}: {obj.claim}")
        print(f"       Evidence: {obj.evidence}")
    print(f"     @defender: Rebut each objection factually or state 'CONCEDED'!\n")

    print(f"🛡️ [4] DEFENDER (@defender):")
    print("     The Defense presents counter-evidence and explicit concessions:")
    for d in case.defenses:
        badge = "[CONCEDED]" if d.is_conceded else "[MITIGATED]"
        print(f"     • {badge} {d.objection_id}: {d.claim}")
        print(f"       Evidence: {d.evidence}")
    print(f"     @rollback: Audit reversibility and confirm our fail-safe decapitation!\n")

    print(f"🔄 [5] ROLLBACK ENGINEER (@rollback):")
    rb = case.rollback_plan
    print(f"     Rollback Target: {rb.target_version} (Current: {rb.current_version})")
    print(f"     Decapitation Command: {rb.command}")
    print(f"     Health Probes: {', '.join(rb.health_checks)}")
    print(f"     Rollback Commander: {rb.rollback_owner} (Status: {rb.execution_status.value})")
    print(f"     SAFETY INTERLOCK: Autonomous execution is disabled; human approval required.")
    print(f"     @clerk: Arguments concluded. Convene the Release Judge!\n")

    # CLERK WEIGHS THE BATTLE (LEVERAGE / POWER ASSESSMENT)
    unresolved_blocking = [o for o in case.objections if o.classification == ObjectionSeverity.BLOCKING]
    conceded_count = sum(1 for d in case.defenses if d.is_conceded)
    mitigated_count = len(case.defenses) - conceded_count

    print("=" * 75)
    print("⚖️  CLERK'S ADVERSARIAL LEVERAGE ANALYSIS (WHO HAS MORE POWER?)")
    print("=" * 75)
    print(f"  • PROSECUTION POWER: Established {len(unresolved_blocking)} BLOCKING vulnerability(ies).")
    print(f"  • DEFENSE POWER: Rebutted {mitigated_count} charge(s), but entered {conceded_count} CONCESSION(S).")
    if conceded_count > 0:
        print(f"  • MAGISTRATE RULING: The PROSECUTION holds superior leverage on unmitigated risks!")
        print(f"    Judge Recommendation: Give priority to the prosecution's concerns by issuing")
        print(f"    CONDITIONS (require missing alert / canary stepping) or BLOCK.")
    else:
        print(f"  • MAGISTRATE RULING: The DEFENSE holds superior leverage!")
        print(f"    Judge Recommendation: Defense has mitigated architectural hazards; APPROVE is viable.")
    print("-" * 75 + "\n")

    print("⚖️  CASE IS AWAITING HUMAN VERDICT.")
    print("Release Judge, what is your binding ruling?")
    print("  Option 1: @court-clerk verdict APPROVE")
    print("  Option 2: @court-clerk verdict BLOCK reason=\"<reason>\"")
    print("  Option 3: @court-clerk verdict CONDITIONS <cond 1>; <cond 2>; <owner> owns rollback")
    print("  (Shortcuts accepted: '@clerk approve', '@clerk block because ...', '@clerk conditions: ...')\n")

    try:
        user_cmd = input("Your Verdict > ").strip()
    except EOFError:
        user_cmd = "@clerk conditions: add monitoring alert; canary 5%; Priya owns rollback"

    if not user_cmd:
        user_cmd = "@clerk conditions: add monitoring alert; canary 5%; Priya owns rollback"

    print(f"\n[RECORDING VERDICT]: {user_cmd}\n")
    brief = manager.record_verdict(case.case_id, user_cmd, judge="Priya", is_human=True)

    print("=" * 75)
    print("FINAL SIGNED RELEASE BRIEF ARTIFACT:")
    print("=" * 75)
    print(brief)
    print("=" * 75)
    print(f"\nFinal Case State: {case.state.value}")
    print(f"Switch Tasks Created: {len(case.tasks)}")
    for i, t in enumerate(case.tasks, 1):
        print(f"  Task {i}: {t.description} (Owner: {t.owner})")
    print("\n[COURT ADJOURNED] Verdict recorded into immutable Switch state.")

def run_courtroom(mode: str):
    import os
    if mode == "live":
        if not os.getenv("SWITCH_API_TOKEN"):
            raise RuntimeError(
                "LIVE MODE REQUIRES SWITCH_API_TOKEN.\n"
                "Refusing to run simulated courtroom in live mode.\n"
                "Set $env:SWITCH_API_TOKEN and ensure Switch Console / bridge is running."
            )
        from .switch_native_runner import SwitchNativeCourtroom
        runner = SwitchNativeCourtroom()
        return runner.run_case()
    elif mode == "simulation":
        from .local_courtroom_simulation import run_live_demonstration
        return run_live_demonstration()
    else:
        raise ValueError(f"Unknown mode '{mode}'. mode must be 'live' or 'simulation'.")

def main():
    parser = argparse.ArgumentParser(description="Ship Court Multi-Agent Release Governance")
    parser.add_argument("--mode", choices=["live", "simulation"], default="simulation", help="Execution mode: 'live' (requires Switch API & token) or 'simulation' (local harness)")
    parser.add_argument("--demo", action="store_true", help="Run full example case SC-0482 in simulation mode")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run interactive trial where you enter the task and issue the verdict")
    parser.add_argument("--task", type=str, help="Specify task or change description directly for courtroom trial")
    parser.add_argument("--open-case", type=str, help="Open a specific PR URL")
    parser.add_argument("--serve", action="store_true", help="Start background HTTP server for webhook / REST requests")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for HTTP server")
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP server")
    args = parser.parse_args()

    if args.serve:
        start_server(host=args.host, port=args.port)
    elif args.mode == "live":
        run_courtroom("live")
    elif args.interactive or args.task:
        run_interactive_courtroom(initial_task=args.task)
    elif args.open_case:
        mgr = CaseManager()
        c = mgr.open_case(args.open_case)
        res = mgr.run_procedural_pipeline(c.case_id)
        print(f"Opened case {c.case_id} across {res['round_count']} procedural rounds.")
    else:
        run_courtroom("simulation")

if __name__ == "__main__":
    main()
