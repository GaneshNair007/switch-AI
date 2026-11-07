# Accounts, credentials, and startup

Configure these locally after the code checks. Do not paste secrets into chat or commit `.env`. You do not need OpenAI, Anthropic, or Gemini keys for the integrated Groq workflow.

## 1. Local application identity — no account needed

In PowerShell:

```powershell
Set-Location C:\Users\arjit\Desktop\switch
.runtime\venv\Scripts\python.exe -m server.configure
```

This generates `SHIPCOURT_TOKEN` and its hashed identity in the gitignored `.env`. It refuses to replace an existing token. Use that token in the dashboard access field. The CLI loads it automatically. The initial identity is a local administrator (`operator`, `approver`, `*`); provision narrower scopes for other users.

Copy required settings individually from `.env.example` into `.env`, preserving generated identity records. Restart Python and Node processes after changing configuration.

## 2. Groq — courtroom, research, transcription, speech

Create an account at [Groq Console](https://console.groq.com/), open **API Keys**, and create a key. Save it locally as `GROQ_API_KEY`. Check available text models in the console and set `DEFAULT_GROQ_MODEL` to an exact available model ID. One key is sufficient; fallback keys are optional.

For voice, defaults are `GROQ_STT_MODEL=whisper-large-v3`, `GROQ_TTS_MODEL=canopylabs/orpheus-v1-english`, and `GROQ_TTS_VOICE=troy`. Confirm access to those models and any billing/model terms in your account before the live call. Provider availability and quotas can change.

References: [quickstart](https://console.groq.com/docs/quickstart), [speech to text](https://console.groq.com/docs/speech-to-text), [text to speech](https://console.groq.com/docs/text-to-speech).

## 3. GitHub — evidence and approved deliverables

Choose a disposable/test repository and an **open PR** where you authorize a real review comment, governance label, and follow-up issues. Public evidence can be read without a token, subject to rate limits. Writes require one.

GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Select only that repository, set an expiry, and grant **Pull requests: read/write** and **Issues: read/write**. Save as `GITHUB_TOKEN`. Organization approval may also be required. No workflow, deployment, administration, or broad repository token is needed for the implemented operations.

Create repository labels `ship-court:approved`, `ship-court:conditional`, and `ship-court:blocked`. The application expects them to exist. Supply the nonsecret test PR URL and explicitly authorize those writes when ready. A release verdict alone does not execute changes: inspect the generated plan and approve its exact hash separately.

Reference: [GitHub token setup](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## 4. Discord — text and voice

Use a test Discord server that you administer. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application, open **Bot**, obtain/reset its token, and enable **Message Content Intent**. Save the token as `DISCORD_BOT_TOKEN`. Copy the application ID to `DISCORD_APPLICATION_ID`.

Enable Developer Mode in Discord settings. Copy your server ID to `DISCORD_GUILD_ID` and copy each participating human's user ID. Provision exact IDs, for example:

```dotenv
DISCORD_MEMBERS={"YOUR_USER_ID":{"roles":["operator","approver"],"scopes":["*"]}}
```

The wildcard is convenient for your private test administrator; production members should get explicit scopes such as `meeting:MEETING_ID:floor`, `meeting:MEETING_ID:decision`, `case:CASE_ID:verdict`, and `case:CASE_ID:github`. Display names grant no permissions.

Invite the bot using the portal's installation/OAuth2 URL with the `bot` scope. Grant **View Channels, Send Messages, Read Message History, Attach Files**. Create a text channel for court commands. Voice also needs **Connect** and **Speak** in a voice channel.

A separate voice bot application is recommended. Put its token in `DISCORD_VOICE_BOT_TOKEN`, invite it to the same server with the same text and voice permissions, and enable Message Content Intent. Generate its separate backend credential:

```powershell
.runtime\venv\Scripts\python.exe -m server.configure --voice-gateway
npm.cmd ci --prefix voice --ignore-scripts
```

This adds `SHIPCOURT_VOICE_TOKEN` with only the gateway role. It cannot directly approve releases. Voice still checks the authenticated Discord participant's configured permissions.

The normal text gateway does **not** require a public web server, interaction endpoint, or public key. Optional signed HTTP interactions require `DISCORD_PUBLIC_KEY` from General Information, an HTTPS endpoint at `/discord/interactions`, and registered Discord commands; the gateway `!court` commands work without that setup. See [Discord getting started](https://docs.discord.com/developers/quick-start/getting-started).

## 5. Switch — required for the native collaboration demo

Install/start the official [Switch runtime](https://github.com/sandbox-quantum/switch) following its [documentation](https://docs.switchagents.ai/). The adapter was checked against source revision `7bf37f8f82b45865b0f0bb207857fd9c25796172` (0.31.0). Official source is available locally under `.runtime/switch-source`; this is not a running Switch instance.

Using the installed runtime's registration interface/API, register two external agent clients: clerk and reviewer. Obtain each **registered agent ID and agent API key**, a **room ID**, and the runtime's **agent HTTP/SSE base URL**. Give both agents membership in the same room. A registration/admin credential is different from an agent key; use agent keys here.

```dotenv
SWITCH_CLERK_KEY=YOUR_CLERK_AGENT_KEY
SWITCH_REVIEWER_KEY=YOUR_REVIEWER_AGENT_KEY
SWITCH_CLIENTS=[{"url":"http://127.0.0.1:PORT","agent_id":"CLERK_ID","key_env":"SWITCH_CLERK_KEY","room_id":"ROOM_ID","role":"clerk","reviewer_mention":"@REVIEWER_HANDLE"},{"url":"http://127.0.0.1:PORT","agent_id":"REVIEWER_ID","key_env":"SWITCH_REVIEWER_KEY","room_id":"ROOM_ID","role":"reviewer"}]
SWITCH_PARTICIPANTS={"EXACT_HUMAN_SENDER_ID":{"actor_type":"human","roles":["operator","approver"],"scopes":["*"]},"EXACT_CLERK_SENDER_ID":{"actor_type":"agent","roles":["operator"],"scopes":["*"]}}
```

Replace all placeholders from the running runtime. IDs must match the incoming event's sender identity; mention handles must address the registered agent. Nonhuman entries cannot receive the approver role. Remote Switch URLs require HTTPS. Run only one process for each configured client identity.

The service starts these clients automatically. The clerk receives human intake and sends the reviewer a native handoff. Disconnecting Switch prevents that handoff; local fixture tests do not substitute for this proof.

## 6. Antigravity hook — no additional paid API

```powershell
.runtime\venv\Scripts\python.exe -m server.configure --hook frontend-agent
```

This adds a scoped `SHIPCOURT_HOOK_TOKEN`. Configure the hook process with that token, `SHIPCOURT_AGENT_ID=frontend-agent`, `SHIPCOURT_COORDINATOR_URL=http://127.0.0.1:8080`, and `SHIPCOURT_WORKSPACE_ROOT` set to the actual project directory. The editor process must receive these environment variables; it does not automatically inherit Python server `.env` loading. See the [hook installation guide](../linking_antigravity/README.md). Provision the assignment through `/api/scope/assignments` before attempting edits. Missing assignments are denied.

## 7. Optional staging and research

`SHIPCOURT_STAGING_URL` must be an operator-selected, safe staging health endpoint; this performs bounded GET measurements only. It does not inject failures or roll back anything. Set `SHIPCOURT_RESEARCH_HOSTS` to comma-separated HTTPS source hostnames you trust; redirects are refused. Research uses the existing Groq key.

## Start after configuration

Terminal 1:

```powershell
Set-Location C:\Users\arjit\Desktop\switch
.runtime\venv\Scripts\python.exe -m server.main --serve --port 8080
```

Terminal 2, optional voice (Node 24.18 is already installed here):

```powershell
Set-Location C:\Users\arjit\Desktop\switch
node --env-file=.env voice/gateway.mjs
```

Open `http://127.0.0.1:8080`. Follow [DEMO.md](DEMO.md). Once configured, report only **which services are ready**, the **test PR URL**, and the **authorized write scope**. Keep tokens local. We can then verify the live workflow and capture evidence; no live success is claimed before that test.
