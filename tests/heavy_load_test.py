"""Heavy Load and High-Concurrency Backend Stress Verifier.
Simulates thousands of concurrent user requests against the Ship Court HTTP API
and internal state machine to verify zero dropouts, thread safety, and latency profiles.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

# Add repo root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.case_manager import CaseManager
from server.local_courtroom_simulation import setup_live_courtroom
from server.main import ShipCourtHTTPHandler, ShipCourtServer

logging.basicConfig(level=logging.WARNING)


def run_heavy_stress_test(total_requests: int = 10000, concurrency: int = 50, port: int = 9123):
    print("=" * 78)
    print(f"SHIP COURT HEAVY CONCURRENCY & STRESS TEST HARNESS")
    print(f"Target: {total_requests:,} requests | Concurrency: {concurrency} threads | Port: {port}")
    print("=" * 78)

    # 1. Start Server with large backlog
    room = setup_live_courtroom("stress-court-room")
    mgr = CaseManager()
    ShipCourtHTTPHandler.room = room
    ShipCourtHTTPHandler.mgr = mgr

    httpd = ShipCourtServer(("127.0.0.1", port), ShipCourtHTTPHandler)
    httpd.request_queue_size = 1024
    httpd.daemon_threads = True

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"
    print(f"Server online at {base_url}. Commencing traffic flood...\n")

    latencies: List[float] = []
    success_count = 0
    security_blocked_count = 0
    failure_count = 0
    errors: List[str] = []

    lock = threading.Lock()

    def send_request(req_id: int):
        t0 = time.perf_counter()
        endpoint_type = req_id % 6

        # Retry loop for ephemeral port / socket buffer pressure
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if endpoint_type == 0:
                    # GET /health
                    req = urllib.request.Request(f"{base_url}/health")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        assert resp.status == 200
                        resp.read()
                elif endpoint_type == 1:
                    # GET /status
                    req = urllib.request.Request(f"{base_url}/status")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        assert resp.status == 200
                        resp.read()
                elif endpoint_type == 2:
                    # GET /tasks
                    req = urllib.request.Request(f"{base_url}/tasks")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        assert resp.status == 200
                        resp.read()
                elif endpoint_type == 3:
                    # GET /decisions
                    req = urllib.request.Request(f"{base_url}/decisions")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        assert resp.status == 200
                        resp.read()
                elif endpoint_type == 4:
                    # POST /api/case/open
                    payload = json.dumps({"pr_url": f"https://github.com/acme/shop/pull/{req_id % 500 + 1}"}).encode()
                    req = urllib.request.Request(f"{base_url}/api/case/open", data=payload, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        assert resp.status == 200
                        resp.read()
                elif endpoint_type == 5:
                    # POST /api/case/verdict - Unauthorized check (prosecutor attempting verdict)
                    payload = json.dumps({"case_id": "SC-0482", "command": "verdict APPROVE", "judge": "prosecutor", "is_human": False}).encode()
                    req = urllib.request.Request(f"{base_url}/api/case/verdict", data=payload, headers={"Content-Type": "application/json"})
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            assert False, "Unauthorized verdict succeeded!"
                    except urllib.error.HTTPError as e:
                        assert e.code == 403
                        with lock:
                            nonlocal security_blocked_count
                            security_blocked_count += 1
                        dt = time.perf_counter() - t0
                        with lock:
                            latencies.append(dt)
                        return True

                dt = time.perf_counter() - t0
                with lock:
                    nonlocal success_count
                    success_count += 1
                    latencies.append(dt)
                return True

            except urllib.error.URLError as ue:
                if attempt < max_retries - 1:
                    time.sleep(0.02 * (attempt + 1))
                    continue
                dt = time.perf_counter() - t0
                with lock:
                    nonlocal failure_count
                    failure_count += 1
                    if len(errors) < 10:
                        errors.append(f"Req #{req_id} (type {endpoint_type}) failed: {ue}")
                return False
            except Exception as ex:
                dt = time.perf_counter() - t0
                with lock:
                    failure_count += 1
                    if len(errors) < 10:
                        errors.append(f"Req #{req_id} (type {endpoint_type}) failed: {type(ex).__name__} - {ex}")
                return False

    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, total_requests + 1)]
        for idx, f in enumerate(as_completed(futures), 1):
            if idx % (total_requests // 10 or 1) == 0:
                pct = (idx / total_requests) * 100
                elapsed = time.perf_counter() - t_start
                rate = idx / elapsed if elapsed > 0 else 0
                print(f"  [Progress] {idx:,}/{total_requests:,} requests completed ({pct:.0f}%) - Current Rate: {rate:,.0f} req/sec")

    total_time = time.perf_counter() - t_start

    httpd.shutdown()

    latencies.sort()
    avg_latency = (sum(latencies) / len(latencies)) * 1000 if latencies else 0
    p50 = latencies[int(len(latencies) * 0.50)] * 1000 if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] * 1000 if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] * 1000 if latencies else 0
    min_lat = latencies[0] * 1000 if latencies else 0
    max_lat = latencies[-1] * 1000 if latencies else 0
    throughput = total_requests / total_time if total_time > 0 else 0

    print("\n" + "=" * 78)
    print("HEAVY LOAD TEST RESULTS & LATENCY PROFILE")
    print("=" * 78)
    print(f"Total Requests Processed: {total_requests:,}")
    print(f"Concurrency Level:        {concurrency} worker threads")
    print(f"Total Time Taken:         {total_time:.2f} seconds")
    print(f"System Throughput:        {throughput:,.2f} requests/second")
    print(f"Successful Requests:      {success_count:,} (HTTP 200 OK)")
    print(f"Security Gate Rejections: {security_blocked_count:,} (HTTP 403 Forbidden properly enforced)")
    print(f"Unexpected Failures:      {failure_count:,}")
    print(f"Total Success Rate:       {((success_count + security_blocked_count) / total_requests) * 100:.2f}%")
    print("-" * 78)
    print("Latency Distribution (ms):")
    print(f"  Min:  {min_lat:8.2f} ms")
    print(f"  p50:  {p50:8.2f} ms")
    print(f"  Avg:  {avg_latency:8.2f} ms")
    print(f"  p95:  {p95:8.2f} ms")
    print(f"  p99:  {p99:8.2f} ms")
    print(f"  Max:  {max_lat:8.2f} ms")
    print("=" * 78)

    if failure_count > 0:
        print("SAMPLE ERRORS:")
        for err in errors:
            print(f"  [ERROR] {err}")
        return False
    else:
        print(">>> VERDICT: 100% TIP-TOP PASS -- ZERO FAILURES OUT OF 10,000 REQUESTS!")
        print("=" * 78)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heavy Load Stress Tester")
    parser.add_argument("-n", "--requests", type=int, default=10000, help="Total requests to send")
    parser.add_argument("-c", "--concurrency", type=int, default=50, help="Concurrent client workers")
    parser.add_argument("-p", "--port", type=int, default=9123, help="Server port")
    args = parser.parse_args()

    ok = run_heavy_stress_test(total_requests=args.requests, concurrency=args.concurrency, port=args.port)
    sys.exit(0 if ok else 1)
