# Ship Court System Architecture

## 1. High-Level Architecture

```
+-------------------------------------------------------------------------+
|                               TEAM CHAT                                 |
|  (Mattermost / Slack / Teams / Discord)                                 |
|       Developer <---> #ship-court <---> Human Release Judge (Exclusive) |
+------------------------------------+------------------------------------+
                                     |
                             Switch Chat Bridge
                                     |
+------------------------------------v------------------------------------+
|                               SWITCH CORE                               |
|  - Room State & Protocol            - Task & Decision Auditing          |
|  - SSE In / HTTP Out Engine         - Docker & Local Agent Runtimes     |
|  - Shared Instructions & Rules      - Distributed Machine Session Bus   |
+------------------------------------+------------------------------------+
                                     |
                  +------------------+------------------+
                  |                                     |
+-----------------v-----------------+ +-----------------v-----------------+
|      ALWAYS-ON SERVER HOST        | |     DEVELOPER / OPS MACHINE       |
|  - Court Clerk                    | |  - Defender                       |
|  - Incident Historian             | |  - Rollback Engineer              |
|  - Prosecutor                     | |                                   |
+-----------------+-----------------+ +-----------------+-----------------+
                  |                                     |
                  +------------------+------------------+
                                     |
+------------------------------------v------------------------------------+
|                         EXTERNAL CONNECTORS                             |
|  - GitHub API / PR Scraper (Firecrawl web extraction)                   |
|  - Incident Memory (SQLite / Seeded JSON)                               |
|  - Rollback Runbooks & Service Health Checks                            |
+-------------------------------------------------------------------------+
```

## 2. Machine Topology
Switch distinguishes an agent identity from an active session. Ship Court takes advantage of this distributed topology:
- **Court Clerk (Always-on server):** Listens for case commands, coordinates procedural rounds, enforces bounding rules.
- **Incident Historian (Always-on server):** Retains persistent access to historical incident database (`INC-XXX`).
- **Prosecutor (Always-on / CI runner):** Validates diff, CI status, missing alerts, and formulates strict objections.
- **Defender (Developer machine / CI):** Runs close to repository code and test suites to verify technical mitigations.
- **Rollback Engineer (Ops host / Local runner):** Inspects deployment runbooks and verifies target versions and commands.
- **Release Judge (Human in Chat):** Holds exclusive `approver` authority in Switch room.

## 3. Switch Primitives
- **Rooms:** `#ship-court` provides durable conversation memory and auditable logs.
- **Addressing Scopes:** Clerk responds to `anyone`; specialist agents listen to `owner-agents`.
- **Exclusive Roles:** `approver` can only be held by verified humans.
- **Tasks & Decisions:** Switch stores structured conditions and verdicts.

