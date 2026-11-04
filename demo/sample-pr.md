# Demo Pull Request: acme/shop#482
**Title:** feat: dynamic checkout pricing with real-time tax estimation  
**Author:** Priya (@priya)  
**Target:** `staging -> production canary`  
**Affected Services:** `checkout-service`, `cart-service`, `pricing-worker`

## Changes Summary
This PR transitions checkout pricing from static cart calculations to an asynchronous pricing engine that evaluates volume discounts and jurisdictional tax rates during checkout finalization.

### Changed Files
- `services/checkout/pricing_engine.py`: Replaces client-side math with server-authoritative calculations.
- `services/checkout/tests/pricing_consistency_test.py`: Adds end-to-end pricing validation test suite.
- `services/cart/models.py`: Adjusts schema to store computed tax breakdown.
- `config/alerts.yaml`: Existing alerts retained; lacks `pricing-mismatch` alert.

### CI Status
- Tests Passed: 42 / 42
- Linter: Passed
- Code Coverage: 89.4%

