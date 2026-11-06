# Flip the Switch Hackathon Compliance Matrix

This document benchmarks Ship Court against the official rules and guidelines for **Track 01: Best Business Workflow** of the **Flip the Switch Hackathon** ([Official Rules](https://www.wemakedevs.org/hackathons/switch/rules)).

---

## Compliance Mapping

| Hackathon Requirement | Official Source | Ship Court Implementation | Concrete Evidence | Remaining Gap |
| :--- | :--- | :--- | :--- | :--- |
| **Track 01: Business Workflow** | [Rules § Tracks](https://www.wemakedevs.org/hackathons/switch) | Multi-agent release review boardroom where AI agents argue risk before human signs off | `switch/ship-court.template.yaml` defines 5 courtroom agents & exclusive approver role | None |
| **Use of Switch** | [Rules § Judging](https://www.wemakedevs.org/hackathons/switch/rules) | Workflow defined as a native Switch room template (`ship-court.template.yaml`) using Switch Core v0.31.0 schema | Passed official `lint_template()` with 0 errors/warnings and `plan_template()` with 5 agents | Native Mattermost chat bridge requires Docker Desktop |
| **Human-in-the-Loop Gate** | [Rules § Judging](https://www.wemakedevs.org/hackathons/switch/rules) | Exclusive `approver` role (@Priya). AI agents and unauthorized users are cryptographically barred from self-approving | Verified via `test_unauthorized_judge_rejected()` and `test_bot_cannot_approve()` | None |
| **Structured Multi-Agent Roles** | [Track 01 Guidelines](https://www.wemakedevs.org/hackathons/switch) | 5 distinct roles: Clerk (Bailiff), Historian (Forensics), Prosecutor (Adversary), Defender (SRE), Rollback Engineer | Verified in `server/agent_runners.py` and `server/live_courtroom_debate.py` | None |
| **Real LLM Inference** | [Track 01 Guidelines](https://www.wemakedevs.org/hackathons/switch) | Live LLM agents powered by Groq (`qwen/qwen3.8-27b`) and NVIDIA NIM with zero hardcoding | Live HTTP 200 API calls returning dynamic cross-examinations | None |
| **Audit Ledger & Tasks** | [Rules § Deliverables](https://www.wemakedevs.org/hackathons/switch) | Generates structured Markdown Release Brief and binding tasks recorded in audit ledger | Verified in `server/audit_ledger.py` and `server/release_brief.py` | None |
| **Honest Status Reporting** | [Rules § Submissions](https://www.wemakedevs.org/hackathons/switch/rules) | Explicit separation between LIVE, SIMULATION, DETERMINISTIC, and UNKNOWN | Verification table in README and `docs/integration-evidence.md` | Docker Desktop install requires human UAC click |

---

## Verified vs Pending Execution Summary

- **Verified Working**:
  - Switch Core template linting & planning (0 errors, 0 warnings).
  - Real 3-bot LLM adversarial courtroom arena (live tokens from Groq/NVIDIA).
  - Interactive local web console on `http://127.0.0.1:8080`.
  - Exclusive human approver security gate.
  - Signed Release Brief artifact generation.
  - All 11 unit & simulation tests passing.
- **Pending Human Action**:
  - User double-clicking `C:\Users\Ganesh Nair\Downloads\DockerDesktopInstaller.exe` to approve Windows UAC elevation, enabling containerized local Mattermost.
