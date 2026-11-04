"""Evidence collection connector supporting Firecrawl, GitHub API, and offline mock fallbacks."""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from pathlib import Path
from typing import Dict, Any, List

class EvidenceCollector:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "")
        self.github_token = os.getenv("GITHUB_TOKEN", "")

    def fetch_pr_evidence(self, pr_url: str) -> Dict[str, Any]:
        """Fetch PR metadata via Firecrawl, GitHub API, or seeded repository data."""
        if self.firecrawl_api_key and "github.com" in pr_url:
            crawled = self._scrape_with_firecrawl(pr_url)
            if crawled: return crawled

        if self.github_token and "github.com" in pr_url:
            gh_data = self._fetch_from_github_api(pr_url)
            if gh_data: return gh_data

        return self._load_local_meta(pr_url)

    def search_incidents(self, service: str, change_type: str = "") -> List[Dict[str, Any]]:
        """Search local incident memory for past failures matching service or change type."""
        incidents_path = self.data_dir / "incidents.json"
        if not incidents_path.exists(): return []
        with open(incidents_path, "r", encoding="utf-8") as f:
            incidents: List[Dict[str, Any]] = json.load(f)
        return [
            inc for inc in incidents
            if inc.get("service") == service or (change_type and inc.get("change_type") == change_type)
        ]

    def _scrape_with_firecrawl(self, url: str) -> Dict[str, Any] | None:
        """Extract web and markdown content using Firecrawl API."""
        try:
            req = urllib.request.Request(
                "https://api.firecrawl.dev/v1/scrape",
                data=json.dumps({"url": url, "formats": ["markdown"]}).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.firecrawl_api_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"source": "firecrawl", "raw": data.get("data", {})}
        except Exception:
            return None

    def _fetch_from_github_api(self, pr_url: str) -> Dict[str, Any] | None:
        """Extract pull request status via GitHub REST API."""
        try:
            parts = pr_url.rstrip("/").split("/")
            owner, repo, pr_num = parts[-4], parts[-3], parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
            req = urllib.request.Request(
                api_url,
                headers={"Authorization": f"token {self.github_token}", "User-Agent": "ShipCourt-Agent"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"source": "github_api", "raw": json.loads(resp.read().decode("utf-8"))}
        except Exception:
            return None

    def _load_local_meta(self, pr_url: str) -> Dict[str, Any]:
        """Load deterministic demo fixture from data/demo_repository_meta.json."""
        meta_path = self.data_dir / "demo_repository_meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["source"] = "local_demo_meta"
                data["pr_url"] = pr_url
                return data
        return {
            "source": "fallback",
            "repository": "acme/shop",
            "pr_number": 482,
            "pr_url": pr_url,
            "affected_services": ["checkout-service"],
            "ci_status": {"state": "SUCCESS", "passed": 1, "failed": 0},
            "deployment_target": "production canary"
        }
