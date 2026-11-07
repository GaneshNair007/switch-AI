# Engineering verification — 2026-11-07

Branch: `arjit`, based on commit `a6cc64c`. Implementation changes are local and uncommitted. No deployment, push, merge, submission, or external GitHub write was performed.

Final local check: **107 Python tests passed, 2 skipped** (missing Groq credentials), **4 Node voice tests passed**, official Switch lint **0 errors / 0 warnings**. Python 3.12 reports one upstream discord.py `audioop` deprecation warning. The skips cover live provider connectivity and live courtroom inference, not silently passing replacements.

Subsequent credential setup: **all 3 provider integration tests passed live** with the locally saved Groq credential and `openai/gpt-oss-120b`. This includes a completion and the full prosecutor/defender/advisory-judge trial. The previously configured Llama model returned 404 for this account; GPT OSS reasoning settings and token allowance were added to both Groq call paths. No external GitHub changes were made.

Discord text verification: the configured human sent `!court status {}` and received `[]` (reply `1568657568669245634`), then `!court meeting-start` created meeting `meeting-805da8e8b7b94867b482572da78b2739` (reply `1568657675347300373`). Both incoming commands have durable `COMPLETED` receipts. Replies were retrieved live from the `ship-court` channel. Interactive floor buttons and voice remain pending live tests.

## Capability matrix

| Capability | Status | Evidence / remaining gate |
|---|---|---|
| Authorization and human verdict | VERIFIED LOCAL | Forged names/objects, expired sessions, wrong scopes and bot actors rejected; conditional verdict parsing tested |
| Floor ownership | VERIFIED LOCAL | Concurrent grants, one owner per meeting, TTL, cooldown, duplicate suppression, restart interruption and meeting isolation |
| Shared workflow and persistence | VERIFIED LOCAL | Actual loopback HTTP lifecycle, SQLite restart, interrupted-review recovery |
| GitHub evidence | VERIFIED LIVE | Public PR 17 read from GaneshNair007/switch-AI; head `90b6396d7f98c4aed856e0f7336176a3858f1e59`, closed; read-only |
| GitHub comments/labels/issues | VERIFIED SIMULATED | Real REST adapter exercised with controlled transport, exact plan approval, SHA rejection and replay; actual writes await chosen open test PR and authorization |
| Official Switch template | VERIFIED LOCAL | Official 0.31.0 lint at source `7bf37f8f82b45865b0f0bb207857fd9c25796172`: zero errors/warnings |
| Native Switch connections | VERIFIED LIVE | Five Groq custom agents registered in local core 0.31.0; authenticated SSE receivers and heartbeats live; Discord bridge active in ship-court |
| Native Switch collaboration | VERIFIED LIVE | Human Discord task → Clerk → Historian → Prosecutor → Defender → Third Voice → Clerk; five real Switch handoffs and five Groq contributions independently retrieved from Discord; final state AWAITING_HUMAN. See evidence/native-handoff-2026-11-08.json |
| Scope notification to Switch | VERIFIED LOCAL | Durable notification, disconnected guard, bounded retry and retained failure; live delivery pending |
| Courtroom inference | VERIFIED LIVE | Groq completion and three-role advisory trial passed with openai/gpt-oss-120b; no binding human decision or GitHub writes in this test |
| Antigravity scope/exception | VERIFIED LOCAL | Real hook function → loopback HTTP assignment/violation/approval → next permitted exact-file action; actual IDE hook installation pending |
| Parallel Earth | VERIFIED SIMULATED | Reproducible model, corrected contracts, input validation and explicit assumptions; no production performance claim |
| Staging measurements | VERIFIED LOCAL | Metric contracts tested; operator staging endpoint required for observed workload |
| Discord text | VERIFIED LIVE | Authenticated human status and meeting-start commands produced real bot replies and durable receipts |
| Discord buttons | IMPLEMENTED BUT UNVERIFIED | Installed discord.py callbacks and signature/security tests pass locally; actual button interaction pending |
| Voice | IMPLEMENTED BUT UNVERIFIED | DAVE module loads, actual Opus encode/decode, WAV conversion and interruption gate tested; live call/STT/TTS pending |
| Meeting memory/tasks | VERIFIED LOCAL | Consent, transcripts, decision references, task ownership and structured summaries persist |
| Research | VERIFIED LOCAL | Allowlisted HTTPS sources, bounded fetch, source-reference rejection and provenance; live inference pending |
| Actual rollback/merge/deploy | NOT IMPLEMENTED | No execution endpoint; recommendations and ownership are advisory only |
| Complete live demonstration | BLOCKED BY EXTERNAL DEPENDENCY | Requires the configured services in CREDENTIALS.md and an authorized test target |

## Limits that must remain visible

- Deploy one Python process against each SQLite database. Locks and sessions are in-process; this is not a distributed/multi-worker service.
- Incident data and the default service graph are illustrative. Financial node sums can double-count shared revenue. Canary percentages are seeded modeled outcomes, not measured telemetry. Rollback success is never asserted without execution.
- External effects cannot share a database transaction with remote APIs. GitHub markers and saved Switch action results reduce retry duplication; an ambiguous remote timeout or process crash can still require operator reconciliation. Switch notifications retry at most five times and preserve failed/unknown status.
- Native Switch supports five separate registered Groq roles with independent context. The legacy clerk/reviewer adapter remains supported. Native discuss tasks are advisory; the existing authenticated case workflow handles PR evidence, binding verdicts and GitHub operations.
- Discord voice reception is an unofficial receive capability of the voice library. Live platform compatibility must be demonstrated. Consent revocation stops subsequent processing; it cannot retract audio already sent to the speech provider.
- Quiet Assistant suppresses contributions. The other named meeting modes currently share the same grounded contribution policy; distinct facilitation strategies are not implemented.
- Meeting IDs and case IDs are separate records; automatic comprehensive meeting-to-case synchronization and general task execution are not implemented. Tasks support assignment/status tracking.
- No automatic coding agent execution, rollback branch, revert PR, deployment, meeting recording archive, or published hackathon entry is claimed.
- Existing historical documents may describe earlier aspirations or sample transcripts. README.md and this matrix describe current evidence.

## Security and failure handling

Role correction after the live handoff: Third Voice is the meeting/call assistant and has been removed from automatic courtroom discussion. New review jobs follow Historian → Prosecutor → Defender → Clerk; seven focused handoff/voice tests pass. The earlier five-role evidence is retained as a historical run, not the current routing configuration.

Bindings come from provisioned bearer hashes or trusted platform identities, never supplied display names or `is_human`. Approver role and target scope are checked at the domain boundary. AI output remains advisory. Evidence text cannot invoke GitHub tools; only a separately authorized current plan hash reaches that adapter. Remote PR head/state is checked immediately before writes. Raw audio is bounded in memory, and unconsented participants are not transcribed.

Tests cover spoofing/replay, concurrency, changed targets, failure persistence, missing configuration, invalid research citations and voice cross-meeting requests. These are local evidence, not a claim of comprehensive production security review.

See [DEMO.md](DEMO.md) for commands and expected live artifacts, and [CREDENTIALS.md](CREDENTIALS.md) for every required account and key.

Voice debugging: Discord receive and transcription were observed live, including false silence transcriptions. Added energy/confidence filters, English language setting, 16kHz mono input and Whisper large v3; missing floor-ID prefixes are accepted. Groq streaming WAV data uses an unknown-length marker, now decoded correctly. A live synthetic TTS → WAV → STT roundtrip recovered timeout and idempotency terminology; **9 Node audio/transcription tests** and **2 focused Python voice/HTTP tests** pass. Human microphone accuracy and audible Discord playback still require a fresh user test after restart.

Second live microphone check: intended timeout/idempotency sentence was transcribed correctly, but punctuation, a short thanks, and vocabulary-hint copying still appeared. No hand requests or playback occurred in that session. Removed the transcription prompt; added WebRTC VAD with a pinned WASM dependency, punctuation rejection and stricter short-utterance confidence. **10 Node tests pass**, including sustained-noise rejection; live prompt-free generated speech passes VAD and transcription. This does not yet prove noise rejection or audible playback with the user microphone.
