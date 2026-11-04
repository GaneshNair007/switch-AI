# SHIP COURT
> **No Deploy Survives Cross-Examination**  
> *A Switch-native, multi-agent release-governance workflow.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/WeMakeDevs%20x%20DevTools%20Academy-Flip%20the%20Switch-blueviolet)](https://github.com/GaneshNair007/switch-AI)
[![Track](https://img.shields.io/badge/Track-01%20Best%20Business%20Workflow-green)](https://github.com/GaneshNair007/switch-AI)

Ship Court treats every code deployment as a formal legal case. When an engineer proposes a release, the system convenes a courtroom inside a shared team chat room (`#ship-court`). Specialized AI agents cross-examine the change, raise evidence-backed objections, test rollback viability, and extract institutional failure memory. A human Release Judge issues a binding verdict: **APPROVE**, **BLOCK**, or **SHIP WITH CONDITIONS**.

---

## 🏛️ The Courtroom Roles

| Court Role | Type | Responsibility | Output |
| :--- | :--- | :--- | :--- |
| **Court Clerk** | Agent | Case intake, orchestration, procedure enforcement | Case file & Release Brief |
| **Prosecutor** | Agent | Find credible reasons not to ship | Max 3 classified objections |
| **Incident Historian** | Agent | Search past incidents, alerts, deploys | Incident precedent report |
| **Defender** | Agent | Answer objections with evidence or concede | Mitigation / concession record |
| **Rollback Engineer** | Agent | Prove the release is reversible | Executable rollback plan |
| **Release Judge** | Human | Exclusive final release authority | APPROVE / BLOCK / CONDITIONS |

---

## 🏗️ System Architecture

```
+-------------------------------------------------------------------------+
|                               TEAM CHAT                                 |
|  (Mattermost / Slack / Teams / Discord)                                 |
|       Developer <---> #ship-court <---> Human Release Judge (Exclusive) |
+------------------------------------+------------------------------------+
                                     |
                             Switch Chat Bridge
                                     |
+------------------------------------v------------------------------------+
|                               SWITCH CORE                               |
|  - Room State & Protocol            - Task & Decision Auditing          |
|  - SSE In / HTTP Out Engine         - Docker & Local Agent Runtimes     |
|  - Shared Instructions & Rules      - Distributed Machine Session Bus   |
+------------------------------------+------------------------------------+
                                     |
                  +------------------+------------------+
                  |                                     |
+-----------------v-----------------+ +-----------------v-----------------+
|      ALWAYS-ON SERVER HOST        | |     DEVELOPER / OPS MACHINE       |
|  - Court Clerk                    | |  - Defender                       |
|  - Incident Historian             | |  - Rollback Engineer              |
|  - Prosecutor                     | |                                   |
+-----------------+-----------------+ +-----------------+-----------------+
                  |                                     |
                  +------------------+------------------+
                                     |
+------------------------------------v------------------------------------+
|                         EXTERNAL CONNECTORS                             |
|  - GitHub API / PR Scraper (Firecrawl web extraction)                   |
|  - Incident Memory (SQLite / Seeded JSON)                               |
|  - Rollback Runbooks & Service Health Checks                            |
+-------------------------------------------------------------------------+
```

---

## ⚖️ Why Switch Is Load-Bearing

Ship Court cannot function as a simple webhook or single-agent bot:
1. **Durable Room State:** `#ship-court` hosts the case file, shared guidelines, and historical case precedents.
2. **Multi-Agent Session Routing:** Coordinates 5 distinct agents running across distributed machines (server vs. local machine).
3. **Exclusive Approver Role:** Cryptographically guarantees that only a verified human can issue binding release verdicts.
4. **Task & Decision Auditing:** Automatically converts conditional release requirements into assigned, auditable Switch tasks.

---

## 💬 Command Grammar

```bash
# Open case
@court-clerk open case https://github.com/acme/shop/pull/482

# Check status & evidence
@court-clerk status
@court-clerk evidence
@court-clerk objections
@court-clerk rollback

# Issue binding human verdict
@court-clerk verdict APPROVE
@court-clerk verdict BLOCK reason="No rollback owner"
@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback
```

---

## 🚀 Quick Start & Clean-Room Reproduction

### 1. Clone & Configure
```bash
git clone -b courtroom-ship-court https://github.com/GaneshNair007/switch-AI.git
cd switch-AI
cp .env.example .env
```

### 2. Run Tests
```bash
python -m pytest -v tests/
```

### 3. Run Courtroom Simulation
```bash
python -m server.main --demo
```

### 4. Deploy into Switch Console
```bash
switch template apply switch/ship-court.template.yaml \
  --param team=shipcourt \
  --param repository=acme/shop \
  --param provider=claude \
  --param bridge=mattermost
```

---

## 📜 Example Release Brief Artifact

Every case terminates in an auditable Release Brief posted directly into Switch:

```markdown
# Release Brief — SC-0482
Change: Dynamic checkout pricing
Repository: acme/shop
PR: #482
Requested by: Priya
Decision: SHIP WITH CONDITIONS

## Risk assessment
| # | Objection | Classification | Status | Evidence |
|---|---|---|---|---|
| 1 | Cart-total mismatch | WARNING | Mitigated | Server-side pricing validation test |
| 2 | No pricing mismatch alert | BLOCKING | Open | Missing monitoring rule |
| 3 | Rollout scope unclear | NOTE | Resolved | 5% canary proposed |

## Rollback plan
- Current version: v2.14.0
- Rollback target: v2.13.2
- Command: ./scripts/rollback.sh checkout-service v2.13.2
- Health checks: checkout error rate, cart latency, pricing consistency
- Rollback owner: Priya
- Execution status: READY — requires explicit human approval

## Conditions before full rollout
- [ ] Add pricing-mismatch alert — DevOps
- [ ] Configure 5% canary rollout — Priya
- [ ] Rehearse rollback procedure — Priya

## Decision record
- Judge: Priya
- Verdict: SHIP WITH CONDITIONS
- Switch room: #ship-court
- Case ID: SC-0482
```

---

## 👥 Authors & License
- **Author:** Ganesh Nair (@GaneshNair007)
- **License:** [MIT](LICENSE)
