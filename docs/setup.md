# Ship Court Setup & Switch Integration Guide

This guide details how to reproduce, test, and run Ship Court with the SandboxAQ Switch platform.

## 1. Prerequisites
- Python 3.12+
- Git & GitHub CLI (`gh`)
- Switch Console (Installed at `AppData\Local\Programs\Switch Console Canary\Switch Console Canary.exe`)
- `switch-agent-controller` (Pre-configured on system PATH)

## 2. Environment Configuration
Create your `.env` file from the provided template:
```bash
cp .env.example .env
```
Populate any optional API keys (`FIRECRAWL_API_KEY`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `SWITCH_API_KEY`). If omitted, Ship Court seamlessly falls back to reproducible seeded mock data in `data/` and `demo/test_repo/`.

## 3. Switch Template Verification
Ship Court's template conforms to the official SandboxAQ Switch schema:
```bash
python switch/validate_template.py
# Verified with official switch_core.template_lint: 0 errors, 0 warnings.
```

## 4. Agent Controller Enrollment & Runner
Check the local machine readiness using the Switch sidecar controller:
```bash
switch-agent-controller doctor
```

Enroll your machine with a one-time code generated from the Switch Console **Machines** page:
```bash
switch-agent-controller enroll --server <SWITCH_SERVER_URL> --code <ENROLLMENT_CODE>
switch-agent-controller run
```

## 5. Running the Test Suite (18 Tests)
```bash
python -m pytest -v tests/
```

## 6. Running the Local Courtroom Simulation
```bash
python -m server.local_courtroom_simulation
```

## 7. Starting the HTTP API & Webhook Server
```bash
python -m server.main --serve --port 8080
```
