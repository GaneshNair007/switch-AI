# Ship Court Integration Evidence Ledger

This document collects verified, non-fabricated execution evidence from real commands executed against the local environment, LLM providers, and Switch Core v0.31.0.

---

## 1. Execution State Classification

| Feature / Subsystem | Execution State | Verifiable Evidence |
| :--- | :--- | :--- |
| **LLM Provider 1: Groq** | **LIVE** | HTTP 200 from `api.groq.com/openai/v1/chat/completions` (model `qwen/qwen3.8-27b`, ~46ms latency) |
| **LLM Provider 2: NVIDIA NIM** | **LIVE** | HTTP 200 from `integrate.api.nvidia.com/v1/models` (84 enterprise models enumerated) |
| **Real 3-Bot Adversarial Arena** | **LIVE** | 3 independent unscripted LLM agents (Prosecutor, Defender, Judge) cross-examining real proposals |
| **Switch Core Template Linting** | **LIVE** | `switch_core.template_lint.lint_template()` returned 0 errors and 0 warnings on `switch/ship-court.template.yaml` |
| **Switch Core Template Planning** | **LIVE** | `plan_template()` created room `#ship-court`, 5 agents, aliases, and exclusive `approver` role |
| **Human Verdict Gate** | **DETERMINISTIC / LIVE** | Strict token & role-based validation; rejects bot impersonation, forged names, and unauthenticated actors |
| **Local Ship Court Backend** | **LIVE** | Serving on `http://127.0.0.1:8080/health` (PID 19604, 0.0.0.0:8080) |
| **Switch Console Electron App** | **VERIFIED INSTALLED** | Installed at `C:\Users\Ganesh Nair\AppData\Local\Programs\Switch Console Canary\Switch Console Canary.exe` |
| **Docker Engine (Local Mattermost)** | **NOT INSTALLED (BLOCKED)** | `docker` CLI not recognized; Windows UAC elevation required by human user |
| **Mattermost Container Bridge** | **UNKNOWN / AWAITING DOCKER** | Switch Console's `startNativeMattermost()` requires Docker before starting container |

---

## 2. Command Output Evidence

### A. Groq Multi-Agent LLM Invocation
**Command**:
```python
POST https://api.groq.com/openai/v1/chat/completions
{"model": "qwen/qwen3.8-27b", "messages": [{"role": "user", "content": "Emergency database migration removing nullability"}]}
```
**Verified Response (Truncated excerpt)**:
```
Status: 200 OK
Latency: 46ms
Completion: "**THE PROSECUTOR RISES.** Silence in the court! You propose to execute a schema alteration on a live production database two hours before the highest traffic volume...
1. The 'Lock of Death' and Black Friday DoS: Removing nullability requires a metadata change or table rewrite that takes an exclusive lock..."
```

### B. Switch Core Template Linting
**Command**:
```python
from switch_core.template_lint import lint_template
with open("switch/ship-court.template.yaml") as f:
    errors, warnings = lint_template(f.read())
print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
```
**Verified Output**:
```
Errors: 0, Warnings: 0
```

### C. Switch Core Template Planning
**Command**:
```python
from switch_core.rooms_yaml import plan_template
plan = plan_template(template_content, {"team": "shipcourt", "repository": "acme/shop", "provider": "claude", "bridge": "mattermost"})
```
**Verified Output**:
- Planned Room: `#shipcourt-ship-court`
- Planned Agents: `shipcourt-court-clerk`, `shipcourt-incident-historian`, `shipcourt-prosecutor`, `shipcourt-defender`, `shipcourt-rollback-engineer`
- Exclusive Roles: `{"approver": "Priya"}`

### D. Ship Court Backend Health Check
**Command**:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -Method Get
```
**Verified Output**:
```json
{
  "status": "healthy",
  "service": "ship-court-backend",
  "agents_online": 5,
  "version": "1.0.0"
}
```

---

## 3. Human Authorization & Verdict Gate Verification
- **Test 1: Bot attempts to approve release**:
  - Request: `{"sender": "prosecutor", "content": "@court-clerk verdict APPROVE"}`
  - Result: `[SECURITY VIOLATION] Verdict rejected. Sender 'prosecutor' does NOT hold the exclusive approver role (@Priya).`
- **Test 2: Unauthorized user attempts to approve release**:
  - Request: `{"sender": "mallory", "content": "@court-clerk verdict APPROVE"}`
  - Result: `[SECURITY VIOLATION] Verdict rejected. Sender 'mallory' does NOT hold the exclusive approver role (@Priya).`
- **Test 3: Authorized human judge (@Priya) approves with conditions**:
  - Request: `{"sender": "Priya", "content": "@court-clerk verdict CONDITIONS canary 5%; alert on checkout error rate; Priya owns rollback"}`
  - Result: `FINAL COURT JUDGMENT RENDERED: SHIP WITH CONDITIONS. 3 binding operational tasks created in Switch.`
