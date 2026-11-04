# Hackathon Alignment & Judging Criteria

## 1. Hackathon Overview
- **Event:** WeMakeDevs × DevTools Academy × Switch AI Flip the Switch Hackathon (Nov 4–7, 2026)
- **Track:** Track 01 — Best Business Workflow
- **Submission Deadline:** November 7, 2026 at 11:59 PM IST

## 2. Judging Pillars Scoring Breakdown

### 1. Use of Switch (25%)
- **Load-bearing centrality:** Switch is not just a chat relay; it stores case states, maintains agent sessions, enforces exclusive human-approver roles, registers structured decisions, and tracks conditional follow-up tasks.
- If Switch is removed, distributed multi-machine agent coordination and auditable release governance collapse.

### 2. Technical Execution (25%)
- Fully reproducible clean-room setup via `switch/ship-court.template.yaml`.
- Parameterized configuration (no hardcoded machine paths).
- Complete test suite verifying state transitions, severity classification, defense matching, and rollback validation.
- Pluggable external scrapers (Firecrawl API, GitHub API, local JSON incident store).

### 3. Creativity & Impact (25%)
- Moves beyond passive single-agent review ("Does this PR look good?") to structured adversarial cross-examination.
- Solves a multi-billion dollar enterprise problem: catastrophic production outages caused by unvetted deployments and missing rollback plans.

### 4. Presentation (25%)
- Intuitive courtroom metaphor: Clerk, Prosecutor, Historian, Defender, Rollback Engineer, and Human Release Judge.
- Clear 4-round bounded state machine resulting in an auditable Release Brief artifact.

## 3. Compliance Guardrails
- **No auto-approval:** `auto_approve: false` hard-enforced.
- **No destructive autonomy:** Rollbacks require human authorization.
- **Scoped credentials:** Zero production secrets committed.
- **Anti-hallucination:** Agents must cite real evidence or concede.
