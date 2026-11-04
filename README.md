# SHIP COURT
> **"We built a courtroom where AI agents must argue against a deployment before a human judge lets it ship."**  
> *No Deploy Survives Cross-Examination.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/WeMakeDevs%20x%20DevTools%20Academy-Flip%20the%20Switch-blueviolet)](https://www.wemakedevs.org/hackathons/switch/rules)
[![Track](https://img.shields.io/badge/Track-01%20Best%20Business%20Workflow-green)](https://www.wemakedevs.org/hackathons/switch/rules)
[![CI Status](https://github.com/GaneshNair007/switch-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/GaneshNair007/switch-AI/actions)
[![Release](https://img.shields.io/badge/Release-v0.9.0--local--simulation-yellow)](https://github.com/GaneshNair007/switch-AI/releases/tag/v0.9.0-local-simulation)

---

## 🚦 Verification Status

| Capability | Status |
|---|---|
| Courtroom domain model and bounded workflow | ✅ Verified locally |
| Prosecutor / Defender / Rollback rules | ✅ Verified by 17 unit tests |
| HTTP API and unauthorized-verdict protection | ✅ Verified locally |
| 10-cycle local reliability test | ✅ Passed |
| Switch Console template loading | ✅ Verified by official switch_core parser (0 errors, 0 warnings) |
| Mattermost connected through Switch | ⬜ Must verify |
| Real agent sessions live in Switch | ⬜ Must verify |
| Agent-to-agent messaging through Switch | ⬜ Must verify |
| Human verdict enforced by Switch | ⬜ Must verify |
| Switch-native tasks and decisions | ⬜ Must verify |

> ⚠️ **Development & Simulation Notice:**  
> The local simulation (`server/local_courtroom_simulation.py`) validates courtroom logic without requiring API keys, Docker, or a Switch session. It is a development and CI harness — **not a substitute for the live Switch demonstration**.

---

## ⚡ 60-Second Overview

Traditional AI code reviews are passive and shallow ("Looks good to me!"). Catastrophic production outages happen because no one rigorously argued against shipping or verified the rollback plan.

**Ship Court** turns AI agents from polite assistants into accountable courtroom participants:
1. **Case Intake:** When a developer proposes a release, the system convenes a courtroom inside a shared Switch room (`#ship-court`).
2. **Adversarial Cross-Examination:** The **Prosecutor** must formulate at most 3 evidence-backed objections using past failure precedent from the **Incident Historian**.
3. **Factual Defense:** The **Defender** must address every objection in order or explicitly concede (`CONCEDED`).
4. **Guaranteed Reversibility:** The **Rollback Engineer** validates the target version, runbook command, health checks, and owner.
5. **Exclusive Human Gate:** No deploy or rollback executes autonomously. A human **Release Judge** holding the exclusive `approver` role issues a binding verdict: **APPROVE**, **BLOCK**, or **SHIP WITH CONDITIONS**.
6. **Verifiable Artifact:** Switch registers the decision, assigns follow-up tasks to owners, and publishes the signed **Release Brief**.

---

## 🎬 Target Live Interaction Sequence

The courtroom sequence designed for the Switch room:

```
Developer:              @court-clerk open case https://github.com/acme/shop/pull/482

Court Clerk:            Case SC-0482 opened. Change: dynamic checkout pricing.
                        Affected: checkout-service, cart-service, pricing-worker. CI: 42 passed.
                        @historian: Please search incident memory for relevant precedent.

Incident Historian:     Relevant precedent found: INC-017.
                        A pricing-related change on 2026-08-19 caused cart total mismatch (41 failed checkouts).
                        Lesson: Require server-side pricing assertion and mismatch alert.
                        @prosecutor: Formulate objections based on precedent.

Prosecutor:             Prosecution Objections:
                        • OBJ-1 [BLOCKING]: Dynamic pricing may create cart-total mismatch. Evidence: INC-017.
                        • OBJ-2 [WARNING]: No monitoring exists for pricing inconsistency. Evidence: Missing alert.
                        • OBJ-3 [NOTE]: Rollout percentage is not specified.
                        @defender: Please address each objection in order or concede.

Defender:               Defense Responses:
                        • For OBJ-1: Pricing is calculated only server-side; validated by pricing_consistency_test.py.
                        • For OBJ-2: CONCEDED. No mismatch alert currently exists.
                        • For OBJ-3: Proposed 5% canary rollout with progressive stepping.
                        @rollback: Please produce validated rollback plan.

Rollback Engineer:      Rollback plan verified: target version: v2.13.2.
                        Command: ./scripts/rollback.sh checkout-service v2.13.2
                        Health checks: checkout error rate < 1%, cart latency < 400ms, pricing consistency job passes.
                        Rollback owner: Priya (Status: READY). Auto-execution is disabled.
                        @clerk: Ready for Release Judge.

Court Clerk:            Case ready for verdict. Unresolved blocking condition: pricing mismatch alert.
                        Awaiting binding verdict from Human Release Judge (@Priya).

Priya (Human Judge):    @court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback

Court Clerk:            Verdict recorded: CONDITIONS.
                        Switch Tasks Created:
                        1. Configure canary 5% rollout — owner: Priya
                        2. add checkout mismatch alert — owner: DevOps
                        3. Confirm rollback owner and rehearse rollback — owner: Priya
                        Signed Release Brief published to #ship-court.
```

---

## ⚖️ Why Switch Is Load-Bearing (Remove-Switch Test)

If Switch is removed, the architecture fails to meet Track 01 requirements:
1. **Durable Room State:** `#ship-court` hosts the case timeline, agent identities, and evidence logs.
2. **Multi-Agent Session Routing:** Coordinates 5 distinct agents running across distributed machine boundaries (Server vs. Developer Laptop vs. Ops Host).
3. **Exclusive Approver Role:** Guarantees that only a verified human holding the `approver` role can issue verdicts. Agent attempts to self-approve are strictly rejected.
4. **Integrated Task & Decision Storage:** Natively turns conditional verdicts into assigned, trackable Switch tasks.

---

## 🏛️ System Architecture & Machine Topology

```
+---------------------------------------------------------------------------------------+
|                                      TEAM CHAT                                        |
|  (Mattermost / Slack / Teams / Discord)                                               |
|       Developer <-------------> #ship-court <-------------> Human Judge (Exclusive)   |
+------------------------------------------+--------------------------------------------+
                                           |
                                   Switch Chat Bridge
                                           |
+------------------------------------------v--------------------------------------------+
|                                     SWITCH CORE                                       |
|  • Room State & Message Bus               • Task & Decision Storage                   |
|  • SSE In / HTTP Out Engine               • Exclusive Role Gate (approver)            |
|  • Shared Instructions & Procedure        • Distributed Session Registry              |
+------------------------------------------+--------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
+-------------------v-------------------+ +-----------------------v---------------------+
|        ALWAYS-ON SERVER HOST          | |          DEVELOPER / OPS MACHINE            |
|  • Court Clerk (Orchestrator)         | |  • Defender (Local repo & tests)            |
|  • Incident Historian (Memory search) | |  • Rollback Engineer (Runbook verification) |
|  • Prosecutor (Adversarial review)    | |                                             |
+-------------------+-------------------+ +-----------------------+---------------------+
                    |                                             |
                    +----------------------+----------------------+
                                           |
+------------------------------------------v--------------------------------------------+
|                                 CORE EVIDENCE CHAIN                                   |
|  GitHub PR / Diff / CI  --->  Incident Memory (INC-XXX)  --->  Rollback Runbook       |
|  (Optional: Firecrawl web crawler for dynamic PR scraping)                            |
+---------------------------------------------------------------------------------------+
```

---

## 🚀 Local Verification & Reproducibility

### 1. Clone & Install
```bash
git clone https://github.com/GaneshNair007/switch-AI.git
cd switch-AI
pip install -r requirements.txt
```

### 2. Validate Switch Template (Structural Pre-Checks)
```bash
python switch/validate_template.py
```

### 3. Run Test Suite (17 Unit & HTTP API Tests)
```bash
python -m pytest -v tests/
```

### 4. Run the 10-Cycle Continuous Local Stress Verifier
```bash
python tests/stress_and_health_check.py
```

### 5. Run the Local Multi-Agent Simulation Harness
```bash
python -m server.local_courtroom_simulation
```

---

## 📜 Verifiable Terminal Artifact: Release Brief

Every case terminates in an auditable Release Brief stored with the case record:

```markdown
# Release Brief - SC-0482
Change: Dynamic checkout pricing
Repository: acme/shop
PR: #482
Requested by: Priya
Decision: SHIP WITH CONDITIONS

## Risk assessment
| # | Objection | Classification | Status | Evidence |
|---|---|---|---|---|
| 1 | Dynamic pricing may create cart-total mismatch between client and server. | BLOCKING | Mitigated | INC-017: client-side and server-side pricing divergence |
| 2 | No monitoring exists for pricing inconsistency. | BLOCKING | Open | No alert named pricing-mismatch in monitoring configuration. |
| 3 | Rollout percentage is not specified. | NOTE | Resolved | Deployment target specified canary without explicit traffic percentage. |

## Rollback plan
- Current version: v2.14.0
- Rollback target: v2.13.2
- Command: ./scripts/rollback.sh checkout-service v2.13.2
- Health checks: checkout error rate < 1%, cart-service p95 latency < 400ms, pricing consistency job passes
- Rollback owner: Priya
- Execution status: READY -- requires explicit human approval

## Conditions before full rollout
- [ ] Configure canary 5% rollout -- Priya
- [ ] add checkout mismatch alert -- DevOps
- [ ] Confirm rollback owner and rehearse rollback (rollback) -- Priya

## Decision record
- Judge: Priya
- Verdict: SHIP WITH CONDITIONS
- Switch room: #ship-court
- Case ID: SC-0482
```

---

## 👥 Hackathon Details & Authors
- **Event:** WeMakeDevs × DevTools Academy × Switch AI Flip the Switch Hackathon
- **Track:** Track 01 — Best Business Workflow
- **Author:** Ganesh Nair ([@GaneshNair007](https://github.com/GaneshNair007))
- **License:** [MIT](LICENSE)
