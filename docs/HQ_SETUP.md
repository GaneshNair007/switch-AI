# Ship Court HQ — setup and reproducible checks

Implemented from main `c004d3f`. This machine-specific guide complements the portable setup in the repository README. It is an implementation record, not a claim that every external demonstration has passed.

## Start the workspace

From `C:\Users\arjit\Desktop\switch` in PowerShell:

```powershell
.\.runtime\venv\Scripts\python.exe -m server.main --serve --port 8080
node --env-file=.env voice/gateway.mjs
```

Keep the official Switch local server running. Run only one backend and one voice gateway. Local operational logs are in `.runtime/logs/`; credentials, SQLite, returned registration keys and channel IDs stay gitignored. The five existing custom agents use the configured Groq model and real Switch HTTP/SSE. Historian → Prosecutor → Defender → Clerk is the review chain. Third Voice is meeting-only, as requested. It does not join ordinary PR or idea review chains.

Open [HQ](http://127.0.0.1:8080). Use the **value of `SHIPCOURT_TOKEN` in the local root `.env`** in the dashboard password field, not your Groq or Discord token. The field clears when submitted. The browser receives a five-minute HttpOnly SameSite session; mutations require its CSRF token. No credential is embedded in served HTML, assets, storage or URLs. Remote deployment requires HTTPS. Use individual provisioned identities for teammates; do not distribute the owner's credential to judges.

The existing design shell is retained. Its navigation opens eight API-backed workspace views. Historical design examples remain dormant; preview JavaScript cannot authorize GitHub writes or adopt a modeled universe. Actual cases, evidence, native jobs, simulations, meetings, floor state, tasks, results and audit records come from the shared backend.

## Discord organization

```powershell
.\.runtime\venv\Scripts\python.exe -m server.discord_setup --plan
.\.runtime\venv\Scripts\python.exe -m server.discord_setup --apply --approve-guild 1568655663708770356
.\.runtime\venv\Scripts\python.exe -m server.discord_setup --validate
```

Apply requires an explicit matching guild, no conflicts, and temporary Manage Channels + Manage Roles permissions for permission overwrites. Ordinary runtime needs neither. Remove these two permissions from the bot role after setup. Keep View Channels, Send Messages, Read Message History, Attach Files, Embed Links and the existing Switch Manage Webhooks permission. Create Public Threads is needed for per-mission threads; missing thread permission is recorded as a failure, with channel delivery continuing. Voice uses its separate bot with Connect/Speak and the previously enabled intents. Message Content and Server Members Intent must stay enabled for the Switch text bridge.

The approved live setup creates seven numbered categories and 17 channels, reusing `ship-court` and the existing `boardroom` voice channel. Reused channels move under the intended category; no channels are deleted. `approvals`, `agent-traces` and `system-alerts` deny View Channel to @everyone and explicitly allow the bot and mapped operators/approvers. Unrelated permission overwrites are preserved. Conflicting unrelated View Channel grants in private channels require manual review.

IDs live in `.runtime/discord_channels.json`. `switch_rooms.ship-court` explicitly names the independently created official Switch room. Discord channel creation never creates a Switch room. Both mission types use the existing agent team/room. Additional rooms require actual Switch membership and transport configuration.

If setup permissions are unavailable, manually create:

| Category | Channels |
| --- | --- |
| 01 — COMMAND CENTER | start-here, mission-control |
| 02 — TEAM COLLABORATION | team-chat, dev-watch, agent-handoffs |
| 03 — BOARDROOM OS | Boardroom Live (voice; existing boardroom is reused), meeting-floor, meeting-recaps |
| 04 — ENGINEERING COURT | case-docket, ship-court, parallel-earth |
| 05 — DELIVERY & DECISIONS | approvals, github-results |
| 06 — PERSONAL AI STUDIO | idea-lab, my-projects |
| 07 — BACKSTAGE | agent-traces, system-alerts |

Move existing channels instead of duplicating them. Set the three private channel overwrites as above, then run `--validate` to check and save the IDs. Keep channel names unique. Discord visibility is supplemented by backend identity/role/scope checks.

Logical roles are server-side in `DISCORD_MEMBERS`, keyed by actual Discord user IDs. Workspace Owner has operator + approver roles and explicitly provisioned scopes. Human Teammate has operator access to their own missions, or `mission:ID:manage` for delegated projects. Binding decisions additionally need approver plus `mission:ID:decision`; case verdict/GitHub/floor services retain their own exact scopes. Guest/Judge uses viewer with no private record access in HQ. Bot authors and webhook personas cannot become human approvers. Runtime/harness configuration does not imply online status.

## Demo A — engineering headquarters

1. In `#mission-control`, **New Mission** (or **Open Court**) opens a real modal. Select `engineering_review`, enter a title and technical question. For repository review supply a real PR URL and affected services from the configured dependency graph. Leave PR/services empty for a question-only case; no repository/test evidence is invented.
2. The bot returns a stable mission ID and exact `!court hq:start` command. Send it as the authorized human. Switch agents delegate through actual native room messages. `#agent-handoffs` projects confirmed Switch event IDs. The mission stops at AWAITING_HUMAN.
3. Review the case/advisory in HQ or the mission thread. Run a case model with **Run case model** when affected services exist. It is modeled risk, never production telemetry.
4. Record a human direction with `!court hq:decision {"mission_id":"MISSION-ID","text":"Require bounded retries and load evidence"}`. For a reviewed PR case use `hq:verdict` with a real command, e.g. `CONDITIONS supply load evidence`; a general mission decision alone does not authorize GitHub.
5. **Review exact GitHub plan** returns the actual plan and hash. Only an authorized human may choose **Execute reviewed plan**. The existing service rechecks the head SHA, verdict, scopes, replay and plan hash. Confirmed artifacts are posted with returned URLs; failures/unknown states do not become success. No manual live GitHub writes were performed for this mission, per the user's instruction.
6. Tasks and explicit mission transitions persist. COMPLETED requires a human decision from the current work cycle and no unresolved mission tasks. Resume preserves the project history and creates a new native job; old approvals cannot silently complete the new cycle.

All commands use `!court hq:ACTION JSON`, including `create`, `start`, `resume`, `decision`, `task`, `task-update`, `meeting`, `court`, `review`, `verdict`, `research`, `simulate`, `github-plan`, `github-execute`, `transition` and `assignment`. Discord acknowledges modals/components before doing backend work. `#mission-control` updates a single saved panel, with controls for missions, meetings, agents, tasks and results.

## Demo B — personal Idea Studio

Post a real idea in `#idea-lab`. A mapped human's message creates an `idea_studio` mission and starts the same native Switch team. Unknown users/bots cannot start it. Research claims need supplied sources; creative ideas are labeled proposals, not verified facts. Use HQ **Verify sources** with explicit URLs allowed by `SHIPCOURT_RESEARCH_HOSTS`.

After the advisory, record a direction, assign a task, update it and resume later:

```text
!court hq:decision {"mission_id":"MISSION-ID","text":"Prototype a shared student task board; validate with five interviews"}
!court hq:task {"mission_id":"MISSION-ID","description":"Prepare interview questions","owner_id":"discord:YOUR-USER-ID"}
!court hq:task-update {"mission_id":"MISSION-ID","task_id":"TASK-ID","status":"DONE"}
!court hq:transition {"mission_id":"MISSION-ID","status":"COMPLETED"}
!court hq:resume {"mission_id":"MISSION-ID"}
```

Role contexts are separated by agent and mission. Prior approved project decisions are explicitly supplied on continuation. The project, task, decision and native job records survive process restart. Discord and HQ use the same records.

## Antigravity — actual editor event required

The hook contract matches the official [Antigravity hooks documentation](https://antigravity.google/docs/hooks?tab=ide): a workspace `.agents/hooks.json` can invoke a command before a tool call. **A local contract test is not proof that the IDE invoked it.**

1. Provision a scoped hook credential: `python -m server.configure --hook frontend-agent`. It saves `SHIPCOURT_HOOK_TOKEN` and a hook-only identity locally without printing it. Save `SHIPCOURT_AGENT_ID=frontend-agent` in root `.env`; restart the backend to load the identity.
2. As an authorized human, set an assignment linked to your engineering mission:

```text
!court hq:assignment {"mission_id":"MISSION-ID","agent_id":"frontend-agent","task_id":"frontend-task","task_description":"Work on frontend assets only","allowed_paths":["assets/**"],"restricted_paths":["server/**"],"ownership_info":[{"path_pattern":"server/**","owner_agent_id":"checkout-agent"}]}
```

3. In the actual Antigravity workspace hook settings, merge this entry into existing `.agents/hooks.json` (do not replace unrelated hooks):

```json
{"shipcourt-scope":{"enabled":true,"PreToolUse":[{"matcher":"write_file|edit_file|create_file|run_command","hooks":[{"type":"command","command":"\"C:/Users/arjit/Desktop/switch/.runtime/venv/Scripts/python.exe\" -m server.antigravity_hook","timeout":15}]}]}}
```

The wrapper reads only hook-related local settings and consumes actual stdin. Set the appropriate agent ID/credential in each teammate's editor environment; use separate hook identities for frontend, pricing and checkout. The human assigns their real repository paths and ownerships. Assignments determine mission links server-side; untrusted event text cannot choose a mission.

4. In Antigravity, ask the assigned frontend agent for an actual out-of-scope file edit in a disposable development workspace. Capture the real hook/tool event and its BLOCK/ASK result. Observe stored scope evidence, case link, receipt-backed Switch notification, native investigation and `#dev-watch`/`#case-docket` messages. A human approves an exact scope exception through the existing scoped approval service. Do not present a fabricated stdin payload as the live event.

Arbitrary nested shell commands and outside processes remain outside reliable static file-tool enforcement. IDE configuration and a real tool invocation are still a live verification gate on this machine.

## Boardroom — actual microphone test required

Use **Start Meeting** in Mission Control or **Link a meeting** in HQ. Join the existing boardroom voice channel and send `!voice start MISSION-ID`. The meeting attaches to the mission's existing active record. Each speaker individually sends `!voice consent`; `!voice revoke` stops their capture. No audio is stored on disk; consented audio is sent to the configured Groq transcription service.

Speak a relevant technical statement. A referenced, bounded Third Voice contribution may create a real hand request in `#meeting-floor`, showing agent, reason, priority, evidence and expiry. Controls: **Grant Floor**, **Text Instead**, **Dismiss**, **Interrupt**, **Mute Agent**, **End Meeting**. Speech requires a backend human floor grant. Human voice activity interrupts playback even without transcription consent. Ending/interruption through HQ synchronizes to the voice gateway. `!voice test` remains an explicitly requested audio check, not meeting intelligence proof.

End with `!voice stop`; one structured recap is persisted and queued to `#meeting-recaps`. It includes source-linked discussion entries, approved decisions, tasks and the mission link. Unestablished findings/ideas are left empty instead of invented. Long records are attached in full. Confirm one microphone → transcript → relevant hand → human grant → audible speech → interruption → recap sequence before claiming full voice completion. The earlier user-confirmed audible audio check alone does not establish this sequence.

## CLI and checks

```powershell
# API snapshot (privileged local output; keep it private)
.\.runtime\venv\Scripts\python.exe -m server.hq_cli snapshot
# Any action with exact JSON arguments in a local file
.\.runtime\venv\Scripts\python.exe -m server.hq_cli create --args-file .runtime/mission.json
# Local provider fixtures, HTTP, persistence, permissions and hook contracts
.\.runtime\venv\Scripts\python.exe -m pytest -q --ignore=tests/test_provider_integration.py --ignore=tests/test_live_switch_gate.py --basetemp=.runtime/pytest-hq-final
node --test voice/audio.test.mjs voice/transcription.test.mjs
```

Live provider gates are separate to avoid repeated free-tier spending. No paid harness is installed or required. A missing optional provider remains offline. Discord notification receipts, Switch handoff receipts and the audit correlation IDs are the evidence for delivery; counts/rosters alone are not.
