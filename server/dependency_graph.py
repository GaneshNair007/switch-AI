"""Dependency Graph & Blast Radius Engine for Ship Court.

Analyzes downstream microservice topologies, calculates monetary and systemic blast
radii, and produces evidentiary graphs for courtroom cross-examination.
"""
from __future__ import annotations
import math
from typing import Dict, List, Set, Any
from dataclasses import dataclass, field

@dataclass
class ServiceNode:
    name: str
    tier: int  # 1 = critical revenue path, 2 = operational support, 3 = auxiliary
    downstream: List[str] = field(default_factory=list)
    average_revenue_per_min: float = 0.0
    sla_percentage: float = 99.99

class DependencyGraph:
    """Directed graph representing architecture topology for forensic blast radius evaluation."""
    
    DEFAULT_TOPOLOGY = {
        "checkout-service": ServiceNode(
            name="checkout-service",
            tier=1,
            downstream=["payment-gateway", "pricing-engine", "tax-service", "inventory-service"],
            average_revenue_per_min=4200.0,
            sla_percentage=99.99
        ),
        "payment-gateway": ServiceNode(
            name="payment-gateway",
            tier=1,
            downstream=["stripe-adapter", "fraud-detector", "ledger-audit"],
            average_revenue_per_min=5000.0,
            sla_percentage=99.999
        ),
        "pricing-engine": ServiceNode(
            name="pricing-engine",
            tier=1,
            downstream=["redis-cache", "fx-rates-service", "promotions-rule-engine"],
            average_revenue_per_min=3500.0,
            sla_percentage=99.95
        ),
        "tax-service": ServiceNode(
            name="tax-service",
            tier=2,
            downstream=["avalara-client"],
            average_revenue_per_min=1000.0,
            sla_percentage=99.9
        ),
        "inventory-service": ServiceNode(
            name="inventory-service",
            tier=1,
            downstream=["postgres-primary", "warehouse-event-queue"],
            average_revenue_per_min=2800.0,
            sla_percentage=99.95
        ),
        "fraud-detector": ServiceNode(
            name="fraud-detector",
            tier=2,
            downstream=["risk-scoring-model"],
            average_revenue_per_min=800.0,
            sla_percentage=99.9
        )
    }

    def __init__(self, topology: Dict[str, ServiceNode] | None = None):
        self.nodes: Dict[str, ServiceNode] = dict(self.DEFAULT_TOPOLOGY) if topology is None else dict(topology)

    def register_service(self, service: ServiceNode) -> None:
        """Register or update a service node in the topology."""
        self.nodes[service.name] = service

    def get_downstream_closure(self, service_name: str) -> Set[str]:
        """Compute the transitive closure of all downstream impacted services."""
        visited: Set[str] = set()
        queue: List[str] = [service_name]

        while queue:
            current = queue.pop(0)
            if current in self.nodes:
                for dep in self.nodes[current].downstream:
                    if dep not in visited:
                        visited.add(dep)
                        queue.append(dep)
            else:
                visited.add(current)
        return visited

    def calculate_blast_radius(self, target_service: str, estimated_downtime_minutes: float = 30.0) -> Dict[str, Any]:
        """Calculate forensic blast radius including financial exposure and affected nodes."""
        if not target_service or target_service not in self.nodes:
            raise ValueError("Target service must exist in the configured topology")
        if not math.isfinite(estimated_downtime_minutes) or estimated_downtime_minutes < 0:
            raise ValueError("Downtime must be finite and non-negative")
        impacted_downstream = self.get_downstream_closure(target_service)
        all_impacted = {target_service}.union(impacted_downstream)

        tier1_count = 0
        total_rev_per_min = 0.0

        for svc in all_impacted:
            node = self.nodes.get(svc)
            if node:
                if node.tier == 1:
                    tier1_count += 1
                total_rev_per_min += node.average_revenue_per_min
            else:
                # Default unknown service assumption
                total_rev_per_min += 500.0

        monetary_exposure = total_rev_per_min * estimated_downtime_minutes
        severity_score = min(100.0, (tier1_count * 20.0) + (len(all_impacted) * 5.0) + (monetary_exposure / 10000.0))

        return {
            "root_service": target_service,
            "total_impacted_services": len(all_impacted),
            "impacted_services_list": sorted(list(all_impacted)),
            "tier1_critical_services_count": tier1_count,
            "estimated_downtime_minutes": estimated_downtime_minutes,
            "total_revenue_per_minute": total_rev_per_min,
            "projected_monetary_exposure_usd": round(monetary_exposure, 2),
            "severity_score": round(severity_score, 1),
            "requires_incident_commander": severity_score >= 60.0 or tier1_count >= 2
        }

    def render_ascii_tree(self, service_name: str, prefix: str = "", is_last: bool = True, visited: Set[str] | None = None) -> str:
        """Render ASCII dependency tree for court evidence logs."""
        if visited is None:
            visited = set()

        line = prefix + ("└── " if is_last else "├── ") + service_name + "\n"
        if service_name in visited:
            return line + prefix + ("    " if is_last else "│   ") + "(recursive link)\n"

        visited.add(service_name)
        node = self.nodes.get(service_name)
        if not node or not node.downstream:
            return line

        deps = node.downstream
        sub_prefix = prefix + ("    " if is_last else "│   ")
        for i, dep in enumerate(deps):
            dep_is_last = (i == len(deps) - 1)
            line += self.render_ascii_tree(dep, prefix=sub_prefix, is_last=dep_is_last, visited=visited.copy())
        return line

