# HQ implementation record — 2026-11-08

HQ was implemented on `codex/ship-court-hq`, based on main `c004d3f`, and prepared for publication to `main`. The README now retains the original visual style while documenting both workflows, real screenshots, reproducible setup and verification limits. See Git history for the publication commit.

| Area | Changed files | Result |
| --- | --- | --- |
| Authentication | `server/dashboard_auth.py`, `server/hq_http.py`, `server/dashboard_html.py`, `server/main.py` | Removed public credential injection; five-minute opaque HttpOnly sessions, CSRF/origin checks, protected APIs, scoped record reads |
| Mission domain | `server/workspace.py`, `server/unified_pipeline.py` | Both mission types, explicit states, human decisions, task ownership, research/case/model/GitHub links; linked case/meeting tasks are projected from their original records |
| Discord | `server/discord_setup.py`, `server/discord_gateway.py`, `server/notifications.py` | Approved idempotent organization, private channel reconciliation, persisted IDs, real modal/button controls, one edited panel, Idea Lab intake, mission threads, full attachments, receipt-backed outbox |
| Native collaboration | `server/switch_worker.py`, `server/switch_groq_worker.py`, `server/groq_agents.py` | Shared durable dispatcher across worker implementations, real Switch handoffs, per-mission role context, no paid runtime, blocked inference states, separate meeting-only Third Voice |
| Boardroom | `server/meetings.py`, `server/voice_bridge.py`, `voice/gateway.mjs` | Mission-linked meetings, six voice floor controls, consent, shared budget, interruption/mute/end synchronization, one persisted source-linked recap |
| Dashboard | `server/dashboard.html`, `server/hq_panel.html`, `assets/hq.js` | Existing visual shell, eight shared-data views, real model/plan/approval actions, current identity/status, no fabricated write success, narrow-screen layout |
| Setup adapters | `server/antigravity_hook.py`, `server/hq_cli.py` | Real stdin hook entry point with hook-only credential export; authenticated local CLI without printed credentials |
| Tests | `tests/test_hq_security.py`, `tests/test_hq_workspace.py`, `tests/test_hq_adapters.py`, `tests/test_discord_setup.py`, updated native/server API tests | Security, both workflows, persistence, scope links, task sources, exact GitHub approval fixtures, provision/reuse/conflicts, receipts, recap and voice controls |

## Verified

- The initial HQ check had **124 local Python tests passed** and **10 Node audio/transcription tests passed**. The README publication adds four configuration regression tests, bringing the verified local total to **128 passed**. Both changed JS files passed syntax checks, and `git diff --check` passed. There is one upstream discord.py `audioop` deprecation warning on Python 3.12. Live provider test modules are excluded from the local suite and were checked through the recorded native workflows instead. Fixtures are not external integration proof.
- Discord guild `1568655663708770356`: seven categories, 17 channels; existing text/voice channels reused. Live `--validate` passed, including private permission reconciliation. Mission Control panel `1568740012340682853` is published in channel `1568737544307216414` and edited in place. The setup guide was delivered once to start-here.
- All five Groq custom clients connected to the real local Switch server. Two explicit operator HTTP integration checks each traversed Historian → Prosecutor → Defender → Clerk over native Switch, used actual Groq inference, and reached AWAITING_HUMAN. Both created actual Discord threads. Sixteen related notification deliveries have Discord message receipts; no related pending deliveries remained at capture.
- Engineering mission `MISSION-02770b9ff16c425b82c5078468ed764a`, case `SC-05b9e1b01b5d4e5d8b7230a6030701cf`, job `NATIVE-e6f7398497ac464dba4093d13dbccba4`.
- Personal mission `MISSION-226ef7f0fecb405f92413088b66afe87`, job `NATIVE-ceb1ceaed2b34c468311e59a470627c6`.
- Both native results survived a backend restart, and all five SSE clients reconnected. The updated voice gateway reports ready. The public dashboard shell was inspected in a dedicated browser; invalid login was rejected. Authenticated cookie behavior and all protected mutation paths were exercised through local HTTP tests.
- Changed-file scanning found no configured credential matches. Credentials and machine-specific operational state remain in gitignored `.env`/`.runtime`.

Redacted external receipts and status evidence: [hq-live-2026-11-08.json](evidence/hq-live-2026-11-08.json). Setup and exact demo commands: [HQ_SETUP.md](HQ_SETUP.md).

## Remaining live gates

1. A human must exercise the new Discord modal/Idea Lab intake and record their actual binding decision. The two completed live checks used authenticated local operator HTTP intake; they are not fabricated human Discord messages. No human approval was invented.
2. Install/enable the hook in the real Antigravity workspace and capture an actual editor tool invocation. The stdin → authenticated coordinator → case/evidence → Switch investigation contract is locally tested. An actual IDE-originated event was not claimed.
3. Verify the full live voice sequence with the user's microphone: consent, accurate transcript, relevant hand, human grant, audible speech, interruption and persisted recap. Previous audible audio-check confirmation and the ready gateway do not establish that full sequence.
4. No manual real GitHub write test was performed, following the user's instruction. Exact plan/SHA/approval/result behavior is tested with controlled GitHub transports. A future authorized write requires a real target and reviewed plan.

No optional paid harness is required or reported online. Parallel Earth remains a labeled model, not measured deployment telemetry. Arbitrary background processes/nested shell effects are not comprehensively contained by a pre-tool path hook.
