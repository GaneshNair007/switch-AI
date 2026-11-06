# Google Antigravity Python SDK Integration Guide

This guide details how to integrate the **Antigravity Agent Scope Guard** programmatically using the official **Google Antigravity Python SDK** (`google-antigravity`).

---

## 1. SDK Integration Mechanics

The Google Antigravity Python SDK exposes two primary interception mechanisms:

1. **Declarative Tool Policies (`google.antigravity.hooks.policy`)**:
   - Evaluated before each tool execution using a prioritized resolution order (Specific Deny -> Ask -> Allow).
   - Predicates (`when=lambda args: ...`) inspect tool arguments (`Path`, `CommandLine`) and dynamically approve or reject actions.
   - If a predicate raises an exception or returns `True` for a `deny` policy, the SDK fails closed and denies execution.

2. **Programmatic Lifecycle Hooks (`@hooks.pre_tool_call_decide`)**:
   - An async callback receiving strongly-typed `types.ToolCall` instances.
   - Returns `types.HookResult(allow=False, reason="...")` to block tool execution and inject an explainable reason back to the agent model.

---

## 2. Quickstart SDK Example

```python
import asyncio
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy

from scope_guard.antigravity.sdk_integration import ScopeGuardSDKIntegration
from scope_guard.schema import Assignment, OwnershipRecord, TaskStatus

# 1. Define or load the agent's assignment
assignment = Assignment(
    agent_id="sdk-worker-1",
    task_id="TASK-API-101",
    task_description="Build Authentication Microservice",
    allowed_paths=["backend/src/auth/**"],
    restricted_paths=["frontend/**", "database/**"],
    ownership_info=[
        OwnershipRecord(
            path_pattern="frontend/**",
            owner_agent_id="frontend-agent",
            description="Frontend UI",
        )
    ],
    task_status=TaskStatus.IN_PROGRESS,
    assignment_version=1,
    prohibited_operations=["delete", "rm"],
)

# 2. Initialize Scope Guard SDK helper
sdk_guard = ScopeGuardSDKIntegration(
    assignment=assignment,
    workspace_root="./",
    on_violation=lambda decision: print(f"[VIOLATION DETECTED] {decision.reason}"),
)

async def main():
    # 3. Build SDK declarative policies
    # Generates: policy.deny("write_file", when=...), policy.deny("edit_file", when=...), etc.
    policies = sdk_guard.build_policies(policy_module=policy)

    # 4. Attach policies to LocalAgentConfig
    config = LocalAgentConfig(
        system_instructions=f"You are {assignment.agent_id}. Assigned: {assignment.task_description}",
        capabilities=CapabilitiesConfig(),  # Enables write tools
        policies=policies,                  # Enforces Scope Guard
    )

    async with Agent(config) as agent:
        # Permitted action
        print("\n--- Testing Permitted Action ---")
        resp1 = await agent.chat("Create backend/src/auth/token.py with JWT helper functions.")
        async for token in resp1:
            print(token, end="", flush=True)

        # Blocked action
        print("\n--- Testing Out-of-Scope Action ---")
        resp2 = await agent.chat("Modify frontend/src/auth/Login.jsx to change login buttons.")
        async for token in resp2:
            print(token, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Alternative: Using `@hooks.pre_tool_call_decide`

If you are using functional lifecycle hooks rather than declarative policies:

```python
from google.antigravity import types
from google.antigravity.hooks import hooks

decide_fn = sdk_guard.create_pre_tool_call_hook()

@hooks.pre_tool_call_decide
async def on_pre_tool(data: types.ToolCall) -> types.HookResult:
    return await decide_fn(data)
```
