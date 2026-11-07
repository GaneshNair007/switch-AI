# Native Switch + Groq agents

Ship Court runs five custom Python clients against the official Switch SSE/HTTP protocol. No Claude Code, Codex, or other paid harness is required. The registered connector type is `groq_custom`; future harness names are reserved configuration options, not working integrations or online providers.

## Roles and evidence tools

| Role | Instruction and context | Deterministic evidence access |
|---|---|---|
| Clerk | Coordinate and summarize, ask a human for a binding decision | Shared proposal and specialist results |
| Historian | Distinguish prior decisions from illustrative history | Saved human verdicts and approved meeting decisions |
| Prosecutor | Identify concrete risks and missing proof | Supplied proposal and historian findings; no invented test logs |
| Defender | Challenge objections, propose bounded mitigations | Shared evidence and prosecutor findings |
| Third Voice | Identify contradictions and propose a useful contribution | Approved meeting decisions and specialist findings; cannot grant speech |

Each agent has its own registered ID, API key, role instructions, saved context, and actual Switch connection. A shared Groq model/key is sufficient. The current `discuss` command is an advisory handoff; it does not retrieve a PR, execute tests, authorize releases, or write to GitHub. Use the existing authenticated case workflow for those operations.

## Setup on this machine

1. Run Switch Console's local server. The current instance is core 0.31.0, API `http://localhost:63239`.
2. Configure `GROQ_API_KEY` and an available `DEFAULT_GROQ_MODEL` in the gitignored root `.env`.
3. Obtain a Switch registration token. If Console offers API keys, create one there. Console 0.40.1 on this machine does not expose that screen: its generated local server environment at `%APPDATA%\switchdash\local-switch-server\native\run\switch-core.env` contains `AGENT_REGISTRATION_TOKEN`. Copy its value locally into `SWITCH_REGISTRATION_TOKEN` without printing or sharing it. Do not modify the Console-managed environment.
4. Set `SWITCH_URL` to the actual API base URL. Run `python -m server.setup_switch --register`. This registers missing agents without overwriting existing registrations, saves returned keys in `.env`, and records recovery information in gitignored `.runtime/switch-agents.json`.
5. Connect the Discord bridge to the existing test server and channel. The text bot needs Message Content Intent and Server Members Intent, plus View Channels, Send Messages, Read Message History, Attach Files and Manage Webhooks. Agent-name role autocomplete is disabled, so Manage Roles is not required. Linking the verified human identity to the agent owner lets Switch authorize messages.
6. The configured room is `Ship Court Groq Team`, connected to the existing `#ship-court` channel. `SWITCH_CLIENTS` contains five `runtime: groq_custom` entries. Each has the server-issued agent ID, key environment variable, room ID, mention and exact opaque transport sender ID. `SWITCH_PARTICIPANTS` maps the verified human's exact transport sender ID. Obtain these from actual room context/history; do not derive them from names or UUIDs.
7. To generate those entries without editing long JSON, copy `config/switch-senders.example.json` to `.runtime/senders.json`, fill in the actual observed agent/human transport sender IDs, and run `python -m server.setup_switch --configure --room-id YOUR_ROOM_ID --sender-map .runtime/senders.json`. This reuses the saved registrations and restores their existing local key variables. It does not create new agents or give an agent approval authority.
8. Restart `python -m server.main --serve --port 8080`. `/api/readiness`, with the local operator bearer, reports actual connection and receiver-thread status per agent.

## Real handoff test

From your own account in Discord `#ship-court`, type:

```text
@shipcourt-clerk !shipcourt discuss Review a proposal to retry checkout payment requests indefinitely without a timeout or idempotency key. Ask the specialists for evidence-based advice, then summarize for my decision.
```

The clerk creates a correlated `NATIVE-…` job, then delegates through native Switch messages to Historian → Prosecutor → Defender → Clerk. Third Voice is meeting-only and participates through the permission-controlled voice workflow. Each review step uses Groq and publishes its result to the shared room. The final state is `AWAITING_HUMAN`, not a release approval. Every handoff and reasoning result has the same job ID in the audit ledger. Plain-text `@shipcourt-clerk` is supported; role autocomplete is optional. HQ mission and project controls are documented in [HQ_SETUP.md](HQ_SETUP.md).

Allow time for the shared free-tier budget: concurrency is one, rolling reservations default to 6,000 tokens and six calls per minute, context is bounded to 6,000 characters, and transient provider failures have bounded exponential backoff. Rate-limit waiting can make the four-role review chain take several minutes. These limits apply to the native role runtime; account-wide usage from other applications still shares Groq's quotas.

Restart retains role context and completed outputs. SSE reconnect resumes from a saved cursor. A live connection is reported only when an actual stream is attached. Missing optional harnesses remain offline. Disconnecting Switch prevents native handoffs; there is no local-room fallback.

## What to capture

Keep the human-authored message, native handoff posts, all four review contributions, final request for a human decision, and correlated audit records. Capture Third Voice separately in its meeting workflow. Local mock tests establish contracts, not live evidence. A generated advisory alone does not prove Antigravity editor events, GitHub writes, measured deployment safety, or human authorization.
