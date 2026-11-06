# Antigravity Agent Scope Guard — Known Limitations & Unsupported Enforcement Paths

In accordance with strict safety engineering principles, this document provides an honest assessment of the boundary conditions, unsupported enforcement paths, and technical limitations of the Antigravity Agent Scope Guard.

---

## 1. File Tools vs. Arbitrary Shell Commands (`run_command`)

| Modality | Interception Reliability | Limitation Details |
| :--- | :--- | :--- |
| **Direct File Tools** (`write_file`, `edit_file`, `create_file`) | **Deterministic (100%)** | Fully deterministic. Arguments contain explicit `Path` parameters that are normalized, canonicalized, checked for path traversal, and evaluated against globs and ownership records before the tool executes. |
| **Simple Shell Commands** (`touch`, `rm`, `mv`, `cp`, file redirection `>`) | **Heuristic (High)** | Parsed via lexical analysis (`shlex`) and regex patterns. Known destructive flags and explicit target paths outside scope are caught and blocked before execution. |
| **Arbitrary / Nested Shell Scripts** (e.g., `python3 script.py`, `gcc -o ...`, `make build`) | **Unsupported Statically** | Shell commands can execute arbitrary Turing-complete binaries that mutate files via internal system calls. Static command line inspection cannot inspect runtime dynamic paths or memory allocations without runtime kernel interception. |
| **Mitigation Strategy** | OS Sandbox Confinement | Static policies decide *whether* a command runs; the Antigravity Terminal OS Sandbox (`RunCommandConfig(enable_sandbox=True)`) confines *what the command can touch on disk*. Commands requiring out-of-scope modifications should be disabled or run only in sandboxed environments. |

---

## 2. External Processes & Background Daemons

- **Detached Daemons**: If an external process or daemon (e.g. background web server, watcher, Docker daemon) was spawned in an earlier step or outside the Antigravity session, modifications performed asynchronously by that process bypass the `PreToolUse` hook.
- **PreToolUse Scope**: The hook strictly intercepts **in-turn agent tool invocations**. It is not an OS kernel filesystem driver (e.g., eBPF or FUSE).

---

## 3. Concurrent Modifications & Semantic Merge Conflicts

- **Scope vs. Semantic Conflicts**: Scope Guard enforces that an agent works within its assigned paths and respects declared ownership. It **does NOT** perform AST-level semantic merge conflict resolution or Git three-way merges.
- **Race Conditions**: If another agent concurrently modifies a shared file in the repository without leasing or updating the coordinator's ownership table, Scope Guard allows writes matching the agent's allowed paths.
- **Mitigation Strategy**: The external Coordinator and Courtroom components must maintain reservation leases and run diff comparisons before accepting changes into main branches.

---

## 4. Post-Execution vs. Pre-Execution Interception

- **`PostToolUse` and `PostInvocation`**: In Antigravity, `PostToolUse` and `PostInvocation` hooks run *after* tools execute. These are audit/notification hooks and **must never be treated as security boundaries**.
- **Scope Guard Architecture**: Scope Guard operates strictly inside `PreToolUse` (and SDK `policy.deny` / `@hooks.pre_tool_call_decide`), guaranteeing that decisions are rendered **before** the tool touches the filesystem.

---

## 5. IDE vs. CLI vs. SDK Behavioral Differences

1. **Antigravity IDE & CLI**:
   - Both utilize `.agents/hooks.json` PreToolUse hook execution over standard input/output.
   - When denied, the IDE displays the explanation in the conversational thread; the CLI writes the rejection to the transcript and continues the turn.
2. **Google Antigravity Python SDK**:
   - Uses in-process Python predicates via `policy.deny()`.
   - Predicates execute synchronously and fail closed if an unhandled exception occurs.
   - If an agent runs without `policies` configured in `LocalAgentConfig`, the SDK defaults to read-only or `confirm_run_command()` without custom Scope Guard path rules. Scope Guard must be explicitly passed to `LocalAgentConfig(policies=...)`.

---

## 6. Summary: Fail-Closed Rule

Whenever an action cannot be verified as explicitly permitted, or when internal security checks encounter corrupt data or traversal patterns, **the Scope Guard always fails closed by issuing a BLOCK decision**.
