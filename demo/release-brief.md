# Release Brief — SC-0482
Change: Dynamic checkout pricing  
Repository: acme/shop  
PR: #482  
Requested by: Priya  
Decision: SHIP WITH CONDITIONS  

## Risk assessment
| # | Objection | Classification | Status | Evidence |
|---|---|---|---|---|
| 1 | Cart-total mismatch | WARNING | Mitigated | Server-side pricing validation test |
| 2 | No pricing mismatch alert | BLOCKING | Open | Missing monitoring rule |
| 3 | Rollout scope unclear | NOTE | Resolved | 5% canary proposed |

## Rollback plan
- **Current version:** v2.14.0
- **Rollback target:** v2.13.2
- **Command:** `./scripts/rollback.sh checkout-service v2.13.2`
- **Health checks:** checkout error rate, cart latency, pricing consistency
- **Rollback owner:** Priya
- **Execution status:** READY — requires explicit human approval

## Conditions before full rollout
- [ ] Add pricing-mismatch alert — DevOps
- [ ] Configure 5% canary rollout — Priya
- [ ] Rehearse rollback procedure — Priya

## Decision record
- **Judge:** Priya
- **Verdict:** SHIP WITH CONDITIONS
- **Switch room:** #ship-court
- **Case ID:** SC-0482
