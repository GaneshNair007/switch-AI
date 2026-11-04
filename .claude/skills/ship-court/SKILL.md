---
name: ship-court
description: Orchestrates structured adversarial release-governance cases in Switch rooms with specialized courtroom agents, evidence verification, and human release verdicts.
---

# Ship Court Execution Skill

When running or developing Ship Court cases:

## Procedural Rounds (Strict Max 4)
1. **Intake & Evidence**: Parse PR URL, changed files, CI status, affected services, and query Incident Historian for historical precedent.
2. **Prosecution**: Prosecutor raises at most 3 objections with cited evidence (classified as BLOCKING, WARNING, or NOTE).
3. **Defense**: Defender must address every objection in order or concede ("CONCEDED").
4. **Rollback Verification**: Rollback Engineer supplies concrete target version, command, health checks, and owner. Flag missing owners as BLOCKING.
5. **Human Verdict Gate**: Human Release Judge issues APPROVE, BLOCK, or CONDITIONS.
6. **Artifact Generation**: Generate Release Brief and assign Switch tasks.

## Code Constraints
- Write compact, idiomatic Python.
- Never invent missing test evidence or past incidents.
- No auto-approval under any circumstances.

