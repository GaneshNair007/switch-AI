"""Mock Coordinator Server.

A lightweight HTTP server and in-memory coordinator simulator for testing,
development, and end-to-end demonstrations.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import urllib.request

from scope_guard.coordinator_adapter import CoordinatorNetworkError
from scope_guard.schema import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    Assignment,
    OwnershipRecord,
    TaskStatus,
    ViolationEvent,
)

logger = logging.getLogger("scope_guard.mock_coordinator")


class MockCoordinatorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock coordinator server."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout logging during tests."""
        pass

    @property
    def server_instance(self) -> MockCoordinatorServer:
        return self.server  # type: ignore

    def do_GET(self) -> None:
        self.close_connection = True
        status, body = self.server_instance.dispatch_request("GET", self.path, b"")
        self._send_raw(status, body)

    def do_POST(self) -> None:
        self.close_connection = True
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        status, response_body = self.server_instance.dispatch_request("POST", self.path, body)
        self._send_raw(status, response_body)

    def _send_raw(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockCoordinatorServer(HTTPServer):
    """Embedded mock coordinator server with both HTTP and in-memory transport support."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8089):
        super().__init__((host, port), MockCoordinatorHandler)
        self.simulate_offline = False
        self.auto_approve = True
        self.assignments: Dict[str, Assignment] = {}
        self.approvals: Dict[str, ApprovalResponse] = {}
        self.received_violations: List[ViolationEvent] = []
        self.received_approval_requests: List[ApprovalRequest] = []
        self._thread: Optional[threading.Thread] = None

    def dispatch_request(self, method: str, raw_path: str, body: bytes) -> Tuple[int, bytes]:
        """Core routing logic shared between HTTP sockets and in-memory transports."""
        if self.simulate_offline:
            return 503, json.dumps({"error": "Coordinator Service Temporarily Unavailable"}).encode("utf-8")

        parsed = urlparse(raw_path)
        path_parts = parsed.path.strip("/").split("/")

        if method == "GET":
            # Route: GET /api/v1/agents/{agent_id}/assignment
            if len(path_parts) == 5 and path_parts[:3] == ["api", "v1", "agents"] and path_parts[4] == "assignment":
                agent_id = path_parts[3]
                assignment = self.assignments.get(agent_id)
                if assignment:
                    return 200, json.dumps(assignment.to_dict()).encode("utf-8")
                return 404, json.dumps({"error": f"Agent {agent_id} not found"}).encode("utf-8")

            # Route: GET /api/v1/approvals/{request_id}
            if len(path_parts) == 4 and path_parts[:3] == ["api", "v1", "approvals"]:
                req_id = path_parts[3]
                resp = self.approvals.get(req_id)
                if resp:
                    return 200, json.dumps(resp.to_dict()).encode("utf-8")
                return 404, json.dumps({"error": f"Approval request {req_id} not found"}).encode("utf-8")

        elif method == "POST":
            data = json.loads(body.decode("utf-8")) if body else {}

            # Route: POST /api/v1/violations
            if path_parts == ["api", "v1", "violations"]:
                event = ViolationEvent.from_dict(data)
                self.received_violations.append(event)
                return 201, json.dumps({"status": "recorded", "event_id": event.event_id}).encode("utf-8")

            # Route: POST /api/v1/approvals
            if path_parts == ["api", "v1", "approvals"]:
                appr_req = ApprovalRequest.from_dict(data)
                self.received_approval_requests.append(appr_req)

                if self.auto_approve:
                    current_assignment = self.assignments.get(appr_req.agent_id)
                    new_allowed = list(current_assignment.allowed_paths) if current_assignment else []
                    for p in appr_req.requested_paths:
                        if p not in new_allowed:
                            new_allowed.append(p)

                    new_ownership = []
                    if current_assignment:
                        for own in current_assignment.ownership_info:
                            if own.path_pattern not in appr_req.requested_paths:
                                new_ownership.append(own)

                    new_restricted = []
                    if current_assignment:
                        for rest in current_assignment.restricted_paths:
                            # If approved path falls under restricted path, carve out or remove
                            if rest not in appr_req.requested_paths and not any(p.startswith(rest.rstrip("*")) for p in appr_req.requested_paths):
                                new_restricted.append(rest)

                    new_exceptions = list(current_assignment.exceptions) if current_assignment else []
                    for p in appr_req.requested_paths:
                        if p not in new_exceptions:
                            new_exceptions.append(p)

                    updated = Assignment(
                        agent_id=appr_req.agent_id,
                        task_id=appr_req.task_id,
                        task_description=f"{current_assignment.task_description if current_assignment else ''} (Expanded Scope)",
                        allowed_paths=new_allowed,
                        restricted_paths=new_restricted,
                        ownership_info=new_ownership,
                        exceptions=new_exceptions,
                        assignment_version=(current_assignment.assignment_version + 1) if current_assignment else 2,
                    )
                    self.assignments[appr_req.agent_id] = updated

                    response = ApprovalResponse(
                        request_id=appr_req.request_id,
                        status=ApprovalStatus.APPROVED,
                        approved_by="coordinator-lead",
                        updated_assignment=updated,
                        reason="Scope expansion approved by coordinator.",
                    )
                else:
                    response = ApprovalResponse(
                        request_id=appr_req.request_id,
                        status=ApprovalStatus.PENDING,
                        reason="Waiting for coordinator human review.",
                    )

                self.approvals[appr_req.request_id] = response
                return 202, json.dumps(response.to_dict()).encode("utf-8")

        return 404, json.dumps({"error": "Not Found"}).encode("utf-8")

    def as_transport(self) -> Callable[[urllib.request.Request], Tuple[int, bytes]]:
        """Creates an in-memory transport callback for CoordinatorClient without TCP sockets."""
        def transport(req: urllib.request.Request) -> Tuple[int, bytes]:
            if self.simulate_offline:
                raise CoordinatorNetworkError("Coordinator Service Temporarily Unavailable (Simulated Outage)")
            method = req.get_method()
            raw_url = req.full_url
            parsed = urlparse(raw_url)
            data = req.data or b""
            status, body = self.dispatch_request(method, parsed.path, data)
            if status >= 400:
                raise CoordinatorNetworkError(f"HTTP error {status}: {body.decode('utf-8', errors='ignore')}")
            return status, body

        return transport

    def start_background(self) -> None:
        """Starts the mock coordinator in a background daemon thread."""
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the mock coordinator server."""
        try:
            self.shutdown()
            self.server_close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.0)


def main() -> None:
    """CLI runner to start the Mock Coordinator as a standalone HTTP server."""
    import argparse
    parser = argparse.ArgumentParser(description="Run Mock Coordinator Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    args = parser.parse_args()

    server = MockCoordinatorServer(host=args.host, port=args.port)

    # Pre-populate two collaborative teammate assignments
    server.assignments["frontend-agent"] = Assignment(
        agent_id="frontend-agent",
        task_id="TASK-AUTH-UI-101",
        task_description="Implement login and registration UI components",
        allowed_paths=["frontend/src/auth/**"],
        restricted_paths=["backend/**", "database/**"],
        ownership_info=[
            OwnershipRecord(
                path_pattern="backend/src/auth/**",
                owner_agent_id="backend-agent",
                description="Backend Authentication API Service",
            )
        ],
        task_status=TaskStatus.IN_PROGRESS,
        assignment_version=1,
    )

    server.assignments["backend-agent"] = Assignment(
        agent_id="backend-agent",
        task_id="TASK-AUTH-API-202",
        task_description="Implement backend authentication API and token endpoints",
        allowed_paths=["backend/src/auth/**"],
        restricted_paths=["frontend/**", "database/**"],
        ownership_info=[
            OwnershipRecord(
                path_pattern="frontend/src/auth/**",
                owner_agent_id="frontend-agent",
                description="Frontend UI Components",
            )
        ],
        task_status=TaskStatus.IN_PROGRESS,
        assignment_version=1,
    )

    print(f"\n{'='*70}")
    print(f"  MOCK COORDINATOR RUNNING on http://{args.host}:{args.port}")
    print(f"{'='*70}")
    print("Pre-registered Teammate Assignments:")
    print("  1. 'frontend-agent' -> Allowed: frontend/src/auth/** | Restricted: backend/**")
    print("  2. 'backend-agent'  -> Allowed: backend/src/auth/**  | Restricted: frontend/**")
    print("\nListening for Scope Guard hook evaluations, violations, and approvals...")
    print("Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down coordinator server...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
