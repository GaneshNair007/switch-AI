"""Tests for RollbackSentinel canary verification and circuit breaker automation."""
import pytest
from server.rollback_sentinel import RollbackSentinel, CanaryTelemetrySnapshot

def test_healthy_canary_evaluation():
    sentinel = RollbackSentinel(max_p99_latency_ms=250.0, max_error_rate_pct=0.5)
    healthy_snap = CanaryTelemetrySnapshot(
        case_id="SC-0482",
        canary_weight_percent=5.0,
        p99_latency_ms=112.4,
        error_rate_percent=0.02,
        pricing_drift_detected=False,
        synthetic_probe_failures=0
    )
    res = sentinel.evaluate_canary(healthy_snap)
    assert res["action"] == "HEALTHY_PROCEED"
    assert res["rollback_mandated"] is False
    assert res["violations_count"] == 0

def test_latency_spike_trips_rollback():
    sentinel = RollbackSentinel(max_p99_latency_ms=200.0)
    slow_snap = CanaryTelemetrySnapshot(
        case_id="SC-0482",
        canary_weight_percent=5.0,
        p99_latency_ms=342.1,
        error_rate_percent=0.1,
        pricing_drift_detected=False,
        synthetic_probe_failures=0
    )
    res = sentinel.evaluate_canary(slow_snap)
    assert res["action"] == "HALT_AND_ROLLBACK"
    assert res["rollback_mandated"] is True
    assert any("Latency degradation" in v for v in res["violations"])

def test_pricing_drift_trips_rollback():
    sentinel = RollbackSentinel()
    drift_snap = CanaryTelemetrySnapshot(
        case_id="SC-0482",
        canary_weight_percent=10.0,
        p99_latency_ms=120.0,
        error_rate_percent=0.01,
        pricing_drift_detected=True,
        synthetic_probe_failures=0
    )
    res = sentinel.evaluate_canary(drift_snap)
    assert res["action"] == "HALT_AND_ROLLBACK"
    assert res["rollback_mandated"] is True
    assert any("Data integrity violation" in v for v in res["violations"])

def test_sentinel_summary_aggregation():
    sentinel = RollbackSentinel()
    # 1 healthy, 2 degraded
    sentinel.evaluate_canary(CanaryTelemetrySnapshot("SC-1", 5.0, 100.0, 0.0, False, 0))
    sentinel.evaluate_canary(CanaryTelemetrySnapshot("SC-2", 5.0, 400.0, 0.0, False, 0))
    sentinel.evaluate_canary(CanaryTelemetrySnapshot("SC-3", 5.0, 100.0, 5.0, False, 0))

    summary = sentinel.get_summary()
    assert summary["total_evaluations"] == 3
    assert summary["rollback_trips"] == 2
    assert summary["healthy_evaluations"] == 1
    assert summary["sentinel_status"] == "ACTIVE_WATCH"

