"""Tests for ShipCourtHTTPHandler REST API and Webhooks."""
import json, threading, time, urllib.request, urllib.error, hashlib
from unittest.mock import patch
from http.server import HTTPServer
import pytest
from server.main import ShipCourtHTTPHandler
from server.case_manager import CaseManager
from server.local_courtroom_simulation import setup_live_courtroom

TOKEN = "test-http-credential-with-32-characters"
PORT = 8999
BASE_URL = f"http://127.0.0.1:{PORT}"

@pytest.fixture(scope="module", autouse=True)
def run_test_server():
    room = setup_live_courtroom("test-http-court")
    mgr = CaseManager()
    ShipCourtHTTPHandler.room = room
    ShipCourtHTTPHandler.mgr = mgr
    identity = {'id': 'test-http-human', 'token_sha256': hashlib.sha256(TOKEN.encode()).hexdigest(), 'roles': ['operator', 'approver'], 'scopes': ['*']}
    mgr.authorization.identities.append(identity)
    httpd = HTTPServer(("127.0.0.1", PORT), ShipCourtHTTPHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.3)
    yield
    httpd.shutdown()
    httpd.server_close()
    mgr.authorization.identities.remove(identity)

def test_health_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "healthy"
        assert data["service"] == "ship-court-backend"
        assert data["agents_online"] == 5

def test_status_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/status")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        body = resp.read().decode()
        assert "@clerk" in body
        assert "@prosecutor" in body

def test_case_open_and_verdict_api():
    # 1. Open case via POST
    req = urllib.request.Request(
        f"{BASE_URL}/api/case/open",
        data=json.dumps({"pr_url": "https://github.com/acme/shop/pull/482"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        case_id = data["case_id"]
        assert case_id.startswith("SC-")

    # 2. Unauthorized verdict attempt via POST (should be 403 Forbidden)
    req_bad = urllib.request.Request(
        f"{BASE_URL}/api/case/verdict",
        data=json.dumps({"case_id": case_id, "command": "@court-clerk verdict APPROVE", "is_human": False}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_bad)
    assert exc_info.value.code == 403

    # 3. Authorized human verdict via POST (should succeed)
    req_good = urllib.request.Request(
        f"{BASE_URL}/api/case/verdict",
        data=json.dumps({
            "case_id": case_id,
            "command": "@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback",
            "judge": "Priya",
            "is_human": True
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req_good) as resp:
        assert resp.status == 200
        verdict_res = json.loads(resp.read().decode())
        assert "Release Brief" in verdict_res["release_brief"]

def test_metrics_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/metrics")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert "text/plain" in resp.headers.get("Content-Type", "")
        body = resp.read().decode()
        assert "shipcourt_agents_online" in body
        assert "shipcourt_cases_total" in body
        assert "shipcourt_verdicts_total" in body
        assert "shipcourt_server_healthy 1" in body

def test_debate_endpoint_contract():
    mock_responses = [
        "Prosecutor indictment: High lock contention hazard.",
        "Defender rebuttal: Canary rollout mitigates contention.",
        "PROSECUTION POWER: 70\nDEFENSE POWER: 80\nWINNER: DEFENSE\nVERDICT: CONDITIONS\nRATIONALE: Defense provided viable canary.\nCONDITIONS:\n1. 5% canary for 20m.\nTASKS:\n- Monitor canary (Owner: SRE)\n"
    ]
    with patch("server.live_courtroom_debate.LiveCourtroomDebateEngine._call_llm", side_effect=mock_responses):
        req = urllib.request.Request(
            f"{BASE_URL}/api/debate",
            data=json.dumps({"task": "Test Canary Migration", "repo": "acme/shop", "judge": "Priya"}).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert "verdict" in data
            assert data["verdict"] == "CONDITIONS"
            assert "conditions" in data
            assert isinstance(data["conditions"], list)
            assert len(data["conditions"]) == 1
            assert "5% canary" in data["conditions"][0]
            assert data["judge"] == "Priya"

def test_debate_endpoint_rejects_empty_task():
    req = urllib.request.Request(
        f"{BASE_URL}/api/debate",
        data=json.dumps({"task": "", "repo": "acme/shop"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
