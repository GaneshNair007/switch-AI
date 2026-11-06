# Switch Console Canary & System Runtime Discovery

This document records the exact, source-verified baseline of the machine and the installed SandboxAQ Switch Console Canary software stack.

---

## 1. Machine Environment Baseline

| Component | Detected State | Verifiable Evidence |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 x64 (Build 26100) | `Get-CimInstance Win32_OperatingSystem` |
| **Python Environment** | Python 3.12.10 | `python --version` -> `Python 3.12.10` |
| **WSL Subsystem** | **Not Installed** | `wsl --status` returned: *"The Windows Subsystem for Linux is not installed"* |
| **Docker Engine** | **Not Installed / Missing CLI** | `Get-Command docker` returned `null`; `Test-Path "C:\Program Files\Docker\Docker\resources\bin\docker.exe"` returned `False` |
| **Docker Installer** | Present in Downloads | `C:\Users\Ganesh Nair\Downloads\DockerDesktopInstaller.exe` (623,748,528 bytes) |
| **Switch Console Binary** | Installed & Verified | `C:\Users\Ganesh Nair\AppData\Local\Programs\Switch Console Canary\Switch Console Canary.exe` |
| **Terminal Host** | Windows Console Host configured | Registry `HKCU:\Console\%%Startup` configured with `{00000000-0000-0000-0000-000000000000}` to prevent background popup windows |

---

## 2. Switch Console Canary v0.31.0 Architecture

Discovered by direct inspection of `C:\Users\Ganesh Nair\AppData\Local\Programs\Switch Console Canary\resources\local-server` and Electron bundle manifests:

### A. Bundled Components (`local-server/manifest.json`)
- **Switch Core Version**: `0.31.0`
- **PostgreSQL Version**: `16.14.0-beta.17`
- **Python Runtime**: `3.12` (isolated within `local-server/python`)
- **Package Manager**: `uv 0.13.1`
- **Platform**: `win32-x64`

### B. Control Server API (Electron Loopback Bridge)
- **Port Discovery**: Dynamic ephemeral port bound on loopback (`127.0.0.1`), written to `%APPDATA%\switchdash\control-api.json`.
- **Authentication**: Custom HTTP header `x-switch-control-token: <UUID>` generated at each launch.
- **Control API Routes**:
  - `GET /agents` — Returns list of active registered agents.
  - `GET /rooms` — Returns rooms managed by Switch.
  - `GET /machines` — Returns connected host machines.
  - `POST /rooms` — Creates a managed room.

### C. Switch Core FastAPI Endpoints (`switch_core/gateway/app.py`)
- **Rooms Router** (`/rooms`):
  - `GET /rooms` — List rooms.
  - `POST /rooms` — Provision room from template or definition.
  - `GET /rooms/{room_id}` — Room state and metadata.
  - `POST /rooms/{room_id}/messages` — Message submission.
- **Agents Router** (`/agents`):
  - `GET /agents` — List registered agents.
  - `POST /agents` — Register agent.
  - `GET /agents/{agent_id}/sessions` — Query active sessions.
- **Collaborations Router** (`/collaborations`):
  - Manages chat platform bridges (Mattermost, Slack, Discord, Teams, Telegram).
- **Template Operations** (`/templates` and `/template-runs`):
  - `template_lint.py` — Structural and schema validation.
  - `template_v2.py` / `template_runs.py` — Compilation into rooms, roles, agents, and aliases.

### D. Supported Agent Providers (`switch_core/providers/registry.py`)
The Switch Core provider registry strictly recognizes the following 5 agent providers:
1. `claude` (Claude Code CLI)
2. `codex` (Codex CLI)
3. `opencode` (OpenCode CLI)
4. `antigravity` (Antigravity CLI — `agy`)
5. `cursor` (Cursor CLI)

> **Direct Groq / NVIDIA NIM Support**: Switch Core v0.31.0 does not natively include a built-in provider ID named `groq` in its CLI registry. However, Groq and NVIDIA NIM LLM inference is integrated into Ship Court via custom HTTP agent adapters that register agent sessions over the Switch Agent Bridge or communicate via the collaboration bridge webhook.

### E. Docker Dependency Boundary
- **Core Switch Planning & Linting**: Does **NOT** require Docker. Runs directly via Python/PostgreSQL embedded engine.
- **Local Mattermost Chat Bridge**: **REQUIRES DOCKER**. The function `startNativeMattermost()` in `app.asar` directly checks `(await detectDocker()).available`. If `false`, it raises `"Mattermost needs Docker, which is not available."`
- **Ship Court Local Backend & Real LLM Arena**: Operates independently on `http://127.0.0.1:8080` without Docker, providing full multi-agent cross-examination, power scoring, and human verdict verification.
