"""Live Switch runtime integration gate.
Fails loudly if real Switch Console / local-server is not reachable or unauthenticated.
"""
import os
import pytest
import requests

SWITCH_HEALTH_URL = os.getenv("SWITCH_HEALTH_URL", "http://127.0.0.1:3000/health")
SWITCH_ROOM = os.getenv("SWITCH_ROOM", "shipcourt-ship-court")
SWITCH_API_TOKEN = os.getenv("SWITCH_API_TOKEN")

pytestmark = pytest.mark.skipif(
    not SWITCH_API_TOKEN,
    reason="Live Switch gate disabled: SWITCH_API_TOKEN not set",
)

def test_switch_console_is_reachable():
    response = requests.get(SWITCH_HEALTH_URL, timeout=5)
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"ok", "healthy", "up"}

def test_ship_court_room_exists():
    response = requests.get(
        f"{SWITCH_HEALTH_URL}/rooms/{SWITCH_ROOM}",
        headers={"Authorization": f"Bearer {SWITCH_API_TOKEN}"},
        timeout=5,
    )
    assert response.status_code == 200
    assert response.json().get("name") == SWITCH_ROOM

def test_live_agents_are_present():
    response = requests.get(
        f"{SWITCH_HEALTH_URL}/rooms/{SWITCH_ROOM}/agents",
        headers={"Authorization": f"Bearer {SWITCH_API_TOKEN}"},
        timeout=5,
    )
    assert response.status_code == 200
    agents = response.json().get("agents", [])
    live = [a for a in agents if a.get("status") == "live"]
    assert len(live) >= 2, f"Expected at least 2 live agents, got {len(live)}"
