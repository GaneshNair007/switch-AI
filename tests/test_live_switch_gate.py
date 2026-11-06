"""Live Switch runtime integration gate.
Verifies real connection to SandboxAQ Switch Console ControlServer.
Reads port and auth token dynamically from switchdash runtime config.
"""
import os
import json
import pytest
import requests

APPDATA = os.environ.get("APPDATA", "")
CONTROL_API_PATH = os.path.join(APPDATA, "switchdash", "control-api.json")

def get_live_control_config():
    if not os.path.exists(CONTROL_API_PATH):
        return None
    try:
        with open(CONTROL_API_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def test_switch_console_process_and_control_api():
    """Verifies that Switch Console Canary is running and its Control API responds."""
    cfg = get_live_control_config()
    if not cfg:
        pytest.skip(f"Switch Console control-api.json not found at {CONTROL_API_PATH}. Is Switch Console Canary running?")

    port = cfg.get("port")
    token = cfg.get("token")
    assert port and token, f"Invalid control-api.json content: {cfg}"

    url = f"http://127.0.0.1:{port}/agents"
    headers = {"x-switch-control-token": token}
    
    response = requests.get(url, headers=headers, timeout=5)
    assert response.status_code == 200, f"Expected 200 from ControlServer, got {response.status_code}: {response.text}"
    data = response.json()
    assert "agents" in data, f"Expected 'agents' key in response, got: {data}"
