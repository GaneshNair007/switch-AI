"""Production-Grade Enterprise Release Governance Console for Ship Court.
Serves the high-density dashboard from server/dashboard.html with authenticated operator token.
"""
from pathlib import Path
import os

_HTML_FILE = Path(__file__).resolve().parent / "dashboard.html"

def _get_provisioned_token():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("SHIPCOURT_TOKEN="):
                    return line.strip().split("=", 1)[1].strip("\'\\\"")
    return os.environ.get("SHIPCOURT_TOKEN", "")

def get_dashboard_html():
    token = _get_provisioned_token()
    if _HTML_FILE.exists():
        with open(_HTML_FILE, "r", encoding="utf-8") as f:
            return f.read().replace("__TOKEN_PLACEHOLDER__", token)
    return "<html><body>Dashboard template not found</body></html>"

class DynamicHTML(str):
    def encode(self, *args, **kwargs):
        return get_dashboard_html().encode(*args, **kwargs)

HTML_DASHBOARD = DynamicHTML()
