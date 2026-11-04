# Ship Court Setup & Clean-Room Reproduction Guide

This guide details how to reproduce and run Ship Court locally using Switch Console, Docker, Mattermost, and Python.

## 1. Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Git
- Switch Console CLI installed

## 2. Environment Configuration
Create your `.env` file from the provided example:
```bash
cp .env.example .env
```
Populate any optional API keys (`FIRECRAWL_API_KEY`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `SWITCH_API_KEY`). If omitted, Ship Court seamlessly falls back to reproducible seeded mock data in `data/`.

## 3. Starting Mattermost Local Bridge (Docker)
```bash
docker run -d --name shipcourt-mattermost \
  -p 8065:8065 \
  mattermost/mattermost-team-edition:latest
```

## 4. Loading the Declarative Template into Switch Console
Load the parameter-driven template:
```bash
switch template apply switch/ship-court.template.yaml \
  --param team=shipcourt \
  --param repository=acme/shop \
  --param provider=claude \
  --param bridge=mattermost
```

Verify the agents and aliases:
```bash
!agents-status
!list-agents
!list-aliases
!roles
```

## 5. Running the Ship Court Backend
Install python dependencies:
```bash
pip install -r requirements.txt
```

Run unit tests:
```bash
pytest -v tests/
```

Launch the courtroom runner:
```bash
python server/main.py --demo
```

## 6. Live Interactive Chat Workflow
In `#ship-court`:
1. Developer: `@court-clerk open case https://github.com/acme/shop/pull/482`
2. Clerk orchestrates Historian, Prosecutor, Defender, and Rollback Engineer.
3. Human Judge reviews findings and issues binding verdict:
   `@court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback`
4. Clerk generates the signed Release Brief artifact and assigns tasks in Switch.

