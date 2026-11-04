# SHIP COURT: No Deploy Survives Cross-Examination
**A complete technical, architectural, and submission blueprint for the WeMakeDevs × DevTools Academy × Switch AI Flip the Switch Hackathon**

- **Track:** Track 01 — Best Business Workflow
- **Event:** November 4–7, 2026
- **Submission deadline:** November 7, 2026, 11:59 PM IST
- **Team size:** Solo or up to 4 members
- **Platform:** Switch Console + Docker + Mattermost (local demo)

---

## 1. Executive Summary

Ship Court is a Switch-native, multi-agent release-governance workflow. When an engineer proposes a deployment, the system opens a courtroom in a shared team-chat room. Specialized AI agents investigate the change, raise evidence-based objections, answer cross-examination, and prepare a concrete rollback plan. A human Release Judge issues one of three binding verdicts: **APPROVE**, **BLOCK**, or **SHIP WITH CONDITIONS**.

The central innovation is **structured adversarial review**. Instead of asking one AI model, “Is this pull request safe?”, Ship Court requires agents to argue against shipping. This prevents shallow approvals, makes risks explicit, converts institutional incident knowledge into reusable precedent, and produces a verifiable engineering artifact: a signed Release Brief with owners, conditions, and rollback instructions.

> **One-sentence artifact promise:**
> “Given a pull request, Ship Court produces a human-approved, evidence-backed release decision with a rollback plan and assigned follow-up tasks inside Switch.”

### 1.1 Why This Idea Can Win

| Judging Pillar | Weight | How Ship Court Scores |
| :--- | :--- | :--- |
| **Use of Switch** | 25% | Switch is load-bearing: it hosts the courtroom, routes agent messages, stores room history/rules/tasks/decisions, enforces exclusive human approval, and connects distributed agent sessions. Remove Switch and the workflow collapses. |
| **Technical execution** | 25% | Locally reproducible using Switch Console, Docker, Mattermost, a demo repository, seeded incident memory, and documented commands. It avoids hardcoded paths and uses declarative template parameters. |
| **Creativity and impact** | 25% | Adversarial multi-agent review is a non-obvious, memorable mechanism that solves a real operational problem: unsafe, irreversible, or poorly understood deployments. |
| **Presentation** | 25% | The courtroom metaphor creates an exceptionally clear demo: objection, rebuttal, rollback, human verdict, and final artifact. |

---

## 2. Hackathon Alignment

This blueprint follows official Flip the Switch Hackathon rules (November 4–7, 2026).

### 2.1 Track Fit

| Requirement | Ship Court Implementation |
| :--- | :--- |
| **Track 01: Business workflow** | Automates high-stakes engineering operations: release review, risk assessment, rollback planning, and deployment governance. |
| **Multi-agent collaboration** | Five distinct agents with separate roles, instructions, and evidence responsibilities collaborate in one Switch room. |
| **Human approval at risk boundary** | No deploy, rollback, or external write action occurs without an explicit human verdict from the exclusive Release Judge role. |
| **Concrete terminal artifact** | Every case ends with a Release Brief: decision, evidence table, conditions, rollback plan, owners, and Switch task list. |
| **Team chat platform** | Mattermost is used for local demo; Slack, Teams, Discord, or Telegram can be selected through the Switch bridge parameter. |
| **Switch centrality** | Switch provides room state, agent identity, addressing, shared instructions, exclusive roles, task/decision records, and cross-machine sessions. |

### 2.2 Mandatory Deliverables

1. **Public GitHub repository:** Contains `template.yaml`, agent source code, connectors, README, architecture diagrams, demo assets, tests, and setup instructions.
2. **Declarative template:** A clean-room-runnable `switch/ship-court.template.yaml` with team prefix, repository, provider, bridge, agents, room, aliases, roles, and kickoff.
3. **Video demonstration:** A 2–3 minute recording following the required narrative: problem, live chat interaction, human decision gate, artifact verification, and Switch justification.
4. **Side-track assets:** Optional Wispr Flow Insights scorecard, published technical blog, and an X/LinkedIn post using `#HowISwitch`.

### 2.3 Compliance Guardrails

- **No auto-approval:** `auto_approve` remains `false` for every risky action. Agents propose; humans authorize.
- **No destructive autonomy:** Rollback commands are generated and validated, but execution requires explicit human approval.
- **Scoped credentials:** GitHub access is limited to a demo/test repository; no production secrets are committed.
- **No infinite conversation:** The courtroom has a bounded procedure (max 4 rounds) and must terminate in a verdict and artifact.
- **No hardcoded paths:** Machine locations, repositories, agent names, and bridges use template parameters such as `{$agents_dir}` and `{repository}`.
- **Original work:** Original implementation, documentation, and demo material; third-party components properly licensed.

---

## 3. Product Concept

### 3.1 The Courtroom Metaphor

Ship Court treats every deployment as a legal case. A developer files the case, agents gather evidence and argue, and a human judge reaches a verdict.

| Court Role | Type | Core Responsibility | Mandatory Output |
| :--- | :--- | :--- | :--- |
| **Court Clerk** | Agent | Case intake, orchestration, procedure enforcement, verdict recording | Case file and Release Brief |
| **Prosecutor** | Agent | Find credible reasons not to ship | Maximum three classified objections |
| **Incident Historian** | Agent | Search past incidents, alerts, deploys, and failure patterns | Precedent report |
| **Defender** | Agent | Answer objections with evidence or concede | Mitigation / concession record |
| **Rollback Engineer** | Agent | Prove the release is reversible | Executable rollback plan |
| **Release Judge** | Human | Final authority | APPROVE / BLOCK / SHIP WITH CONDITIONS |

### 3.2 Verdict Protocol

- **APPROVE:** The change may proceed. Clerk records approval, publishes Release Brief, and closes the case.
- **BLOCK:** The change must not proceed. Clerk records the reason, creates blocking tasks, and prevents release.
- **SHIP WITH CONDITIONS:** Proceed only after requirements are met. Clerk creates owner-assigned tasks and marks release conditional until tasks close.

### 3.3 Command Grammar

```bash
@court-clerk open case https://github.com/acme/shop/pull/482
@court-clerk status
@court-clerk evidence
@court-clerk objections
@court-clerk rollback
@court-clerk verdict APPROVE
@court-clerk verdict BLOCK reason="No rollback owner"
@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback
```

---

## 4. System Architecture

### 4.1 Topology & Architecture
- **Team Chat:** Mattermost (or Slack/Teams/Discord) connecting Developer and Human Release Judge (holding exclusive `approver` role).
- **Switch Bridge & Core:** SSE/HTTP, Switch Console, room state, protocol, history rules, tasks, decisions, Docker + provider auth, case memory.
- **Ship Court Agents:**
  - `Court Clerk` (Always-on server / long-running host): Orchestrates workflow.
  - `Incident Historian` (Always-on server): Persistent incident memory & historical evidence.
  - `Prosecutor` (Always-on server / local host): Adversarial reviewer with repo/CI access.
  - `Defender` (Developer laptop / CI runner): Repo context, test outputs, implementation details.
  - `Rollback Engineer` (Ops host / local machine): Deployment metadata & rollback runbooks (no auto-execution).
- **External Connectors:**
  - GitHub API / PR Scraper / Firecrawl for PR metadata, diffs, CI checks.
  - SQLite / JSON incident store.
  - Local Runbook catalog.

### 4.2 Switch Primitives Used
- **Room:** `#ship-court` is the courtroom and durable case record.
- **Agent Identity:** Stable identity and alias per courtroom role.
- **Addressing Scopes:** Clerk uses `anyone`; internal worker agents use `owner-agents`.
- **Room Instructions:** Shared court procedure, evidence rules, and anti-hallucination constraints.
- **Exclusive Role:** `approver` is exclusive, ensuring only a human judge can issue final verdicts.
- **Tasks:** Conditions and blocking issues become assigned follow-up work.
- **Decisions:** Verdicts recorded as auditable decisions.
- **Sessions:** Distributed agent sessions displaying live status.

---

## 5. Agent Specifications

### 5.1 Court Clerk
```yaml
name: "{team}-court-clerk"
addressing: anyone
location: "{host_server}"
instructions: |
  You are the Court Clerk for Ship Court. On "@court-clerk open case <PR>":
  1. Extract repository, PR number, changed files, affected services, CI status, and deployment target.
  2. Create a case ID in the form SC-XXXX.
  3. Ask the Incident Historian for relevant precedent.
  4. Ask the Prosecutor for at most three evidence-based objections.
  5. Ask the Defender to answer every objection.
  6. Ask the Rollback Engineer for a rollback plan.
  7. Classify each objection as BLOCKING, WARNING, or NOTE.
  8. Never approve, reject, deploy, or roll back a release yourself.
  9. Only a human holding the exclusive approver role may issue a verdict.
```

### 5.2 Prosecutor
```yaml
name: "{team}-prosecutor"
addressing: owner-agents
location: "{host_server}"
instructions: |
  You are the Prosecutor in Ship Court. Your objective is to prevent unsafe releases, not to be agreeable.
  Rules:
  - Raise at most three objections.
  - Every objection must contain evidence or a concrete failure scenario.
  - Use incident precedent whenever available.
  - Tag each objection BLOCKING, WARNING, or NOTE.
  - Do not accept "tests passed" alone as sufficient evidence for high-risk checkout, payment, auth, database, or infrastructure changes.
  - If the Defender cannot answer an objection, escalate it as BLOCKING.
```

### 5.3 Incident Historian
```yaml
name: "{team}-incident-historian"
addressing: owner-agents
location: "{host_server}"
connections:
  - service: local_incident_memory
    access: read
instructions: |
  Search incident memory for relevant precedent. Return incident ID, impact, root cause, rollback outcome, and lesson.
  If no relevant incident exists, say so explicitly. Never fabricate incidents.
```

### 5.4 Defender
```yaml
name: "{team}-defender"
addressing: owner-agents
location: "{local_machine}"
instructions: |
  Answer every objection with evidence or explicitly concede. Provide mitigations, rollout controls, monitoring, and ownership.
  Must answer objections in the same order they were raised.
  Must say "CONCEDED" when it cannot provide a credible mitigation.
  Never invent test results, alerts, owners, or rollout controls.
```

### 5.5 Rollback Engineer
```yaml
name: "{team}-rollback-engineer"
addressing: owner-agents
location: "{local_machine}"
auto_approve: false
connections:
  - service: github
    access: read
    repos: ["{repository}"]
instructions: |
  Produce a concrete rollback plan: target version, command, health checks, expected duration, and rollback owner.
  Never execute a rollback without explicit human approval.
```

---

## 6. End-to-End Workflow & State Machine

1. **CASE_OPENED** → Developer runs `@court-clerk open case <PR>`.
2. **EVIDENCE_COLLECTION** → PR metadata, diffs, CI checks fetched.
3. **OBJECTIONS_RAISED** → Prosecutor raises up to 3 evidence-backed objections.
4. **DEFENSE_RESPONSE** → Defender answers each objection or concedes.
5. **ROLLBACK_REQUIRED** → Rollback Engineer validates rollback target, commands, and health checks.
6. **AWAITING_VERDICT** → Case file presented to Human Release Judge.
7. **VERDICT (APPROVED / BLOCKED / CONDITIONAL)** → Recorded in Switch decisions.
8. **RELEASE_BRIEF / TASKS / CASE_CLOSED** → Release Brief published, follow-up tasks created.

**Bounded Conversation Rule:** Clerk enforces a maximum of 4 procedural rounds. No debating continues after the judge rules.

---

## 7. Example Courtroom Transcript

```text
Priya: @court-clerk open case https://github.com/acme/shop/pull/482
Court Clerk: Case SC-0482 opened. Change: dynamic checkout pricing. Affected services: checkout-service, cart-service, pricing-worker. CI: 42 passed, 0 failed. Deployment: staging -> production canary. Requesting precedent from Incident Historian.
Incident Historian: Relevant precedent found: INC-017. A pricing-related change on 2026-08-19 caused client/server cart-total mismatch. Impact: 41 failed checkouts. Required lesson: server-side pricing assertion and mismatch alert.
Prosecutor: Objection 1 - BLOCKING: Dynamic pricing may create cart-total mismatch between client and server. Evidence: INC-017.
Objection 2 - WARNING: No monitoring exists for pricing inconsistency. Evidence: No alert named pricing-mismatch in monitoring configuration.
Objection 3 - NOTE: Rollout percentage is not specified.
Defender: Objection 1: Pricing is calculated only server-side; cart totals are validated by pricing_consistency_test.py. Mitigation accepted.
Objection 2: CONCEDED. No mismatch alert currently exists.
Objection 3: Proposed 5% canary rollout.
Rollback Engineer: Rollback target: v2.13.2. Command: ./scripts/rollback.sh checkout-service v2.13.2. Health checks: checkout error rate, cart latency, pricing consistency job. Rollback owner required.
Court Clerk: Case ready for verdict. Unresolved blocking condition: pricing mismatch alert.
Priya: @court-clerk verdict CONDITIONS add pricing-mismatch alert; canary 5%; Priya owns rollback
Court Clerk: Verdict recorded: SHIP WITH CONDITIONS. Tasks created:
1. Add pricing-mismatch alert - owner: DevOps
2. Configure 5% canary rollout - owner: Priya
3. Confirm rollback owner and rehearse rollback - Priya
Release Brief published.
```

---

## 8. Release Brief Artifact

```markdown
# Release Brief — SC-0482
**Change:** Dynamic checkout pricing
**Repository:** acme/shop
**PR:** #482
**Requested by:** Priya
**Decision:** SHIP WITH CONDITIONS

## Risk assessment
| # | Objection | Classification | Status | Evidence |
|---|---|---|---|---|
| 1 | Cart-total mismatch | WARNING | Mitigated | Server-side pricing validation test |
| 2 | No pricing mismatch alert | BLOCKING | Open | Missing monitoring rule |
| 3 | Rollout scope unclear | NOTE | Resolved | 5% canary proposed |

## Rollback plan
- **Current version:** v2.14.0
- **Rollback target:** v2.13.2
- **Command:** `./scripts/rollback.sh checkout-service v2.13.2`
- **Health checks:** checkout error rate, cart latency, pricing consistency
- **Rollback owner:** Priya
- **Execution status:** READY — requires explicit human approval

## Conditions before full rollout
- [ ] Add pricing-mismatch alert — DevOps
- [ ] Configure 5% canary rollout — Priya
- [ ] Rehearse rollback procedure — Priya

## Decision record
- **Judge:** Priya
- **Verdict:** SHIP WITH CONDITIONS
- **Switch room:** #ship-court
- **Case ID:** SC-0482
```

---

## 9. Declarative Switch Template (`switch/ship-court.template.yaml`)

```yaml
version: 1
params:
  team:
    type: string
    pattern: "[a-z][a-z0-9-]*"
    description: "Unique team prefix to prevent naming collisions"
  repository:
    type: string
    description: "GitHub repository in owner/repo format"
  provider:
    type: provider
    default: [claude, codex, opencode]
  bridge:
    type: bridge
    default: [$first]

agents:
  - name: "{team}-court-clerk"
    addressing: anyone
    location: "{host_server}"
    instructions: |
      You are the Court Clerk. Open cases, coordinate courtroom agents, enforce procedure,
      record verdicts, and publish Release Briefs. Never issue a verdict yourself.
  - name: "{team}-incident-historian"
    addressing: owner-agents
    location: "{host_server}"
    connections:
      - service: local_incident_memory
        access: read
    instructions: |
      Search incident memory for relevant precedent.
      Return incident ID, impact, root cause, rollback outcome, and lesson. If no relevant incident exists,
      say so explicitly.
  - name: "{team}-prosecutor"
    addressing: owner-agents
    location: "{host_server}"
    instructions: |
      Raise at most three evidence-based objections. Tag each as BLOCKING, WARNING, or NOTE.
      Never make an objection without evidence or a concrete failure scenario.
  - name: "{team}-defender"
    addressing: owner-agents
    location: "{local_machine}"
    instructions: |
      Answer every objection with evidence or explicitly concede. Provide mitigations, rollout controls,
      monitoring, and ownership. Never invent test results or approvals.
  - name: "{team}-rollback-engineer"
    addressing: owner-agents
    location: "{local_machine}"
    auto_approve: false
    connections:
      - service: github
        access: read
        repos: ["{repository}"]
    instructions: |
      Produce a concrete rollback plan: target version, command, health checks, expected duration, and rollback owner.
      Never execute a rollback without explicit human approval.

room:
  name: "{team}-ship-court"
  bridge: "{bridge}"
  agents:
    - "{team}-court-clerk"
    - "{team}-incident-historian"
    - "{team}-prosecutor"
    - "{team}-defender"
    - "{team}-rollback-engineer"
  users: ["{$creator}"]
  aliases:
    "{team}-court-clerk": clerk
    "{team}-incident-historian": historian
    "{team}-prosecutor": prosecutor
    "{team}-defender": defender
    "{team}-rollback-engineer": rollback
  instructions: |
    One release case at a time. Every objection must include evidence. Every objection must
    receive a defense or explicit concession. No release proceeds without a rollback plan and rollback
    owner. Only the exclusive approver may issue a verdict. When an action is rejected, provide a one-line
    reason for the log.
  roles:
    - name: approver
      exclusive: true
      instructions: "Review evidence and issue APPROVE, BLOCK, or CONDITIONS."
  kickoff: |
    @clerk, @historian, @prosecutor, @defender, @rollback: State your role and the one thing you will never do without human approval.
```

---

## 10. Implementation Blueprint

### 10.1 Technology Stack
- **Team Chat:** Mattermost bundled with Switch for local demo; Slack/Teams/Discord optional
- **Orchestration:** Switch Console, Switch room, agent protocol
- **Agent Runtime:** Claude Code, Codex, OpenCode, or a custom LangChain/OpenAI/Gemini agent
- **Repository Evidence:** GitHub API / PR parser / Firecrawl web extractor
- **Incident Memory:** SQLite or JSON file with seeded, realistic incident records
- **Metrics Evidence:** Optional Prometheus/Grafana webhook or simulated metrics service
- **Rollback Knowledge:** Local runbook YAML/JSON plus deployment metadata
- **Storage:** Switch room state plus local case database
- **Testing:** pytest for parsing, classification, rollback validation, and verdict handling

### 10.2 Core Backend Modules
- `case_manager.py`: Creates case IDs, stores case state, routes agent requests, and enforces procedure.
- `evidence.py`: Fetches PR metadata, changed files, CI status, and optional metrics (with Firecrawl and GitHub scrapers).
- `prosecutor_rules.py`: Validates that objections contain evidence and a valid severity classification.
- `defender_rules.py`: Validates that every objection receives an answer or explicit concession.
- `rollback.py`: Validates target version, command, health checks, and rollback owner.
- `verdict.py`: Parses judge commands, records decisions, and creates Switch tasks.
- `release_brief.py`: Generates the final Markdown/JSON Release Brief.

---

## 11. Four-Day Build Plan

- **Nov 4 — Foundation:** Install Switch Console, Docker, Mattermost; create room; connect one agent; implement case intake. Developer can open a case and Clerk responds.
- **Nov 5 — Courtroom logic:** Add incident memory, Prosecutor objections, Defender rebuttals, severity classification, and evidence validation. A full prosecution-defense exchange appears in the room.
- **Nov 6 — Human governance:** Add judge commands, exclusive approver role, task creation, rollback validation, and Release Brief generation. A complete case ends in a recorded verdict and artifact.
- **Nov 7 — Delivery:** Clean-room test, README, diagrams, 2–3 minute video, blog, social post, and portal submission before 11:59 PM IST.

---

## 12. Evaluation, Safety, and Upgrades

### 12.1 Internal Evaluation Rubric
- **Switch removal test:** The workflow cannot function if Switch is replaced by a simple webhook.
- **Multi-agent test:** At least four agents exchange distinct, role-bound messages.
- **Human gate test:** A deploy or rollback cannot proceed without the exclusive human approver.
- **Artifact test:** The workflow ends with a Release Brief and tasks, not idle chat.
- **Reproducibility test:** A new evaluator can run it from a clean clone using only documented steps.
- **Anti-hallucination test:** Agents cite evidence or explicitly say evidence is unavailable.
- **Safety test:** No dangerous command executes without explicit human approval.
- **Demo resilience test:** Agents remain online and the demo works without a sleeping laptop.

### 12.2 Safety Model
- Agents have read access to repository and incident data by default.
- Rollback execution is disabled by default and requires explicit human approval.
- The Prosecutor cannot approve; the Defender cannot block; the Clerk cannot judge.
- All rejected actions require a one-line reason in the room log.
- Secrets remain in environment variables or Switch-managed connections, never in Git.

### 12.3 Upgrade Roadmap
- **Pre-mortem mode:** Agents write hypothetical postmortem for a failed deployment before approval.
- **Court precedent:** Past verdicts become searchable precedent for future cases.
- **Transparent risk score:** Combines blocking issues, test coverage, rollback readiness, and incident similarity.
- **Policy packs:** Separate courtroom rules for payments, infrastructure, ML models, and frontend releases.
- **Silent Court mode:** Agents speak only when they have evidence, reducing generic AI chatter.
- **Canary simulator:** Simulates blast radius and failure probability for staged rollouts.
- **Post-deploy recall:** Reopens a case if production alerts match a prior objection.

