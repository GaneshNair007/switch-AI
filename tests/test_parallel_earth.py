import pytest
from server.models import Case
from server.parallel_earth import ParallelEarthSimulator
from server.switch_room import SwitchRoom
from server.dependency_graph import DependencyGraph


def make_case():
    return Case('TEST-1', 'https://github.com/test/test/pull/1', 'test/test', ['checkout-service'], 'unknown')


def test_report_contract_and_provenance():
    case = make_case()
    report = ParallelEarthSimulator(SwitchRoom()).run_simulation(case)
    blast = DependencyGraph().calculate_blast_radius('checkout-service', 15)
    assert report.financial_exposure_usd == blast['projected_monetary_exposure_usd']
    assert report.impacted_downstream == blast['impacted_services_list']
    assert report.mode == 'MODELED'
    assert not report.auto_rollback_verified
    assert report.rollback_recovery_seconds is None
    assert report.p99_latency_delta_ms is None
    assert case.rollback_plan is None


def test_model_is_reproducible_and_sensitive_to_inputs():
    simulator = ParallelEarthSimulator(SwitchRoom())
    first = simulator.run_simulation(make_case(), seed=42)
    second = simulator.run_simulation(make_case(), seed=42)
    assert first.synthetic_canary_pass_rate == second.synthetic_canary_pass_rate
    assert simulator.run_simulation(make_case(), failure_probability=0).synthetic_canary_pass_rate == 100
    assert simulator.run_simulation(make_case(), failure_probability=1).synthetic_canary_pass_rate == 0


@pytest.mark.parametrize('minutes', [-1, float('nan'), float('inf')])
def test_invalid_downtime(minutes):
    with pytest.raises(ValueError):
        ParallelEarthSimulator(SwitchRoom()).run_simulation(make_case(), estimated_downtime_minutes=minutes)


@pytest.mark.parametrize('probability', [-1, 2, float('nan')])
def test_invalid_probability(probability):
    with pytest.raises(ValueError):
        ParallelEarthSimulator(SwitchRoom()).run_simulation(make_case(), failure_probability=probability)


def test_missing_service_rejected():
    case = make_case()
    case.affected_services = []
    with pytest.raises(ValueError):
        ParallelEarthSimulator(SwitchRoom()).run_simulation(case)
