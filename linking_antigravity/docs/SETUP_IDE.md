# Antigravity IDE Setup Guide

This guide details how to integrate and verify the **Antigravity Agent Scope Guard** within the **Antigravity IDE** (or Antigravity 2.0).

---

## 1. How Antigravity IDE Integrates with Scope Guard

Antigravity IDE provides two native integration points for Scope Guard:

1. **PreToolUse Lifecycle Hook (`.agents/hooks.json`)**:
   - The IDE invokes the hook executable before executing sensitive file-modifying tools (`write_file`, `edit_file`, `create_file`, `run_command`).
   - The hook receives the pending tool arguments on `stdin` and writes its verdict (`allow`, `deny`, `ask`) to `stdout`.
   - When the verdict is `"deny"`, the IDE immediately halts tool execution, cancels the proposed diff, and displays the explainable rejection notice to the agent and developer.

2. **Hierarchical Workspace Rules (`.agents/rules/agent_scope.md`)**:
   - The IDE automatically scans `.agents/rules/` on project open and as files are navigated.
   - The Scope Guard generates a personalized rule markdown file priming the LLM with its assigned responsibility, allowed paths, and other agents' ownership reservations.

---

## 2. Workspace Installation & Setup

### Step 1: Place Scope Guard in Project Root
Ensure the `scope_guard/` package and `bin/scope-guard-hook` are placed at the root of your project workspace:

```sh
chmod +x bin/scope-guard-hook
```

### Step 2: Configure `.agents/hooks.json`
Create or update `.agents/hooks.json` in your project root:

```json
{
  "agent-scope-guard": {
    "enabled": true,
    "PreToolUse": [
      {
        "matcher": "write_file|edit_file|create_file|run_command",
        "hooks": [
          {
            "type": "command",
            "command": "sh -c 'if [ -x ./bin/scope-guard-hook ]; then ./bin/scope-guard-hook; elif [ -x ../bin/scope-guard-hook ]; then ../bin/scope-guard-hook; else python3 -m scope_guard.antigravity.hook_handler; fi'",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

### Step 3: Initialize the Agent's Assignment
Run the Scope Guard CLI to register the agent's assigned task and boundaries:

```sh
python3 -m scope_guard.cli init \
  --agent-id frontend-agent \
  --task-id TASK-AUTH-UI-101 \
  --description "Implement login and registration UI components" \
  --allow "frontend/src/auth/**" \
  --restrict "backend/**" \
  --restrict "database/**" \
  --ownership "backend/src/auth/**:backend-agent" \
  --prohibit "delete"
```

This generates:
- `.scope_guard/current_assignment.json` (local policy cache)
- `.agents/rules/agent_scope.md` (IDE rule file)

---

## 3. Verifying the IDE Guard

1. Open the project in **Antigravity IDE**.
2. Open the **Sidebar Chat** (Agent Mode).
3. Instruct the agent:
   > *"Please refactor `frontend/src/auth/Login.jsx`."*
   - **Result**: The agent proposes and executes the change smoothly (`ALLOW`).
4. Instruct the agent:
   > *"Please edit `backend/src/auth/login.py` to add database logging."*
   - **Result**: The IDE executes the hook, catches the ownership collision with `backend-agent`, and blocks the action immediately (`BLOCK`), outputting:
     ```
     BLOCKED: OWNERSHIP COLLISION
     Agent: frontend-agent
     Attempted action: Modify backend/src/auth/login.py
     Assigned responsibility: Implement login and registration UI components
     Reason: The requested file is reserved/owned by another agent ('backend-agent').
     Owner: backend-agent
     Action: Modification denied. Request cross-agent authorization or coordinator reassignment.
     ```
