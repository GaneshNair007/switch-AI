# Reproducible demo

First complete [credentials setup](CREDENTIALS.md). Local fixture tests are available without credentials. The live walkthrough requires actual services; never present fixture output as a live demonstration.

## Local verification

```powershell
.runtime\venv\Scripts\python.exe -m pytest -q
.runtime\venv\Scripts\python.exe switch/validate_template.py
node --test voice/audio.test.mjs voice/transcription.test.mjs
```

The HTTP test covers intake, advisory, scoped human verdict, exact GitHub plan approval, returned fixture artifact URLs, meetings, floor ownership, and real hook-to-loopback HTTP delivery. GitHub and model responses in this test are controlled fixtures.

## Live review, then explicitly authorized GitHub output

Start the backend, open the dashboard, and enter the local token. Use the Release workflow panel to open an actual PR with affected service `checkout-service` (the bundled topology is illustrative), review it, and inspect the advisory. Enter `CONDITIONS run a staging load test; rollback owner arjit`. Inspect the release brief and exact GitHub plan before selecting execute. Execute only on the approved test repository/PR.

Equivalent CLI calls use the same services:

```powershell
.runtime\venv\Scripts\python.exe -m server.cli /api/readiness
.runtime\venv\Scripts\python.exe -m server.cli /api/cases --json '{"pr_url":"https://github.com/OWNER/REPO/pull/NUMBER","services":["checkout-service"]}'
.runtime\venv\Scripts\python.exe -m server.cli /api/cases/review --json '{"case_id":"CASE_ID"}'
.runtime\venv\Scripts\python.exe -m server.cli /api/verdicts --json '{"case_id":"CASE_ID","command":"CONDITIONS run a staging load test"}'
.runtime\venv\Scripts\python.exe -m server.cli /api/github/plan --json '{"case_id":"CASE_ID"}'
# Only after inspecting and explicitly approving this plan:
.runtime\venv\Scripts\python.exe -m server.cli /api/github/execute --json '{"case_id":"CASE_ID","plan_hash":"RETURNED_PLAN_HASH"}'
.runtime\venv\Scripts\python.exe -m server.cli /api/audit/events
```

Replace returned IDs and hashes. Expected result is `CONFIRMED` with actual GitHub URLs. Changed/closed PRs are rejected. Failed/partial operations remain in the audit trail; do not describe them as completed.

## Native Switch proof

In the configured Switch room, address the clerk:

```text
@CLERK_HANDLE !shipcourt open {"pr_url":"https://github.com/OWNER/REPO/pull/NUMBER","services":["checkout-service"]}
```

Observe the clerk's case ID, native reviewer mention, and reviewer's advisory response. Then address the clerk with `!shipcourt verdict`, `!shipcourt github-plan`, and, after explicit approval, `!shipcourt github-execute`, each with the same JSON arguments as the CLI above. Capture real room messages and `/api/audit/events`. Disconnect Switch and demonstrate that new native handoffs stop. The local HTTP endpoint remaining usable is not a native Switch handoff.

## Discord text and meeting controls

Use `!court open`, `review`, `attach`, `verdict`, `github-plan`, and `github-execute` with the same JSON objects. Additional examples:

```text
!court meeting-start {"title":"Checkout review"}
!court consent {"meeting_id":"MEETING_ID","enabled":true}
!court transcript {"meeting_id":"MEETING_ID","event_id":"discussion-1","text":"Checkout needs a bounded retry timeout"}
!court decision {"meeting_id":"MEETING_ID","text":"Require bounded retries","evidence_refs":["discussion-1"]}
!court raise {"meeting_id":"MEETING_ID","agent_id":"reviewer","emoji":"hand","reason":"Timeout risk","spoken_script":"Verify the retry timeout under load","priority":50}
```

The last command creates real Grant Floor / Text Instead / Dismiss buttons. Grant reserves the floor; it does not claim speech has already happened. Text Instead posts the contribution and releases the floor. `!court interrupt {"request_id":"REQUEST_ID"}` interrupts a request. End with `!court meeting-end {"meeting_id":"MEETING_ID"}`.

For persistent meeting tasks use `/api/meetings/tasks` with `meeting_id`, `description`, `owner_id`, and optional approved-decision `evidence_refs`; update via `/api/meetings/tasks/update` with `meeting_id`, `task_id`, `status` (`OPEN`, `IN_PROGRESS`, `BLOCKED`, `DONE`).

## Discord voice

Join a voice channel, then in the text channel:

```text
!voice start Checkout design review
!voice consent
```

Each participant must consent individually. Speak a concrete design concern. Observe transcript and a grounded hand request if the model finds a useful contribution. Use `!voice grant REQUEST_ID`; confirm audible speech only after grant. Speak during playback to confirm interruption. `!voice revoke` stops your transcription; `!voice stop` ends the meeting and returns its structured summary. Never claim receive/TTS compatibility until tested in that actual server and call.

## Dangerous Checkout Change narrative (3–4 minutes)

1. Provision a hook assignment allowing `frontend/**`, restricting `backend/**`. Attempt a restricted edit through the actual configured editor hook. Show denial, correlated AG case and Switch notification.
2. Attach the real PR to that case through `/api/cases/attach`; review it through the native reviewer (`!shipcourt review {"case_id":"AG_CASE_ID"}`).
3. Show the evidence, labeled incident fixtures and modeled blast radius. State explicitly that modeled canary results are not measured production performance.
4. In Discord, discuss a concrete risk; show hand request, human grant and interruption. Record a human-approved meeting decision.
5. Issue the conditional verdict, inspect the exact GitHub plan, explicitly approve execution, and open the returned artifact URLs.
6. Show the common case ID in hook, Switch and GitHub records. Meeting IDs are separate; include the case ID in the meeting title/discussion so the captured narrative is identifiable.

Save screenshots/video and sanitized audit output only after a genuine live run. Publishing/submission remains a separate user action.
