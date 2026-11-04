# Demo Repository: acme/shop
This directory contains the fixture code for Pull Request #482:
- **Change:** Dynamic pricing enabled via `FEATURE_DYNAMIC_PRICING = True`.
- **Mitigation:** Server-authoritative calculation test passed in `services/checkout/tests/test_pricing.py`.
- **Vulnerability:** `config/monitoring_alerts.yaml` lacks `pricing-mismatch` alert (re-triggering past failure pattern INC-017).

