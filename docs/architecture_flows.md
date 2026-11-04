# Ship Court - Architecture Sequence & Event Flows

```mermaid
sequenceDiagram
    autonumber
    actor Developer as Developer / CI
    participant MM as Team Chat (#ship-court)
    participant Switch as Switch Room Engine
    participant Clerk as Court Clerk (@clerk)
    participant Historian as Incident Historian (@historian)
    participant Prosecutor as Prosecutor (@prosecutor)
    participant Defender as Defender (@defender)
    participant Rollback as Rollback Engineer (@rollback)
    actor Judge as Human Release Judge (@judge)

    Developer->>MM: @court-clerk open case https://github.com/acme/shop/pull/482
    MM->>Switch: Broadcast message
    Switch->>Clerk: on_message()
    Note over Clerk: Case SC-0482 docketed
    Clerk->>MM: Docket SC-0482 open. @historian subpoena precedent!

    Switch->>Historian: on_message()
    Note over Historian: Search incident database
    Historian->>MM: Incident INC-017 unsealed: Cart pricing divergence outage ($340k impact). @prosecutor indict!

    Switch->>Prosecutor: on_message()
    Note over Prosecutor: Formulate 3 evidence-backed objections
    Prosecutor->>MM: 1. [BLOCKING] Concurrency pricing desync<br/>2. [BLOCKING] Missing pricing-mismatch alert<br/>3. [NOTE] Unbounded canary traffic. @defender answer!

    Switch->>Defender: on_message()
    Note over Defender: Rebut or Concede
    Defender->>MM: 1. Server-side validation clamp active<br/>2. CONCEDED: Mismatch alert missing<br/>3. Traffic capped at 5% canary. @rollback verify!

    Switch->>Rollback: on_message()
    Note over Rollback: Audit recovery procedures
    Rollback->>MM: Rollback target checkout-service v2.13.2 verified. Owner: Priya. Auto-execution LOCKED.

    Clerk->>MM: Cross-examination sealed. 1 Concession, 1 Open Blocking Hazard. @judge render binding verdict!
    Judge->>MM: @court-clerk verdict CONDITIONS canary 5%; add checkout mismatch alert; Priya owns rollback
    
    Clerk->>Switch: Record Decision & Create Tasks
    Clerk->>MM: FINAL VERDICT: SHIP WITH CONDITIONS.<br/>Signed Release Brief published.
```
