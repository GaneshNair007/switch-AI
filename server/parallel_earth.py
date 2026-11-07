from __future__ import annotations
from dataclasses import dataclass, field
import math
import random
from typing import Any, Dict, List, Optional
from .bridge_connector import ChatBridgeConnector
from .dependency_graph import DependencyGraph
from .models import Case, Condition, ObjectionSeverity, RollbackPlan, RollbackStatus
from .switch_room import SwitchRoom


@dataclass
class EarthSimulationReport:
    simulation_id: str
    case_id: str
    target_services: List[str]
    impacted_downstream: List[str]
    tier1_impacted_count: int
    financial_exposure_usd: float
    synthetic_canary_pass_rate: float
    p99_latency_delta_ms: Optional[float]
    auto_rollback_verified: bool
    rollback_recovery_seconds: Optional[float]
    ascii_blast_tree: str
    recommended_conditions: List[Condition] = field(default_factory=list)
    summary: str = ""
    mode: str = "MODELED"
    assumptions: Dict[str, Any] = field(default_factory=dict)


class ParallelEarthSimulator:
    def __init__(
        self,
        room: SwitchRoom,
        graph: Optional[DependencyGraph] = None,
        bridge: Optional[ChatBridgeConnector] = None,
    ):
        self.room = room
        self.graph = graph or DependencyGraph()
        self.bridge = bridge
        self.reports: Dict[str, EarthSimulationReport] = {}
        self.room.register_session(
            agent_name="shipcourt-parallel-earth",
            alias="parallel-earth",
            location="sandbox-simulation-cluster",
            provider="claude",
        )

    def run_simulation(
        self,
        case: Case,
        estimated_downtime_minutes: float = 15.0,
        synthetic_requests: int = 1000,
        failure_probability: float = 0.01,
        seed: int = 0,
    ) -> EarthSimulationReport:
        if not case.affected_services:
            raise ValueError("At least one affected service is required")
        if not isinstance(synthetic_requests, int) or isinstance(synthetic_requests, bool) or synthetic_requests <= 0:
            raise ValueError("synthetic_requests must be a positive integer")
        if not math.isfinite(failure_probability) or not 0 <= failure_probability <= 1:
            raise ValueError("failure_probability must be finite and between 0 and 1")
        primary_service = case.affected_services[0]
        blast = self.graph.calculate_blast_radius(primary_service, estimated_downtime_minutes=estimated_downtime_minutes)
        blasts = [self.graph.calculate_blast_radius(service, estimated_downtime_minutes)
                  for service in case.affected_services]
        impacted = sorted({name for result in blasts for name in result["impacted_services_list"]})
        blast["impacted_services_list"] = impacted
        blast["tier1_critical_services_count"] = sum(
            self.graph.nodes[name].tier == 1 for name in impacted if name in self.graph.nodes)
        blast["projected_monetary_exposure_usd"] = round(sum(
            self.graph.nodes[name].average_revenue_per_min if name in self.graph.nodes else 500.0
            for name in impacted) * estimated_downtime_minutes, 2)
        ascii_tree = "\n".join(self.graph.render_ascii_tree(service) for service in case.affected_services)
        rng = random.Random(seed)
        successes = sum(rng.random() >= failure_probability for _ in range(synthetic_requests))
        canary_pass_rate = 100 * successes / synthetic_requests
        latency_delta = None
        recovery_sec = None

        conditions: List[Condition] = [
            Condition(
                id=f"COND-PE-{case.case_id}-1",
                description=f"Gate `{primary_service}` behind 5% canary traffic split for 30 minutes.",
                owner="teammate-2-pricing",
            ),
            Condition(
                id=f"COND-PE-{case.case_id}-2",
                description="Provide a rollback plan and obtain human approval before any execution.",
                owner="teammate-3-checkout",
            ),
        ]

        sim_id = f"EARTH-SIM-{len(self.reports) + 1:03d}"
        summary = (
            f"[PARALLEL EARTH MODEL {sim_id}] Modeled {synthetic_requests} independent requests "
            f"for {case.case_id}; modeled pass rate {canary_pass_rate:.2f}%. "
            f"Estimated exposure ${blast['projected_monetary_exposure_usd']:,.2f}. "
            "No staging workload or rollback executed."
        )
        report = EarthSimulationReport(
            simulation_id=sim_id,
            case_id=case.case_id,
            target_services=list(case.affected_services),
            impacted_downstream=blast["impacted_services_list"],
            tier1_impacted_count=blast["tier1_critical_services_count"],
            financial_exposure_usd=blast["projected_monetary_exposure_usd"],
            synthetic_canary_pass_rate=canary_pass_rate,
            p99_latency_delta_ms=latency_delta,
            auto_rollback_verified=False,
            rollback_recovery_seconds=recovery_sec,
            ascii_blast_tree=ascii_tree,
            recommended_conditions=conditions,
            summary=summary,
            assumptions={"seed": seed, "failure_probability": failure_probability,
                         "synthetic_requests": synthetic_requests,
                         "downtime_minutes": estimated_downtime_minutes,
                         "topology": "configured graph; bundled defaults are illustrative",
                         "unknown_service_revenue_per_minute": 500.0,
                         "exposure": "sum of node revenue rates; may double-count shared revenue",
                         "request_model": "independent Bernoulli trials; no network traffic"},
        )
        self.reports[case.case_id] = report
        self.room.post_message("parallel-earth", summary, sender_role="parallel-earth")
        if self.bridge:
            self.bridge.forward_to_chat(summary)
        return report
