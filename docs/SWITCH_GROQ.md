# Native Switch + Groq agents

Ship Court runs five custom Python clients against the official Switch SSE/HTTP protocol. No Claude Code, Codex, or other paid harness is required. The registered connector type is `groq_custom`; future harness names are reserved configuration options, not working integrations or online providers.

## Roles and evidence tools

| Role | Instruction and context | Deterministic evidence access |
|---|---|---|
| Clerk | Coordinate and summarize, ask a human for a binding decision | Shared proposal and specialist results |
| Historian | Distinguish prior decisions from illustrative history | Saved human verdicts and approved meeting decisions |
| Prosecutor | Identify concrete risks and missing proof | Supplied proposal and historian findings; no invented test logs |
| Defender | Challenge objections, propose bounded mitigations | Shared evidence and prosecutor findings |
| Third Voice | Meeting-only assistant, like an AI colleague on a call | Consented meeting discussion and approved decisions; hand request and human grant before speech; excluded from routine PR review |

Each agent has its own registered ID, API key, role instructions, saved context, and actual Switch connection. A shared Groq model/key is sufficient. The current `discuss` command is an advisory handoff; it does not retrieve a PR, execute tests, authorize releases, or write to GitHub. Use the existing authenticated case workflow for those operations.

## Setup on this machine

1. Run Switch Console's local server. The current instance is core 0.31.0, API `http://localhost:63239`.
2. Configure `GROQ_API_KEY` and an available `DEFAULT_GROQ_MODEL` in the gitignored root `.env`.
3. Obtain a Switch registration token. If Console offers API keys, create one there. Console 0.40.1 on this machine does not expose that screen: its generated local server environment at `%APPDATA%\switchdash\local-switch-server\native\run\switch-core.env` contains `AGENT_REGISTRATION_TOKEN`. Copy its value locally into `SWITCH_REGISTRATION_TOKEN` without printing or sharing it. Do not modify the Console-managed environment.
4. Set `SWITCH_URL` to the actual API base URL. Run `python -m server.setup_switch --register`. This registers missing agents without overwriting existing registrations, saves returned keys in `.env`, and records recovery information in gitignored `.runtime/switch-agents.json`.
5. Connect the Discord bridge to the existing test server and channel. The text bot needs Message Content Intent and Server Members Intent, plus View Channels, Send Messages, Read Message History, Attach Files and Manage Webhooks. Agent-name role autocomplete is disabled, so Manage Roles is not required. Linking the verified human identity to the agent owner lets Switch authorize messages.

   The Console's legacy bootstrap registration token can assign a different service owner from the signed-in local Admin. In that case, keep the agent addressing policy restricted: add the verified Discord **platform identity record ID** (`ExternalUser.id`, returned by the bridge identity API) to `users`, scope `rooms` to the selected room, and retain same-owner agent access for the handoff. The `users` selector does not take the Gateway user ID or the raw Discord snowflake. `server.setup_switch.addressing_policy` builds the correct rule, and the regression test checks it with Switch's actual permission evaluator. Do not clear the policy or grant everyone access. The supported 0.31.0 endpoint is `PUT /gateway/agents/{id}/addressing-policy` with `{policy: {rules: [...]}}`; configuring it requires authenticated owner/admin access. A message refused before this change must be sent again; stored historical messages are not retroactively authorized.
6. The configured room is `Ship Court Groq Team`, connected to the existing `#ship-court` channel. `SWITCH_CLIENTS` contains five `runtime: groq_custom` entries. Each has the server-issued agent ID, key environment variable, room ID, mention and exact opaque transport sender ID. `SWITCH_PARTICIPANTS` maps the verified human's exact transport sender ID. Obtain these from actual room context/history; do not derive them from names or UUIDs.
7. Restart `python -m server.main --serve --port 8080`. `/api/readiness`, with the local operator bearer, reports actual connection and receiver-thread status per agent.

## Real handoff test

From your own account in Discord `#ship-court`, type:

```text
@shipcourt-clerk !shipcourt discuss Review a proposal to retry checkout payment requests indefinitely without a timeout or idempotency key. Ask the specialists for evidence-based advice, then summarize for my decision.
```

The clerk creates a correlated `NATIVE-…` job, then delegates through native Switch messages to Historian → Prosecutor → Defender → Clerk. Third Voice participates in the separate meeting/voice workflow. Each courtroom step uses Groq and publishes its result to the shared room. The final state is `AWAITING_HUMAN`, not a release approval. Every handoff and reasoning result has the same job ID in the audit ledger. Plain-text `@shipcourt-clerk` is supported; role autocomplete is optional.

Allow time for the shared free-tier budget: concurrency is one, rolling reservations default to 6,000 tokens and six calls per minute, context is bounded to 6,000 characters, and transient provider failures have bounded exponential backoff. Rate-limit waiting can make the five-role chain take several minutes. These limits apply to the native role runtime; account-wide usage from other applications still shares Groq's quotas.

Restart retains role context and completed outputs. SSE reconnect resumes from a saved cursor. A live connection is reported only when an actual stream is attached. Missing optional harnesses remain offline. Disconnecting Switch prevents native handoffs; there is no local-room fallback.

## What to capture

Keep the human-authored message, native handoff posts, all five model-generated role contributions, final request for a human decision, and correlated audit records. Local mock tests establish contracts, not live evidence. A generated advisory alone does not prove Antigravity editor events, GitHub writes, measured deployment safety, or human authorization.

## Verified live run — 2026-11-08

Job `NATIVE-0746d5d2b427435db806cb298c642d13` completed all five Groq roles and reached `AWAITING_HUMAN`. The human input, five native handoff receipts, five reasoning events, five independently retrieved Discord outputs and final human-decision request are saved in [the evidence artifact](evidence/native-handoff-2026-11-08.json). [Open the actual final Clerk summary](https://discord.com/channels/1568655663708770356/1568657474901254254/1568697808330956912). This verified the advisory proposal handoff with Groq and local Switch 0.31.0; it did not exercise a real PR, binding verdict or external GitHub mutation.

Following that test, Third Voice was removed from routine courtroom handoffs to match its intended meeting-only role. The historical evidence remains unchanged; current-chain regression tests verify that PR discussion does not invoke Third Voice. Discord voice playback was separately confirmed audible by the user.
