# CLAUDE.md - Ship Court Guidelines

## Architecture & Code Philosophy
- **Concise & Direct:** Never write 10 lines of code when 1 line does the job cleanly. Use Python standard library and modern idioms (`dataclasses`, `enum`, `typing`).
- **Deterministic & Bounded:** The courtroom workflow terminates strictly within 4 procedural rounds (evidence, objections, defense, rollback, verdict).
- **Human-in-the-Loop:** `auto_approve` is strictly false. No destructive commands or deployments run without the exclusive `approver` role.
- **Pluggable Evidence:** Scrapers support Firecrawl API, GitHub REST API, and offline reproducible mocks.

## Project Structure
- `server/`: Core backend modules (`case_manager.py`, `evidence.py`, `prosecutor_rules.py`, `defender_rules.py`, `rollback.py`, `verdict.py`, `release_brief.py`, `main.py`).
- `switch/`: Declarative Switch templates (`ship-court.template.yaml`).
- `agents/`: Switch agent definitions (`court-clerk`, `prosecutor`, `incident-historian`, `defender`, `rollback-engineer`).
- `rooms/`: Switch room definitions (`ship-court.yaml`).
- `data/`: Seeded incident history (`incidents.json`), runbooks (`runbooks.json`), and demo repository metadata.
- `demo/`: Transcript, sample PR, and release brief markdown files.
- `docs/`: System architecture, setup guide, judging alignment, and upgrade roadmap.
- `tests/`: Pytest suite verifying full state machine and rule engines.

## Commands
- Run tests: `pytest -v tests/`
- Run local server: `python server/main.py`
- Run interactive CLI demo: `python server/main.py --demo`
