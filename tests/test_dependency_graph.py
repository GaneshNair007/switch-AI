"""Tests for DependencyGraph and Blast Radius Calculation Engine."""
import pytest
from server.dependency_graph import DependencyGraph, ServiceNode

def test_default_topology_loaded():
    graph = DependencyGraph()
    assert "checkout-service" in graph.nodes
    assert "payment-gateway" in graph.nodes
    assert len(graph.nodes) >= 6

def test_transitive_downstream_closure():
    graph = DependencyGraph()
    closure = graph.get_downstream_closure("checkout-service")
    assert "payment-gateway" in closure
    assert "stripe-adapter" in closure
    assert "fraud-detector" in closure
    assert "pricing-engine" in closure
    assert "redis-cache" in closure

def test_blast_radius_calculation():
    graph = DependencyGraph()
    radius = graph.calculate_blast_radius("checkout-service", estimated_downtime_minutes=20.0)
    assert radius["root_service"] == "checkout-service"
    assert radius["total_impacted_services"] >= 7
    assert radius["tier1_critical_services_count"] >= 3
    assert radius["projected_monetary_exposure_usd"] > 100000.0
    assert radius["severity_score"] > 60.0
    assert radius["requires_incident_commander"] is True

def test_custom_service_registration():
    graph = DependencyGraph()
    custom_node = ServiceNode(
        name="crypto-settlement-worker",
        tier=1,
        downstream=["ethereum-node", "vault-service"],
        average_revenue_per_min=10000.0
    )
    graph.register_service(custom_node)
    assert "crypto-settlement-worker" in graph.nodes
    closure = graph.get_downstream_closure("crypto-settlement-worker")
    assert "ethereum-node" in closure
    assert "vault-service" in closure

def test_render_ascii_tree():
    graph = DependencyGraph()
    tree = graph.render_ascii_tree("checkout-service")
    assert "checkout-service" in tree
    assert "payment-gateway" in tree
    assert "├──" in tree or "└──" in tree

