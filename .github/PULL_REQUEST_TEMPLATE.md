## Ship Court Case Review Checklist

### 1. Pre-Deployment Evidence
- [ ] PR URL cited and metadata fetched
- [ ] CI checks status confirmed
- [ ] Affected services listed

### 2. Multi-Agent Cross-Examination
- [ ] Incident Historian searched past incidents (INC-XXX)
- [ ] Prosecutor raised at most 3 evidence-backed objections
- [ ] Defender addressed each objection in order or explicitly conceded (`CONCEDED`)
- [ ] Rollback Engineer validated target version, command, health checks, and owner

### 3. Human Governance
- [ ] Human Release Judge holding exclusive `approver` role issued binding verdict (`APPROVE`, `BLOCK`, `CONDITIONS`)
- [ ] Tasks created in Switch for conditions
- [ ] Release Brief artifact signed and stored
