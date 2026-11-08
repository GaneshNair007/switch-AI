"""Ship Court entry point, CLI runner, and HTTP API server."""
import os, sys, argparse, json
from pathlib import Path

# Explicitly load .env from project root before anything else
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                val = v.strip().strip("'").strip('"')
                if val:
                    os.environ[k.strip()] = val

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from .case_manager import CaseManager
from .local_courtroom_simulation import setup_live_courtroom
from .dashboard_html import HTML_DASHBOARD
from .llm_providers import LLMProviderManager
from .interactive_courtroom import InteractiveCourtroom

llm_manager = LLMProviderManager()

class ShipCourtHTTPHandler(BaseHTTPRequestHandler):
    room = None
    mgr = None
    workflow = None
    discord = None

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "same-origin")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers(200, "text/html; charset=utf-8")

    def _json_response(self, status, payload):
        from .store import encode
        self._set_headers(status)
        self.wfile.write(json.dumps(payload, default=encode).encode('utf-8'))

    def _principal(self):
        from .hq_http import principal
        return principal(self)

    def do_GET(self):
        from .hosting import validate_host
        try:validate_host(self)
        except PermissionError:
            self._json_response(403,{'error':'Unexpected request host'});return
        from .hq_http import get
        if get(self): return
        if self.path in ('/api/keys', '/status', '/tasks', '/decisions'):
            try:
                (self.workflow or self.mgr).authorization.require(self._principal(),role='operator')
            except PermissionError:
                self._json_response(403,{'error':'Authenticated operator required'})
                return
        if self.path.startswith('/api/v1/agents/') or self.path.startswith('/api/v1/approvals/'):
            try:
                principal = self._principal()
                if self.path.startswith('/api/v1/agents/') and self.path.endswith('/assignment'):
                    result = self.workflow.scope.assignment(self.path.split('/')[-2], principal)
                elif self.path.startswith('/api/v1/approvals/'):
                    result = self.workflow.scope.status(self.path.split('/')[-1], principal)
                else:
                    raise KeyError('Unknown route')
                self._json_response(200, result)
            except PermissionError:
                self._json_response(403, {'error': 'Scoped hook identity required'})
            except KeyError:
                self._json_response(404, {'error': 'Not found'})
            return
        if self.path in ('/api/cases', '/api/audit/events', '/api/floor/requests', '/api/readiness'):
            try:
                if not self.workflow:
                    raise RuntimeError('Workflow not initialized')
                principal = self._principal()
                self.workflow.authorization.require(principal, role='operator')
                if self.path == '/api/cases':
                    result = self.workflow.workspace.snapshot(principal)['cases']
                elif self.path == '/api/audit/events':
                    result = self.workflow.workspace.snapshot(principal)['audit']
                elif self.path == '/api/floor/requests':
                    result = self.workflow.workspace.snapshot(principal)['floor']
                else:
                    result = {'github_configured': bool(os.getenv('GITHUB_TOKEN')), 'groq_configured': bool(os.getenv('GROQ_API_KEY')),
                              'switch_configured': bool(json.loads(os.getenv('SWITCH_CLIENTS', '[]'))), 'discord_configured': bool(os.getenv('DISCORD_BOT_TOKEN') or os.getenv('DISCORD_PUBLIC_KEY')),
                              'switch_agents': [{'role':worker.role,'connected':worker.client.connected,'receiver_running':thread.is_alive(),
                                  'runtime':getattr(getattr(worker,'runtime',None),'runtime_type','workflow')} for worker,thread in getattr(self.workflow,'switch_workers',[])],
                              'live_integrations_verified': False}
                self._json_response(200, result)
            except PermissionError:
                self._json_response(403, {'error': 'Authentication and operator role required'})
            except Exception as exc:
                self._json_response(400, {'error': str(exc)})
            return
        if self.path in ("/", "/dashboard", "/ui"):
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
        elif self.path.startswith("/assets/"):
            asset_name = os.path.basename(self.path.split("?")[0])
            asset_path = Path(__file__).resolve().parent.parent / "assets" / asset_name
            if asset_path.exists() and asset_path.is_file():
                import mimetypes
                content_type = mimetypes.guess_type(asset_name)[0] or 'application/octet-stream'
                self._set_headers(200, content_type)
                with open(asset_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(b"Not Found")
        elif self.path == "/api/keys":
            self._set_headers(200)
            self.wfile.write(json.dumps(llm_manager.get_keys_status(), indent=2).encode("utf-8"))
        elif self.path == "/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "ship-court-backend",
                "agents_online": sum(1 for w,t in getattr(self.workflow,"switch_workers",[]) if w.client.connected and t.is_alive()),
                "version": "1.0.0",
                "api_keys": llm_manager.get_keys_status()
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
            sessions_count = sum(w.client.connected and t.is_alive() for w,t in getattr(self.workflow,'switch_workers',[]))
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
        from .hosting import validate_host
        try:validate_host(self)
        except PermissionError:
            self._json_response(403,{'error':'Unexpected request host'});return
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if not 0 <= content_length <= 1048576:
                self._json_response(413, {'error': 'Request too large'})
                return
            post_data = self.rfile.read(content_length) if content_length else b'{}'
            body = json.loads(post_data)
            if not isinstance(body, dict):
                raise ValueError('JSON object required')
        except (ValueError, UnicodeDecodeError):
            self._json_response(400, {'error': 'Invalid JSON request'})
            return
        from .hq_http import post
        if post(self, body): return
        if self.path == '/discord/interactions':
            if not self.discord:
                self._json_response(503, {'error': 'Discord application is not configured'})
                return
            try:
                result = self.discord.handle(post_data, self.headers.get('X-Signature-Ed25519', ''), self.headers.get('X-Signature-Timestamp', ''))
                self._json_response(200, result)
            except PermissionError:
                self._json_response(401, {'error': 'Invalid Discord identity or signature'})
            except (ValueError, KeyError, TypeError):
                self._json_response(400, {'error': 'Invalid interaction'})
            return
        routes = ('/api/cases', '/api/cases/review', '/api/verdicts', '/api/github/plan', '/api/github/execute',
                  '/api/v1/approvals', '/api/scope/assignments', '/api/scope/decide', '/api/voice/action', '/api/research', '/api/simulations', '/api/staging/measure', '/api/cases/attach', '/api/meetings/start', '/api/meetings/consent', '/api/meetings/transcript', '/api/meetings/decision', '/api/meetings/end', '/api/meetings/tasks', '/api/meetings/tasks/update',
                  '/api/floor/requests', '/api/floor/grants', '/api/floor/release', '/api/floor/dismiss', '/api/v1/violations')
        if self.path in routes:
            try:
                if not self.workflow:
                    raise RuntimeError('Workflow not initialized')
                principal = self._principal()
                service = self.workflow
                if self.path == '/api/cases':
                    result = service.open_case(body['pr_url'], body['services'], principal)
                elif self.path == '/api/v1/approvals':
                    result = service.scope.request(body, principal)
                elif self.path == '/api/scope/assignments':
                    result = service.scope.set_assignment(body, principal)
                elif self.path == '/api/scope/decide':
                    result = service.scope.decide(body['request_id'], body['approve'], principal)
                elif self.path == '/api/voice/action':
                    from .voice_bridge import VoiceBridge
                    result = VoiceBridge(service, os.getenv('DISCORD_GUILD_ID', ''), json.loads(os.getenv('DISCORD_MEMBERS', '{}'))).handle(principal, body)
                elif self.path == '/api/research':
                    result = service.research.verify(body['claim'], body['urls'], principal, body['correlation_id'])
                elif self.path == '/api/simulations':
                    service.authorization.require(principal, role='operator')
                    result = service.parallel_earth.run_simulation(service.cases[body['case_id']],
                        estimated_downtime_minutes=body.get('downtime_minutes', 15),
                        synthetic_requests=body.get('requests', 1000), failure_probability=body.get('failure_probability', .01), seed=body.get('seed', 0))
                    service.store.put('simulation', body['case_id'], result)
                elif self.path == '/api/staging/measure':
                    service.authorization.require(principal, scope='staging:measure')
                    endpoint = os.getenv('SHIPCOURT_STAGING_URL')
                    if not endpoint:
                        raise ValueError('No staging endpoint configured by the operator')
                    from .staging import measure_staging
                    result = measure_staging(endpoint, body.get('samples', 10))
                    service.store.event('staging.measured', body.get('case_id', 'staging'), principal.subject, result)
                elif self.path == '/api/cases/attach':
                    result = service.attach_pull_request(body['case_id'], body['pr_url'], body['services'], principal)
                elif self.path == '/api/meetings/start':
                    result = service.meetings.start(body['title'], principal, body.get('mode', 'Professional Colleague'))
                elif self.path == '/api/meetings/consent':
                    if type(body['enabled']) is not bool:
                        raise ValueError('Consent must be a boolean')
                    result = service.meetings.consent(body['meeting_id'], principal, body['enabled'])
                elif self.path == '/api/meetings/transcript':
                    result = service.meetings.transcript(body['meeting_id'], body['text'], principal, body['event_id'])
                elif self.path == '/api/meetings/decision':
                    result = service.meetings.decision(body['meeting_id'], body['text'], principal, body.get('evidence_refs'))
                elif self.path == '/api/meetings/tasks':
                    result = service.meetings.assign_task(body['meeting_id'], body['description'], body['owner_id'], principal, body.get('evidence_refs'))
                elif self.path == '/api/meetings/tasks/update':
                    result = service.meetings.update_task(body['meeting_id'], body['task_id'], body['status'], principal)
                elif self.path == '/api/meetings/end':
                    result = service.meetings.end(body['meeting_id'], principal)
                elif self.path == '/api/cases/review':
                    result = service.review(body['case_id'], principal)
                elif self.path == '/api/verdicts':
                    result = {'release_brief': service.decide(body['case_id'], body['command'], principal)}
                elif self.path == '/api/github/plan':
                    import hashlib
                    plan = service.github_plan(body['case_id'], principal)
                    result = {'plan': plan, 'plan_hash': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()}
                elif self.path == '/api/github/execute':
                    result = service.execute_github(body['case_id'], principal, body['plan_hash'])
                elif self.path == '/api/v1/violations':
                    result = service.ingest_violation(body, principal)
                elif self.path == '/api/floor/requests':
                    service.authorization.require(principal, role='operator')
                    if "now" in body:
                        raise ValueError("Client-controlled timestamps are not allowed")
                    result = service.floor_controller.raise_hand(**body)
                elif self.path == '/api/floor/grants':
                    result = service.floor_controller.grant_floor(body['request_id'], principal)
                else:
                    req = service.floor_controller.requests[body['request_id']]
                    service.authorization.require(principal, scope=f'meeting:{req.meeting_id}:floor')
                    if self.path == '/api/floor/release':
                        service.floor_controller.release(req.request_id)
                    else:
                        service.floor_controller.dismiss(req.request_id, principal, interrupt=body.get('interrupt', False))
                    result = {'state': req.state.value}
                self._json_response(200, result)
            except PermissionError:
                self._json_response(403, {'error': 'Authenticated identity with required role and scope required'})
            except (ValueError, KeyError, TypeError) as exc:
                self._json_response(400, {'error': str(exc)})
            except Exception as exc:
                self._json_response(502, {'error': type(exc).__name__, 'detail': 'Operation failed; inspect local audit and service configuration'})
            return
        # All legacy mutation/cost-incurring routes require a provisioned operator.
        try:
            principal = self._principal()
            self.mgr.authorization.require(principal, role='operator')
        except PermissionError:
            self._json_response(403, {'error': 'Authenticated operator required'})
            return

        if self.path == "/api/debate":
            task_desc = str(body.get("task", "")).strip()
            if not task_desc:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Task description is required. No default or hardcoded task will be assumed."}).encode("utf-8"))
                return
            repo = str(body.get("repo", "")).strip() or "unspecified-repository"
            judge = str(body.get("judge", "")).strip() or "Release-Judge"
            from .live_courtroom_debate import LiveCourtroomDebateEngine
            engine = LiveCourtroomDebateEngine()
            try:
                result = engine.run_live_trial(task_desc, repo=repo, judge_name=judge)
                self._set_headers(200)
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e), "is_live_trial": False}).encode("utf-8"))
        elif self.path == "/api/llm/complete":
            prompt = body.get("prompt", "Analyze risks of deploying dynamic pricing without an alert.")
            system_prompt = body.get("system", "You are the Ship Court Clerk.")
            max_tokens = int(body.get("max_tokens", 150))
            res = llm_manager.complete_with_groq(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
            self._set_headers(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
        elif self.path == "/api/case/open":
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
                principal = self._principal()
                brief = self.mgr.record_verdict(case_id, command, principal=principal)
                self._set_headers(200)
                self.wfile.write(json.dumps({"case_id": case_id, "release_brief": brief}).encode("utf-8"))
            except PermissionError as pe:
                self._set_headers(403)
                self.wfile.write(json.dumps({"error": str(pe)}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif self.path == "/webhook":
            sender = principal.subject
            text = body.get("text", body.get("content", ""))
            self.room.post_message(sender, text, principal=principal)
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
    # Windows SO_REUSEADDR can allow two live servers to bind the same port.
    allow_reuse_address = os.name != 'nt'

def start_server(host="127.0.0.1", port=8080):
    from .hosting import public_origin
    public_origin()  # Refuse an invalid public origin before opening gateways.
    # A duplicate process must fail before changing persisted workflow state
    # or opening external bot/agent sessions.
    httpd = ShipCourtServer((host, port), ShipCourtHTTPHandler)
    from .unified_pipeline import UnifiedBoardroomCourtPipeline
    state_path = Path(os.getenv('SHIPCOURT_STATE_PATH', '.runtime/shipcourt.sqlite3'))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        workflow = UnifiedBoardroomCourtPipeline(db_path=state_path)
    except Exception:
        httpd.server_close()
        raise
    mgr = workflow.manager
    room = workflow.room
    ShipCourtHTTPHandler.workflow = workflow
    ShipCourtHTTPHandler.room = room
    ShipCourtHTTPHandler.mgr = mgr
    if os.getenv('DISCORD_PUBLIC_KEY'):
        from .discord_interactions import DiscordInteractions
        ShipCourtHTTPHandler.discord = DiscordInteractions(workflow, os.environ['DISCORD_PUBLIC_KEY'],
            os.environ['DISCORD_APPLICATION_ID'], os.environ['DISCORD_GUILD_ID'], json.loads(os.getenv('DISCORD_MEMBERS', '{}')))
    if os.getenv('DISCORD_BOT_TOKEN'):
        from .discord_gateway import start_discord_gateway
        workflow.discord_gateway = start_discord_gateway(workflow, os.environ['DISCORD_BOT_TOKEN'],
            os.environ['DISCORD_GUILD_ID'], json.loads(os.getenv('DISCORD_MEMBERS', '{}')))
    from .switch_worker import start_workers
    workflow.switch_workers = start_workers(workflow, json.loads(os.getenv('SWITCH_CLIENTS','[]')),
                                            json.loads(os.getenv('SWITCH_PARTICIPANTS', '{}')))
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

    print("Simulation stops at AWAITING_VERDICT; use the authenticated workflow for a binding decision.")
    return


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
    principal = manager.authorization.authenticate("Bearer " + os.getenv("SHIPCOURT_TOKEN", ""))
    brief = manager.record_verdict(case.case_id, user_cmd, principal=principal)

    print("=" * 75)
    print("FINAL SIGNED RELEASE BRIEF ARTIFACT:")
    print("=" * 75)
    print(brief)
    print("=" * 75)
    print(f"\nFinal Case State: {case.state.value}")
    print(f"Switch Tasks Created: {len(case.tasks)}")
    for i, t in enumerate(case.tasks, 1):
        print(f"  Task {i}: {t.description} (Owner: {t.owner})")
    print("\n[COURT ADJOURNED] Authenticated verdict recorded in the local procedural case.")

def run_courtroom(mode: str):
    if mode == "live":
        if not json.loads(os.getenv('SWITCH_CLIENTS', '[]')):
            raise RuntimeError('LIVE MODE REQUIRES SWITCH_CLIENTS with registered agent IDs and credential environment names')
        return start_server()
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
