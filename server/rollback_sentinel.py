"""Rollback Sentinel & Canary Verification Monitor for Ship Court.

Automated watchdog that monitors active canary deployments following a conditional
courtroom release, validating SLA compliance and halting execution if metrics deteriorate.
"""
from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class CanaryTelemetrySnapshot:
    case_id: str
    canary_weight_percent: float
    p99_latency_ms: float
    error_rate_percent: float
    pricing_drift_detected: bool
    synthetic_probe_failures: int

class RollbackSentinel:
    """Evaluates real-time canary signals against the judicial release conditions."""

    def __init__(self, max_p99_latency_ms: float = 250.0, max_error_rate_pct: float = 0.5):
        self.max_p99_latency_ms = max_p99_latency_ms
        self.max_error_rate_pct = max_error_rate_pct
        self.evaluation_history: List[Dict[str, Any]] = []

    def evaluate_canary(self, snapshot: CanaryTelemetrySnapshot) -> Dict[str, Any]:
        """Assess telemetry metrics against release gates and determine whether rollback is mandatory."""
        violations: List[str] = []

        if snapshot.p99_latency_ms > self.max_p99_latency_ms:
            violations.append(
                f"Latency degradation: p99 at {snapshot.p99_latency_ms:.1f}ms exceeds threshold {self.max_p99_latency_ms:.1f}ms"
            )

        if snapshot.error_rate_percent > self.max_error_rate_pct:
            violations.append(
                f"Error budget exhausted: error rate {snapshot.error_rate_percent:.2f}% exceeds ceiling {self.max_error_rate_pct:.2f}%"
            )

        if snapshot.pricing_drift_detected:
            violations.append("Data integrity violation: client-server dynamic pricing drift observed in live traffic")

        if snapshot.synthetic_probe_failures > 0:
            violations.append(f"Synthetic probe failures: {snapshot.synthetic_probe_failures} failed transaction probes")

        rollback_required = len(violations) > 0
        action = "HALT_AND_ROLLBACK" if rollback_required else "HEALTHY_PROCEED"

        result = {
            "case_id": snapshot.case_id,
            "action": action,
            "rollback_mandated": rollback_required,
            "violations_count": len(violations),
            "violations": violations,
            "canary_weight_percent": snapshot.canary_weight_percent,
            "metrics": {
                "p99_latency_ms": snapshot.p99_latency_ms,
                "error_rate_percent": snapshot.error_rate_percent,
                "pricing_drift_detected": snapshot.pricing_drift_detected,
                "synthetic_probe_failures": snapshot.synthetic_probe_failures
            }
        }
        self.evaluation_history.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Return watchdog health summary."""
        total = len(self.evaluation_history)
        trips = sum(1 for e in self.evaluation_history if e["rollback_mandated"])
        return {
            "total_evaluations": total,
            "rollback_trips": trips,
            "healthy_evaluations": total - trips,
            "sentinel_status": "ACTIVE_WATCH"
        }

