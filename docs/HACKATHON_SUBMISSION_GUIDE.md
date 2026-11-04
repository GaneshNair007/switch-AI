# Ship Court: Hackathon Submission & Judge Verification Guide

> **Flip the Switch Hackathon — Track 01: Best Business Workflow**  
> *"No deploy survives cross-examination."*

---

## 1. Executive Summary

Traditional deployment approvals rely on polite, superficial "LGTM" comments or passing CI tests that fail to detect high-concurrency race conditions, missing alert monitors, or untested rollback scripts.

**Ship Court** transforms release approval into a structured adversarial trial inside SandboxAQ Switch Console. Instead of passive consensus, four specialized AI agents cross-examine every release candidate with forensic intensity. Crucially, autonomous deployment approval is mathematically and procedurally forbidden: only a designated **Human Release Judge** (`auto_approve: false`) can issue binding decrees.

---

## 2. Multi-Agent Courtroom Architecture

```
                                  [ GitHub Pull Request ]
                                             │
                                             ▼
                               [ Switch Room: #ship-court ]
                        ┌────────────────────┴────────────────────┐
                        ▼                                         ▼
            [ Evidence Subpoenas ]                     [ Google Opal Pipeline ]
           (Incident Records: INC-017)                (7-Node State Machine)
                        │                                         │
       ┌────────────────┴────────────────┐                        │
       ▼                                 ▼                        │
[@prosecutor: Indictment]      [@defender: Rebuttal]              │
  • Concurrency Drift            • Isolation Boundaries           │
  • Revenue Exposure             • Alert Concessions              │
       │                                 │                        │
       └────────────────┬────────────────┘                        │
                        ▼                                         │
           [@rollback: Rollback Plan]                             │
             • Target: v2.13.2                                    │
             • Script Verified                                    │
                        │                                         │
                        ▼                                         │
             [@clerk: Judicial Summons]                           │
                        │                                         │
                        ▼                                         ▼
        ┌─────────────────────────────────────────────────────────────┐
        │                 HUMAN RELEASE JUDGE (Priya)                 │
        │        Decree: CONDITIONS (5% canary, alert mandatory)      │
        └─────────────────────────────────────────────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
              [ Cryptographic Ledger ]      [ Rollback Sentinel ]
                (SHA-256 Hash Chain)         (Watchdog & Breaker)
```

### The Adversarial Agent Roster
1. **Court Clerk (`@clerk`)**: Enforces courtroom procedure, manages case lifecycle, enforces the 4-round limit, and summons the Human Judge.
2. **Prosecutor (`@prosecutor`)**: Indicts PRs using forensic failure modes (blast radius, cache invalidation, pricing drift, downtime cost).
3. **Incident Historian (`@historian`)**: Exhumes historical outages (e.g., `INC-017` \$340k checkout failure) to prevent repeat regressions.
4. **Defender (`@defender`)**: Mounts evidence-backed defenses; explicitly marks unmonitored alerts as `CONCEDED`.
5. **Rollback Engineer (`@rollback`)**: Validates reversibility, targets last-known-good state, and enforces human-owned rollback scripts.

---

## 3. Judge Quickstart & Verification Instructions

### Prerequisites
- Python 3.10+
- `git`
- (Optional) SandboxAQ Switch Core CLI (`switch`)

```bash
git clone https://github.com/GaneshNair007/switch-AI.git
cd switch-AI
pip install -r requirements.txt
```

### Step 1: Run the 36-Test Verification Suite
Run the full automated test suite covering rules engines, courtroom protocol, cryptographic audit ledger, blast radius graph, and REST API:

```bash
pytest tests/ -v
```
*Expected Result:* **36 passed in ~1.15 seconds** (100% pass rate).

### Step 2: Run the 20,000-Request Concurrency Stress Test
Verify zero server dropped connections and sub-200ms latency under 100 concurrent worker threads:

```bash
python tests/heavy_load_test.py
```
*Benchmark Metrics:*
- Total Requests: **20,000**
- Concurrent Workers: **100**
- Success Rate: **100.00% (0 errors)**
- Throughput: **567+ requests/second**
- Average Latency: **174 ms**
- p95 Latency: **195 ms**
- Unauthorized Access Checks: **3,333 / 3,333 strictly rejected (HTTP 403)**

### Step 3: Run the Native Switch Core Courtroom Simulation
Run the full 4-round courtroom trial natively with SandboxAQ Switch Core primitives:

```bash
python server/switch_native_runner.py
```
*Output Highlights:*
- Cross-examination between `@prosecutor`, `@historian`, `@defender`, and `@rollback`
- Human Judge intervention: `CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback`
- Tamper-evident cryptographic release brief generated and sealed.

### Step 4: Validate Switch Core Template Schema
Verify that the Switch template strictly adheres to SandboxAQ schema:

```bash
python -c "from switch_core.template_lint import lint_template; errors, warnings = lint_template('switch/ship-court.template.yaml'); print('Template Lint:', len(errors), 'errors,', len(warnings), 'warnings')"
```
*Expected Result:* **0 errors, 0 warnings**.

---

## 4. REST API & Telemetry Endpoints

When running `python -m server.main --server`:
- `GET /health`: JSON system health and agent count.
- `GET /metrics`: Standard Prometheus/OpenTelemetry exporter for observability.
- `GET /status`: Room agent registration and active status.
- `POST /api/case/open`: Open a new courtroom case from a GitHub PR URL.
- `POST /api/case/verdict`: Submit a judicial verdict (**enforces Human Judge authorization; rejects AI verdicts with HTTP 403**).

---

## 5. Security & Governance

- **Zero Autonomous Deploys:** System strictly rejects non-human verdicts (`PermissionError: Only human approvers can issue binding verdicts`).
- **Cryptographic Audit Ledger:** Every event is hashed with SHA-256 and chained to previous blocks (`server/audit_ledger.py`).
- **Active Canary Sentinel:** Background monitor halts rollout if p99 latency exceeds 250ms or data drift is detected (`server/rollback_sentinel.py`).
