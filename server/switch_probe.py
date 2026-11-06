"""Live Switch message probe: verifies real round-trip message delivery through Switch API."""
import os
import sys
import time
import requests

BASE = os.environ.get("SWITCH_API_BASE", "http://127.0.0.1:3000")
TOKEN = os.environ.get("SWITCH_API_TOKEN", "")
ROOM = os.environ.get("SWITCH_ROOM", "shipcourt-ship-court")

if not TOKEN:
    print("[ERROR] SWITCH_API_TOKEN environment variable is required to run live Switch probe.")
    print("Usage: $env:SWITCH_API_TOKEN='...' ; python -m server.switch_probe")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def send(message: str):
    response = requests.post(
        f"{BASE}/rooms/{ROOM}/messages",
        headers=HEADERS,
        json={"text": message},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

def wait_for_reply(marker: str, timeout: int = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(
                f"{BASE}/rooms/{ROOM}/messages",
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            messages = response.json().get("messages", [])
            if any(marker in m.get("text", "") for m in messages):
                return True
        except Exception as e:
            print(f"[Probe] Polling error: {e}")
        time.sleep(2)
    raise AssertionError(f"Expected reply containing {marker!r} was not received within {timeout}s")

if __name__ == "__main__":
    nonce = str(time.time_ns())
    print(f"[Switch Probe] Sending case probe to {BASE}/rooms/{ROOM}...")
    send(f"@clerk open case https://github.com/acme/shop/pull/482?probe={nonce}")
    print("[Switch Probe] Waiting for Clerk response through Switch...")
    wait_for_reply("CASE SC-")
    print("LIVE SWITCH MESSAGE PATH VERIFIED")
