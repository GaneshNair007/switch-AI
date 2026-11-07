> Historical planning/sample evidence. Current verified behavior and limitations are documented in [docs/VERIFICATION.md](docs/VERIFICATION.md). Do not treat sample transcripts as live proof.

# MASTER ARCHITECTURAL & EXECUTION MANIFEST: SHIP COURT × BOARDROOM OS × ANTIGRAVITY × PARALLEL EARTH

**Repository:** GaneshNair007/switch-AI (Branch: `arjit`)
**Target Competition:** WeMakeDevs Flip the Switch Hackathon & DevTools Academy
**Core Runtime:** Switch AI Open-Source Agent Infrastructure

## 1. Unified 5-Ring Architecture
1. **Ring 1 — Three Teammates in Antigravity (`server/antigravity_subpoena.py`):** Monitors PreToolUse hooks across `teammate-1-frontend`, `teammate-2-pricing`, and `teammate-3-checkout`. Freezes cross-boundary edits and automatically opens a Ship Court case (`CASE-AG-101`) in Switch and Discord.
2. **Ring 2 — ChatGPT Third Voice & Boardroom OS (`server/floor_controller.py`):** Deterministic `FloorRequestProtocol` state machine (`listening -> waiting -> granted -> speaking -> yielding`) with `✋/🔎/💡/⚠️` hand-raise embeds in Discord `#meeting-floor`, 90s TTL expiry, and idempotent human floor grants.
3. **Ring 3 — 3-AI Adversarial Courtroom (`server/case_manager.py`, `server/live_courtroom_debate.py`):** Prosecutor, Defender, and Judge cross-examine PR diffs against `data/incidents.json` and `data/runbooks.json`.
4. **Ring 4 — Parallel Earth Blast-Radius Simulator (`server/parallel_earth.py`, `server/dependency_graph.py`):** Computes downstream Tier-1 service closure, $/min financial exposure, synthetic canary pass rate, and 1.8s rollback recovery before human verdict.
5. **Ring 5 — Autonomous GitHub Operations Agent (`server/github_ops_agent.py`):** Strictly gated by `SwitchRoom.enforce_human_verdict_gate` (`auto_approve: false`). Posts the full Courtroom & Parallel Earth review onto GitHub PRs, applies governance labels (`ship-court:conditional`, `antigravity:scope-checked`, `parallel-earth:verified`), opens condition Issues, and arms `rollback/<case_id>` branches.

## 2. Quickstart & Verification
Run the unified pipeline and test suite from the repository root:
```bash
pytest -v tests/test_unified_superpowers.py
```
