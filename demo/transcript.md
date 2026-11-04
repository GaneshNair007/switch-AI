# Ship Court - Example Courtroom Transcript
*Case SC-0482: Pull Request #482 (acme/shop)*

**Priya:**
> `@court-clerk open case https://github.com/acme/shop/pull/482`

**Court Clerk:**
> Case SC-0482 opened.  
> Change: dynamic checkout pricing.  
> Affected services: checkout-service, cart-service, pricing-worker.  
> CI: 42 passed, 0 failed.  
> Deployment: staging → production canary.  
> Requesting precedent from Incident Historian.

**Incident Historian:**
> Relevant precedent found: INC-017.  
> A pricing-related change on 2026-08-19 caused client/server cart-total mismatch.  
> Impact: 41 failed checkouts.  
> Required lesson: server-side pricing assertion and mismatch alert.

**Prosecutor:**
> Objection 1 — BLOCKING: Dynamic pricing may create cart-total mismatch between client and server. Evidence: INC-017.  
> Objection 2 — WARNING: No monitoring exists for pricing inconsistency. Evidence: No alert named pricing-mismatch in monitoring configuration.  
> Objection 3 — NOTE: Rollout percentage is not specified.

**Defender:**
> Objection 1: Pricing is calculated only server-side; cart totals are validated by `pricing_consistency_test.py`. Mitigation accepted.  
> Objection 2: CONCEDED. No mismatch alert currently exists.  
> Objection 3: Proposed 5% canary rollout.

**Rollback Engineer:**
> Rollback target: v2.13.2.  
> Command: `./scripts/rollback.sh checkout-service v2.13.2`.  
> Health checks: checkout error rate, cart latency, pricing consistency job.  
> Rollback owner required.

**Court Clerk:**
> Case ready for verdict. Unresolved blocking condition: pricing mismatch alert.

**Priya (Human Release Judge):**
> `@court-clerk verdict CONDITIONS add pricing-mismatch alert; canary 5%; Priya owns rollback`

**Court Clerk:**
> Verdict recorded: SHIP WITH CONDITIONS.  
> Tasks created:
> 1. Add pricing-mismatch alert — owner: DevOps
> 2. Configure 5% canary rollout — owner: Priya
> 3. Confirm rollback owner and rehearse rollback — Priya
> 
> Release Brief published.

