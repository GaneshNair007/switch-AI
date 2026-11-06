# Antigravity Agent Scope Guard

[![Tests](https://img.shields.io/badge/Tests-16%20Passing-brightgreen.svg)]()
[![Antigravity](https://img.shields.io/badge/Antigravity-IDE%20%7C%20CLI%20%7C%20SDK-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success.svg)]()

A permission, responsibility, and conflict-prevention layer built specifically for **Google Antigravity coding agents** participating in multi-agent collaborative software development systems.

The Scope Guard makes each Antigravity agent aware of its assigned task, validates all file-modification attempts against allowed paths and cross-agent ownership reservations, issues explainable verdicts (`ALLOW`, `WARN`, `ASK`, `BLOCK`), spools structured violation reports to an external Coordinator, and dynamically handles authorized scope expansions.

---

## 1. Quick Demonstration

Run the automated end-to-end demonstration covering all core scenarios:

```sh
python3 demo.py
```

### Demonstration Highlights:
- **Scenario A**: Agent modifies `frontend/src/auth/Login.jsx` → **`ALLOW`** (Within assigned scope).
- **Scenario B**: Agent attempts to modify `backend/src/auth/login.py` → **`BLOCK`** (Detected ownership reservation for `backend-agent`).
- **Scenario C**: Agent attempts to write `database/schema.sql` → **`BLOCK`** (Restricted directory access).
- **Scenario D**: Agent attempts path traversal `../../etc/shadow` → **`BLOCK`** (Critical security violation).
- **Scenario E**: Agent receives prompt to expand scope without authority → **`BLOCK`** (Unauthorized scope expansion rejected).
- **Scenario F**: Coordinator approves scope expansion → **`ALLOW`** (Updated assignment version applied).
- **Scenario G**: Coordinator experiences network outage → Events safely spooled locally in `.scope_guard/events/pending.jsonl` and auto-flushed when connectivity is restored.

---

## 2. Deliverables Index

| # | Deliverable | Location | Description |
|---|:---|:---|:---|
| 1 | **Working Implementation** | [`scope_guard/`](./scope_guard/) | Production-ready Python package (Python 3.10+, zero external dependencies). |
| 2 | **Antigravity Configuration** | [`.agents/hooks.json`](./.agents/hooks.json) | Native `PreToolUse` lifecycle hook configuration. |
| 3 | **Assignment & Policy Schema** | [`scope_guard/schema.py`](./scope_guard/schema.py) | Strongly-typed contracts for assignments, decisions, violations, and approvals. |
| 4 | **Enforcement & Detection** | [`scope_guard/policy_engine.py`](./scope_guard/policy_engine.py)<br>[`scope_guard/violation_detector.py`](./scope_guard/violation_detector.py) | Path normalization, recursive glob matching (`**`), traversal prevention, and violation categorizer. |
| 5 | **Coordinator Interface** | [`scope_guard/coordinator_adapter.py`](./scope_guard/coordinator_adapter.py)<br>[`scope_guard/mock_coordinator.py`](./scope_guard/mock_coordinator.py) | HTTP client, resilient socketless transport, and full-featured mock server. |
| 6 | **Approval Interface** | [`scope_guard/approval_handler.py`](./scope_guard/approval_handler.py) | Request creation, coordinator handshake, and atomic versioned policy updates. |
| 7 | **Unit & Integration Tests** | [`tests/test_required_11_cases.py`](./tests/test_required_11_cases.py)<br>[`tests/`](./tests/) | 16 test cases covering all 11 mandatory specification requirements. |
| 8 | **Setup Guide — IDE** | [`docs/SETUP_IDE.md`](./docs/SETUP_IDE.md) | Setup and verification in Antigravity IDE & Antigravity 2.0. |
| 9 | **Setup Guide — CLI** | [`docs/SETUP_CLI.md`](./docs/SETUP_CLI.md) | Configuration and verification using the `agy` command-line tool. |
| 10 | **Setup Guide — SDK** | [`docs/SETUP_SDK.md`](./docs/SETUP_SDK.md) | Python SDK integration using `policy.deny()` and `@hooks.pre_tool_call_decide`. |
| 11 | **Architecture Diagram** | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System boundaries, component interactions, and sequence diagrams. |
| 12 | **Demonstration** | [`demo.py`](./demo.py) | Interactive multi-scenario simulation. |
| 13 | **Known Limitations** | [`docs/LIMITATIONS.md`](./docs/LIMITATIONS.md) | Honest assessment of static shell analysis boundaries and external processes. |

---

## 3. Running the Test Suite

Execute the comprehensive test suite (including all 11 mandatory test cases):

```sh
python3 -m unittest discover -s tests -p "test_*.py" -v
```

All 16 tests execute in under 0.05 seconds with zero external network or database requirements.

---

## 4. CLI Usage

The Scope Guard provides a standalone command-line interface:

```sh
# 1. Initialize assignment for an agent:
python3 -m scope_guard.cli init \
  --agent-id frontend-agent \
  --task-id TASK-AUTH-101 \
  --description "Implement Login UI" \
  --allow "frontend/src/auth/**" \
  --restrict "backend/**" \
  --restrict "database/**" \
  --ownership "backend/src/auth/**:backend-agent"

# 2. Check current status and buffered events:
python3 -m scope_guard.cli status

# 3. Test an action against policy:
python3 -m scope_guard.cli check --tool edit_file --path frontend/src/auth/Login.jsx
# Output: Decision: ALLOW

python3 -m scope_guard.cli check --tool edit_file --path backend/src/auth/login.py
# Output: Decision: BLOCK (OWNERSHIP COLLISION)

# 4. Flush buffered violation events to coordinator:
python3 -m scope_guard.cli flush --coordinator http://coordinator.internal:8080
```

---

## 5. Explainable Violation Output Example

Whenever an operation is blocked, the Scope Guard generates an explainable report formatted exactly as required by the specification:

```
BLOCKED: OWNERSHIP COLLISION
Agent: frontend-agent
Attempted action: Modify backend/src/auth/login.py
Assigned responsibility: Implement login and registration UI components
Reason: The requested file is reserved/owned by another agent ('backend-agent').
Owner: backend-agent
Action: Modification denied. Request cross-agent authorization or coordinator reassignment.
```

---

## 6. System Boundaries & What Was NOT Built

In strict accordance with the Hackathon Specification:
- **Built**: The Antigravity-specific Scope Guard, native lifecycle hooks (`.agents/hooks.json`), rules generator (`.agents/rules/`), policy engine, violation detector, coordinator integration adapter, and tests.
- **NOT Built**: Coordinator backend server, Switch messaging server, Discord bot, Courtroom judge agents, or Docker merge environments. Clean interfaces and schemas are provided for seamless external integration.
