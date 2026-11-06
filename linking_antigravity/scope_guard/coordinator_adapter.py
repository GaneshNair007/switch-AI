"""Coordinator Adapter for Antigravity Agent Scope Guard.

Provides the network and API communication interface to the external coordinator.
Handles timeouts, HTTP contracts, and network disconnection gracefully.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

from scope_guard.schema import (
    ApprovalRequest,
    ApprovalResponse,
    Assignment,
    ViolationEvent,
)


class CoordinatorNetworkError(Exception):
    """Raised when coordinator is unreachable or returns a transport error."""
    pass


class CoordinatorClient:
    """HTTP client interface for communication with the coordinator backend."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        auth_token: Optional[str] = None,
        timeout: float = 3.0,
        transport: Optional[Callable[[urllib.request.Request], Tuple[int, bytes]]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.transport = transport

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-Scope-Guard/0.1.0",
            "Connection": "close",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _execute_request(self, req: urllib.request.Request) -> Tuple[int, bytes]:
        """Executes an HTTP request and ensures socket draining on errors."""
        if self.transport:
            return self.transport(req)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read()
                return status, body
        except urllib.error.HTTPError as he:
            try:
                he.read()
                he.close()
            except Exception:
                pass
            raise CoordinatorNetworkError(f"HTTP error {he.code}: {he.reason}") from he
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise CoordinatorNetworkError(f"Network transport error: {e}") from e

    def get_assignment(self, agent_id: str) -> Optional[Assignment]:
        """Fetches the latest assigned scope for an agent from the coordinator."""
        url = f"{self.base_url}/api/v1/agents/{agent_id}/assignment"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")

        status, body = self._execute_request(req)
        if status == 200:
            data = json.loads(body.decode("utf-8"))
            return Assignment.from_dict(data)
        return None

    def post_violation(self, event: ViolationEvent) -> bool:
        """Sends a structured violation event to the coordinator."""
        url = f"{self.base_url}/api/v1/violations"
        payload = json.dumps(event.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers=self._headers(), method="POST"
        )

        status, _ = self._execute_request(req)
        return status in (200, 201, 202)

    def post_approval_request(self, approval_req: ApprovalRequest) -> Optional[ApprovalResponse]:
        """Submits an out-of-scope approval request to the coordinator."""
        url = f"{self.base_url}/api/v1/approvals"
        payload = json.dumps(approval_req.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers=self._headers(), method="POST"
        )

        status, body = self._execute_request(req)
        if status in (200, 201, 202):
            data = json.loads(body.decode("utf-8"))
            return ApprovalResponse.from_dict(data)
        return None

    def get_approval_status(self, request_id: str) -> Optional[ApprovalResponse]:
        """Checks the status of a pending approval request."""
        url = f"{self.base_url}/api/v1/approvals/{request_id}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")

        status, body = self._execute_request(req)
        if status == 200:
            data = json.loads(body.decode("utf-8"))
            return ApprovalResponse.from_dict(data)
        return None
