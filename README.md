<!-- ═══════════════════════════════════════════════════════════════════════ --> <!-- SHIP COURT × BOARDROOM OS × ANTIGRAVITY × PARALLEL EARTH --> <!-- Flip the Switch Hackathon · WeMakeDevs × DevTools Academy --> <!-- ═══════════════════════════════════════════════════════════════════════ --> <div align="center"> <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24,30&height=250&section=header&text=SHIP%20COURT&fontSize=84&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=No%20deploy%20survives%20cross-examination&descSize=22&descAlignY=60" alt="Ship Court banner" width="100%"/> <a href="https://github.com/GaneshNair007/switch-AI"> <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3200&pause=900&color=A78BFA&center=true&vCenter=true&width=860&height=50&lines=%E2%9A%96%EF%B8%8F+AI+agents+argue+AGAINST+your+deploy;%F0%9F%91%A9%E2%80%8D%E2%9A%96%EF%B8%8F+A+human+judge+holds+the+only+gavel;%F0%9F%8C%8D+Parallel+Earth+simulates+the+blast+radius+first;%E2%9C%8B+Third+Voice+raises+a+hand+instead+of+interrupting;%F0%9F%94%8C+Powered+by+Switch+%E2%80%94+remove+it+and+it+breaks" alt="Typing animation of the project pitch"/> </a> <br/>
"We built a courtroom where AI agents must argue against a deployment before a human judge lets it ship."
<br/>
Hackathon Track 01 Track 02 <br/> Powered by Switch Python Tests License: MIT CI Release
<br/>
🚀 Overview  •  🎬 Live Trial  •  🔌 Why Switch  •  🏛️ Architecture  •  🦸 Superpowers  •  🧪 Run It  •  👥 Team
</div> <br/>

🎯 The Problem We Flipped
<table> <tr> <td width="50%" valign="top">
😵 Before
* "LGTM 👍" rubber-stamp reviews
* Nobody argues against shipping
* Rollback plans are untested folklore
* Teammates' AI coding agents collide in silence
* Meeting decisions evaporate into voice history
</td> <td width="50%" valign="top">
⚖️ After — Ship Court
* A Prosecutor must object, with evidence
* A Defender must answer or concede
* A Rollback Engineer proves reversibility
* Parallel Earth simulates blast radius first
* A human judge holds the only gavel
</td> </tr> </table>
[!IMPORTANT] No deploy or rollback ever executes autonomously. Only a verified human holding Switch's exclusive approver role can issue a binding verdict. Agents that try to self-approve are rejected.

⚡ 60-Second Overview
Traditional AI code review is passive and shallow. Catastrophic outages happen because nobody rigorously argued against shipping, or verified the rollback. Ship Court turns AI agents from polite assistants into accountable courtroom participants.
<div align="center">
flowchart LR
    A["📥 1. Case Intake"] --> B["🗣️ 2. Cross-Examination"]
    B --> C["🛡️ 3. Factual Defense"]
    C --> D["↩️ 4. Rollback Proof"]
    D --> E["👩‍⚖️ 5. Human Verdict"]
    E --> F["📜 6. Release Brief"]
    style A fill:#312e81,stroke:#818cf8,color:#fff
    style B fill:#7f1d1d,stroke:#f87171,color:#fff
    style C fill:#14532d,stroke:#4ade80,color:#fff
    style D fill:#78350f,stroke:#fbbf24,color:#fff
    style E fill:#581c87,stroke:#c084fc,color:#fff
    style F fill:#0c4a6e,stroke:#38bdf8,color:#fff
</div> <details> <summary><b>👉 Click to expand each stage</b></summary> <br/>
#	Stage	What happens
1	📥 Case Intake	A developer proposes a release; the Court Clerk convenes a courtroom in the shared Switch room #ship-court.
2	🗣️ Adversarial Cross-Examination	The Prosecutor files at most 3 evidence-backed objections, drawing on precedent from the Incident Historian.
3	🛡️ Factual Defense	The Defender must answer every objection in order, or explicitly mark it CONCEDED.
4	↩️ Guaranteed Reversibility	The Rollback Engineer validates target version, runbook command, health checks and owner.
5	👩‍⚖️ Exclusive Human Gate	A human Release Judge with the approver role issues APPROVE, BLOCK, or SHIP WITH CONDITIONS.
6	📜 Verifiable Artifact	Switch records the decision, assigns follow-up tasks, and publishes a signed Release Brief.
</details>

🎭 Meet the Cast
<div align="center">
	Agent	Role	Superpower
📋	Court Clerk	Orchestrator	Opens cases, tracks state, calls the verdict
🗃️	Incident Historian	Memory	Surfaces past failures (INC-017) as precedent
🔥	Prosecutor	Adversary	≤ 3 objections: BLOCKING · WARNING · NOTE
🛡️	Defender	Advocate	Answers each objection or CONCEDED
↩️	Rollback Engineer	Safety net	Verifies version, command, health checks, owner
👩‍⚖️	Human Release Judge	The only gavel	Exclusive approver role
</div>

🎬 The Trial: Live Interaction Sequence
sequenceDiagram
    autonumber
    actor Dev as 👩‍💻 Developer
    participant CL as 📋 Clerk
    participant HI as 🗃️ Historian
    participant PR as 🔥 Prosecutor
    participant DE as 🛡️ Defender
    participant RB as ↩️ Rollback
    actor J as 👩‍⚖️ Human Judge (Priya)

    Dev->>CL: open case acme/shop PR #482
    CL->>HI: search incident memory
    HI-->>PR: INC-017 pricing mismatch precedent
    PR->>DE: OBJ-1 BLOCKING · OBJ-2 WARNING · OBJ-3 NOTE
    DE->>RB: mitigated · CONCEDED · 5% canary proposed
    RB->>CL: rollback plan verified, auto-execution disabled
    CL->>J: ready for verdict
    J->>CL: verdict CONDITIONS
    CL-->>Dev: Switch tasks created + signed Release Brief
<details> <summary><b>🎞️ Replay the full transcript (click to expand)</b></summary>
Developer:              @court-clerk open case https://github.com/acme/shop/pull/482

Court Clerk:            Case SC-0482 opened. Change: dynamic checkout pricing.
                        Affected: checkout-service, cart-service, pricing-worker. CI: 42 passed.
                        @historian: Please search incident memory for relevant precedent.

Incident Historian:     Relevant precedent found: INC-017.
                        A pricing-related change on 2026-08-19 caused cart total mismatch
                        (41 failed checkouts).
                        Lesson: Require server-side pricing assertion and mismatch alert.
                        @prosecutor: Formulate objections based on precedent.

Prosecutor:             Prosecution Objections:
                        • OBJ-1 [BLOCKING]: Dynamic pricing may create cart-total mismatch. Evidence: INC-017.
                        • OBJ-2 [WARNING]:  No monitoring exists for pricing inconsistency.
                        • OBJ-3 [NOTE]:     Rollout percentage is not specified.
                        @defender: Please address each objection in order or concede.

Defender:               Defense Responses:
                        • For OBJ-1: Pricing is calculated only server-side; validated by
                                     pricing_consistency_test.py.
                        • For OBJ-2: CONCEDED. No mismatch alert currently exists.
                        • For OBJ-3: Proposed 5% canary rollout with progressive stepping.
                        @rollback: Please produce validated rollback plan.

Rollback Engineer:      Rollback plan verified: target version v2.13.2.
                        Command: ./scripts/rollback.sh checkout-service v2.13.2
                        Health checks: checkout error rate < 1%, cart latency < 400ms,
                                       pricing consistency job passes.
                        Rollback owner: Priya (READY). Auto-execution is disabled.

Court Clerk:            Case ready for verdict. Unresolved blocking condition: pricing mismatch alert.
                        Awaiting binding verdict from Human Release Judge (@Priya).

Priya (Human Judge):    @court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert;
                        Priya owns rollback

Court Clerk:            Verdict recorded: CONDITIONS.
                        Switch Tasks Created:
                          1. Configure canary 5% rollout            — owner: Priya
                          2. Add checkout mismatch alert            — owner: DevOps
                          3. Confirm rollback owner + rehearse      — owner: Priya
                        Signed Release Brief published to #ship-court.
</details>

🔌 Why Switch Is Load-Bearing
The Remove-Switch Test: take Switch out and the architecture collapses.
<div align="center">
🧱 Switch capability	💥 What breaks without it
Durable Room State	#ship-court holds the case timeline, agent identities and evidence logs. No shared memory → no trial.
Multi-Agent Session Routing	Coordinates agents across server, developer laptop and ops host.
Exclusive approver Role	Guarantees only a verified human can issue verdicts; agent self-approval is rejected.
Task & Decision Storage	Turns conditional verdicts into assigned, trackable Switch tasks.
</div>

🏛️ Architecture
flowchart TB
  subgraph VOICE["🎙️ Third Voice · Boardroom OS Floor Controller"]
    TV["Third Voice Agent<br/>✋ / 🔎 / 💡 / ⚠️ Right-to-Speak Protocol"]
  end

  subgraph WORK["👩‍💻 Working Phase: Three Teammates in Antigravity"]
    T1["Teammate 1<br/>Frontend Scope"]
    T2["Teammate 2<br/>Checkout / Pricing Scope"]
    T3["Teammate 3<br/>Infra / Auth Scope"]
    AG["Antigravity Scope Guard<br/>PreToolUse Hook + Collision Detector"]
    T1 & T2 & T3 --> AG
  end

  subgraph COURT["⚖️ COURTROOM · 3-AI Adversarial Trial (Switch Room)"]
    CLK["Court Clerk + Incident Historian"]
    PRO["Prosecutor<br/>Risk & Incident Matching"]
    DEF["Defender<br/>Mitigations & Safeguards"]
    JDG["Human Judge Gate<br/>auto_approve: false"]
    CLK --> PRO --> DEF --> JDG
  end

  subgraph DEC["📜 Decisions & Autonomous GitHub Ops"]
    DLED["Immutable Decision & Audit Ledger"]
    GHOPS["GitHub Ops Agent<br/>PRs · Reviews · Labels · Rollback Branches"]
    JDG --> DLED --> GHOPS
  end

  subgraph EARTH["🌍 PARALLEL EARTH · Blast-Radius Simulation"]
    PE["Parallel Earth Engine<br/>Dependency Graph + Canary Stress"]
    ESIM["Earth Simulation<br/>Downstream Closure · SLA · Revenue Exposure"]
    OBS["Results & Observations<br/>Rollback Sentinel Verification"]
    GHOPS --> PE --> ESIM --> OBS
  end

  AG -->|"Scope collision / Auto-Subpoena"| COURT
  TV <-->|"Huddle whisper & contradiction alerts"| WORK
  TV <-->|"Floor request & evidence injection"| COURT
  TV <-->|"Simulation telemetry summary"| EARTH
  OBS -->|"Feedback loop: verified telemetry & conditions"| COURT
<details> <summary><b>🖥️ Machine topology (ASCII view)</b></summary>
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
</details>

✅ Verification Dashboard
[!NOTE] We separate what is verified live from what is pending, so nothing here is smoke and mirrors.
<div align="center">
Capability	Status	Evidence
Groq provider credential	✅ LIVE	HTTP 200 via api.groq.com, ~46 ms
Real 3-bot LLM courtroom	✅ LIVE	Prosecutor, Defender, Judge produce unscripted LLM tokens
Local web console UI	✅ LIVE	http://127.0.0.1:8080/ with interactive debate & power meter
Switch template lint	✅ LIVE	0 errors, 0 warnings via switch_core.template_lint
Switch template planning	✅ LIVE	5 agents, aliases & approver role via plan_template
Human Approver Gate	✅ LIVE	Non-human and unauthorized callers blocked
Documentation suite	✅ LIVE	runtime-discovery.md, integration-evidence.md, compliance-matrix.md
Pytest suite	✅ 42 passed	42 passed, 1 skipped (ControlServer closed gate)
Docker Desktop engine	⬜ Pending	Requires interactive UAC approval on Windows
Switch Console (Electron)	⬜ Installed	%LOCALAPPDATA%\Programs\Switch Console Canary
Mattermost container bridge	⬜ Awaiting Docker	startNativeMattermost() checks for the Docker engine
Live Switch-routed chat	⬜ Awaiting Docker	Needs a containerized Mattermost #ship-court room
</div>
[!WARNING] Live vs. simulation clarity: the 3-bot courtroom runs with real live LLM inference and local web/API endpoints. End-to-end routing through containerized Mattermost stays blocked until Docker Desktop is approved on Windows.

🦸 The 5 Superpowers
Beyond the verified Ship Court core, we are extending the repo into one continuous Ship Court × Boardroom OS × Antigravity × Parallel Earth lifecycle. Tap a card to open it.
[!NOTE] The core courtroom, Switch room, scope guard and dependency graph already live in the repo. The five modules below are the engineering plan that wires them together; each file path shows where the work lands.
<details> <summary><b>🪝 Superpower 1 · Antigravity Auto-Subpoena</b> &nbsp;<code>server/antigravity_subpoena.py</code></summary> <br/>
Three teammates (Teammate-1-Frontend, Teammate-2-Pricing, Teammate-3-Infra) work simultaneously in Antigravity, with workspace boundaries enforced by linking_antigravity/scope_guard.
When one agent crosses a boundary (for example Teammate-2-Pricing editing services/checkout-service/payment_contract.py, owned by Teammate-3-Infra), AntigravitySubpoenaBridge intercepts the ViolationEvent / ApprovalRequest. Instead of failing silently in a local terminal, it posts a Subpoena Notice into the Switch-connected chat and calls CaseManager.open_case() to summon the courtroom.
Why it matters: it links coding agents on three separate machines into one shared governance loop, which is exactly what Switch is for.
</details> <details> <summary><b>🌍 Superpower 2 · Parallel Earth Blast-Radius Engine</b> &nbsp;<code>server/parallel_earth.py</code></summary> <br/>
Before the human judge rules, ParallelEarthSimulator spins up a virtual staging twin using DependencyGraph and RollbackSentinel. It will:
* 🌊 simulate synthetic traffic waves
* 🕸️ compute downstream service-cascade probability
* 💸 calculate financial exposure in $/min across Tier-1 services
* ⏱️ verify the rollback command restores health inside the SLA window
* 📨 post a structured EarthSimulationReport to the courtroom and chat
</details> <details> <summary><b>✋ Superpower 3 · Third Voice &amp; Right-to-Speak Protocol</b> &nbsp;<code>server/floor_controller.py</code></summary> <br/>
A deterministic FloorRequestProtocol state machine keeps AI from rudely talking over humans:
stateDiagram-v2
    [*] --> Listening
    Listening --> Evaluating
    Evaluating --> HandRaised
    HandRaised --> Waiting
    Waiting --> Granted: human grants floor
    Waiting --> Expired: TTL elapsed
    Granted --> Speaking
    Speaking --> Yielding
    Yielding --> Listening
    Expired --> Listening
Third Voice monitors three streams at once: teammates / Antigravity (scope drift), the courtroom (contradictions against prior approved decisions: the Contradiction Radar), and Parallel Earth (unmitigated Tier-1 blast radius).
It raises a hand (✋ 🔎 💡 ⚠️) with an expiring card: [🎙️ Grant Floor] · [💬 Text Instead] · [✖ Dismiss]. Only one AI agent can hold the floor at a time.
</details> <details> <summary><b>💬 Superpower 4 · Multi-Persona Discord &amp; Mattermost Bridge</b> &nbsp;<code>server/bridge_connector.py</code></summary> <br/>
ChatBridgeConnector gains auto-detection of Discord webhooks alongside Mattermost and Slack. Every agent role (clerk, prosecutor, defender, judge, rollback, antigravity-guard, third-voice, parallel-earth, github-ops) gets its own username, avatar_url, colour-coded embeds and action metadata, while keeping backward compatibility with tests/test_bridge_connector.py.
</details> <details> <summary><b>🐙 Superpower 5 · Autonomous GitHub Operations Agent</b> &nbsp;<code>server/github_ops_agent.py</code></summary> <br/>
Gives the project real teeth on GitHub:
1. PR review & evidence comments: posts the full courtroom transcript, Parallel Earth blast-radius tree and rollback plan onto the PR.
2. Governance labels: ship-court:approved · ship-court:conditional · ship-court:blocked · parallel-earth:verified · antigravity:scope-checked.
3. Condition issues: a CONDITIONAL verdict opens a tracked Issue per rollout condition.
4. Emergency rollback PRs: on post-merge degradation, opens a rollback/<case_id> branch and revert PR, still gated by auto_approve: false.
5. Offline-safe mode: live GitHub REST API when GITHUB_TOKEN is set, otherwise a deterministic local ledger (data/github_ops_ledger.json) so judges can reproduce everything.
</details>

🔄 End-to-End Lifecycle
<div align="center">
Phase	Trigger	Switch handoff	Artifact
1 · 🪝 Antigravity Monitoring	Teammate 2 touches pricing-engine + checkout-service	antigravity-guard catches the cross-scope edit via PreToolUse and posts an Auto-Subpoena	ViolationEvent + Case CASE-AG-101
2 · 🎙️ Contradiction Radar	third-voice cross-checks against the Decision Ledger	Raises ⚠️ HIGH PRIORITY HAND; human clicks Grant Floor	FloorRequest + 20 s spoken briefing (conflict with #DEC-014)
3 · ⚖️ Courtroom Trial	clerk opens the 4-round trial	historian → prosecutor → defender	Objections / Defenses ledger
4 · 🌍 Parallel Earth	Court requests empirical blast-radius proof	parallel-earth runs calculate_blast_radius() + canary probe	EarthSimulationReportwith $/min exposure
5 · 👩‍⚖️ Verdict & GitHub Ops	Human issues !verdict CONDITIONS	enforce_human_verdict_gate()dispatches github-ops	PR review, labels, condition issues, sealed audit ledger
</div>

🗂️ Repository Map
switch-AI/
├── 🧠 .claude/skills/ship-court/     # Claude skill for the courtroom workflow
├── 🤖 agents/                        # Agent definitions
├── 🗄️ data/                          # Incident memory & ledgers
├── 🎬 demo/                          # Demo assets
├── 📚 docs/                          # runtime-discovery, integration-evidence, compliance-matrix
├── 🪝 linking_antigravity/           # Antigravity scope_guard (PreToolUse hook engine)
├── 🚪 rooms/                         # Switch room definitions
├── ⚙️ server/                        # Courtroom, Switch room, bridge, dependency graph, rollback sentinel
├── 🔌 switch/                        # ship-court.template.yaml + validate_template.py
├── 🧪 tests/                         # pytest suite, stress & load tests
├── .env.example
├── requirements.txt
├── CLAUDE.md
└── LICENSE                           # MIT

🧪 Run It Yourself
<details open> <summary><b>1️⃣ Clone &amp; install</b></summary>
git clone https://github.com/GaneshNair007/switch-AI.git
cd switch-AI
pip install -r requirements.txt
cp .env.example .env        # add your provider keys (e.g. Groq)
</details> <details> <summary><b>2️⃣ Validate the Switch template</b></summary>
python switch/validate_template.py
</details> <details> <summary><b>3️⃣ Run the test suite</b></summary>
python -m pytest -v tests/
</details> <details> <summary><b>4️⃣ 10-cycle continuous stress verifier</b></summary>
python tests/stress_and_health_check.py
</details> <details> <summary><b>5️⃣ Switch-native courtroom runner</b></summary>
# Runs natively when Switch Console is installed, or with offline protocol fallback
python -m server.switch_native_runner
</details> <details> <summary><b>6️⃣ Google Opal workflow bridge</b></summary>
python -c "from server.opal_workflow import GoogleOpalWorkflowBridge; print(GoogleOpalWorkflowBridge().execute_workflow())"
</details> <details> <summary><b>7️⃣ Local multi-agent simulation</b></summary>
python -m server.local_courtroom_simulation
</details> <details> <summary><b>8️⃣ High-concurrency stress test (20,000 requests)</b></summary>
# 20,000 requests across 100 worker threads
python tests/heavy_load_test.py -n 20000 -c 100
</details> <details> <summary><b>🌐 Open the live web console</b></summary>
Start the server, then visit http://127.0.0.1:8080/ for the interactive debate view and power meter.
</details>

📜 The Artifact: Signed Release Brief
Every case ends in an auditable Release Brief stored with the case record.
<details> <summary><b>📄 See a sample brief (SC-0482)</b></summary>
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
</details>

🏆 Built for the Judges
<div align="center">
Pillar	How we answer it
🔌 Use of Switch	Passes the Remove-Switch Test: multiple agents across machines coordinate through one Switch room with role aliases and an exclusive approver gate.
🛠️ Technical Execution	Deterministic state machines (CaseState, FloorState), a 42-test pytest suite, a 20,000-request load test, and offline-safe reproduction.
💡 Creativity & Impact	Business track (adversarial deploy court, GitHub Ops, Parallel Earth) meets creative track (Antigravity collision monitor, hand-raise protocol).
📖 Presentation & Docs	Interactive web console, declarative ship-court.template.yaml, a full docs suite, and this README.
</div>

👥 The Team
<div align="center"> <table> <tr> <td align="center" width="240"> <img src="https://img.shields.io/badge/-%F0%9F%A7%91%E2%80%8D%E2%9A%96%EF%B8%8F-7c3aed?style=for-the-badge" alt=""/><br/> <h3>Arjit Ujjawal</h3> <sub>Builder · Ship Court</sub> </td> <td align="center" width="240"> <a href="https://github.com/GaneshNair007"> <img src="https://avatars.githubusercontent.com/u/232020027?s=120&v=4" width="96" style="border-radius:50%" alt="Ganesh Nair"/> </a><br/> <h3><a href="https://github.com/GaneshNair007">Ganesh Nair</a></h3> <sub>Builder · Repo owner · <code>@GaneshNair007</code></sub> </td> <td align="center" width="240"> <img src="https://img.shields.io/badge/-%F0%9F%A7%91%E2%80%8D%E2%9A%96%EF%B8%8F-db2777?style=for-the-badge" alt=""/><br/> <h3>Jayvee Shah</h3> <sub>Builder · Ship Court</sub> </td> </tr> </table>
Event: WeMakeDevs × DevTools Academy × Switch AI — Flip the Switch  ·  Primary track: Track 01, Best Business Workflow  ·  Also aiming at: Track 02, Best Personal/Creative Workflow
</div>

🔗 Links
* 📦 Repository: GaneshNair007/switch-AI
* 🏁 Hackathon: wemakedevs.org/hackathons/switch · DevTools Academy
* 🔌 Switch runtime: sandbox-quantum/switch · Docs
* 📄 License: MIT
<div align="center"> <br/>
⚖️ Court is adjourned. Nothing ships until a human says so. ⚖️
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24,30&height=140&section=footer" alt="footer wave" width="100%"/> </div>     
