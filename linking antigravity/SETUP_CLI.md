# Antigravity CLI (`agy`) Setup Guide

This guide details how to integrate and enforce the **Antigravity Agent Scope Guard** when running the terminal-based **Antigravity CLI** (`agy`).

---

## 1. How Antigravity CLI Discovers Customizations

The Antigravity CLI discovers customizations identically to the IDE by walking up from the current working directory to the repository root:

1. **Workspace Lifecycle Hooks (`.agents/hooks.json`)**:
   - `agy` loads `.agents/hooks.json` at startup.
   - When the CLI agent loop plans to execute a tool (`write_file`, `edit_file`, `run_command`), it pauses and executes the `PreToolUse` hook command via standard input/output.
   - If the hook returns `"decision": "deny"`, the CLI halts the tool, records the rejection reason into the conversation transcript, and instructs the model that the action was blocked.

2. **Global Fallback Hooks (`~/.gemini/config/hooks.json`)**:
   - For machine-wide enforcement across all repositories, hooks can also be registered globally in `~/.gemini/config/hooks.json`.

---

## 2. CLI Setup Instructions

### Step 1: Initialize Project Hooks & Scope
From your project workspace root:

```sh
# Make hook wrapper executable
chmod +x bin/scope-guard-hook

# Initialize active assignment
python3 -m scope_guard.cli init \
  --agent-id cli-backend-agent \
  --task-id TASK-API-202 \
  --description "Develop authentication API endpoints" \
  --allow "backend/src/auth/**" \
  --restrict "frontend/**" \
  --restrict "database/migrations/**" \
  --ownership "frontend/**:frontend-agent" \
  --prohibit "delete"
```

### Step 2: Validate Hook via CLI Subcommand
You can verify the hook using the Scope Guard CLI without launching an agent:

```sh
# Test permitted action:
python3 -m scope_guard.cli check --tool edit_file --path backend/src/auth/service.py
# Output: Decision: ALLOW

# Test blocked action:
python3 -m scope_guard.cli check --tool edit_file --path frontend/src/App.jsx
# Output: Decision: BLOCK (OWNERSHIP COLLISION)
```

---

## 3. Running with `agy`

Launch the Antigravity CLI inside your workspace:

```sh
agy
```

Inside the CLI prompt, give instructions to the agent:
```
agy> Add JWT verification to backend/src/auth/service.py
# -> Permitted and applied

agy> Refactor the frontend buttons in frontend/src/App.jsx
# -> Intercepted by PreToolUse hook, hard-blocked, reason injected:
# BLOCKED: OWNERSHIP COLLISION (Owned by frontend-agent)
```

### Checking Status & Flushing Events via CLI

```sh
# Inspect active assignment and pending violation buffer:
python3 -m scope_guard.cli status

# Manually flush buffered violation events to coordinator:
python3 -m scope_guard.cli flush --coordinator http://coordinator.internal:8080
```
