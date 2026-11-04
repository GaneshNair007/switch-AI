"""Ship Court entry point, CLI runner, and HTTP API server."""
import sys, argparse, json
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

def main():
    parser = argparse.ArgumentParser(description="Ship Court Multi-Agent Release Governance")
    parser.add_argument("--demo", action="store_true", help="Run full example case SC-0482 simulation")
    parser.add_argument("--open-case", type=str, help="Open a specific PR URL")
    parser.add_argument("--serve", action="store_true", help="Start background HTTP server for webhook / REST requests")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for HTTP server")
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP server")
    args = parser.parse_args()

    if args.serve:
        start_server(host=args.host, port=args.port)
    elif args.open_case:
        mgr = CaseManager()
        c = mgr.open_case(args.open_case)
        res = mgr.run_procedural_pipeline(c.case_id)
        print(f"Opened case {c.case_id} across {res['round_count']} procedural rounds.")
    else:
        run_demo()

if __name__ == "__main__":
    main()
