"""Serve the dashboard shell without embedding credentials."""
from pathlib import Path
_HTML_FILE = Path(__file__).resolve().parent / "dashboard.html"

def get_dashboard_html():
    html=_HTML_FILE.read_text(encoding="utf-8").replace("__TOKEN_PLACEHOLDER__", "")
    panel=(_HTML_FILE.parent/'hq_panel.html').read_text(encoding='utf-8')
    html=html.replace('class="view-section active-section"','class="view-section"')
    html=html.replace('<div class="switch-content">','<div class="switch-content">'+panel,1)
    return html.replace('</body>','<script src="/assets/hq.js"></script></body>')

class DynamicHTML(str):
    def encode(self, *args, **kwargs):
        return get_dashboard_html().encode(*args, **kwargs)

HTML_DASHBOARD = DynamicHTML()
