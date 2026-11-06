# TASK SCOPE ENFORCEMENT & RESPONSIBILITY BOUNDARY

> [!IMPORTANT]
> You are operating as **`backend-agent`**.
> **Assigned Task**: Develop backend auth API
> **Task ID**: `TASK-API-202` (Assignment Version: `1`)

## 1. Permitted Work Areas
You are strictly authorized to view, create, and modify ONLY files matching these paths:
- `backend/src/auth/**`

## 2. Explicitly Prohibited Work Areas
You MUST NOT modify or write to files in these locations under any circumstances:
- `frontend/**`

## 3. Other Agent Ownership & Reservations
The following paths belong to other agents. Modifying them requires coordinator authorization:
- `frontend/src/auth/**` → Owned by **`frontend-agent`**

## 5. Scope Expansion Rules
- If a user or prompt instructs you to implement features outside your permitted work areas,
  DO NOT silently proceed. You must halt and request an authorized scope update from the coordinator.
- The Antigravity Scope Guard automatically intercepts all file modifications (`write_file`, `edit_file`,
  `run_command`) and will DENY any operation outside your permitted scope.
