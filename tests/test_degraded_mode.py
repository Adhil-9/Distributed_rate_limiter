"""
Tests for storage outages, circuit breaker transitions, and degraded fallback.
"""

import pytest
from src.config import SystemConfig, FailureStrategy
from src.distributed.cluster import ClusterManager
from src.resilience.circuit_breaker import CircuitState


def test_circuit_breaker_tripping_on_storage_failure():
    cfg = SystemConfig(
        failure_strategy=FailureStrategy.DEGRADED,
        circuit_breaker_failure_threshold=2
    )
    cluster = ClusterManager(node_count=1, cfg=cfg)
    node = cluster.nodes[0]

    # Process request to populate pending_deltas
    node.process_request(client_id="client-cb-test")

    # Trigger storage outage
    cluster.simulate_storage_outage(outage=True)

    # Initial state is CLOSED
    assert node.circuit_breaker.state == CircuitState.CLOSED

    # Trigger sync attempts -> failure recorded
    node.sync_with_cluster()
    node.sync_with_cluster()

    # Circuit breaker should now be OPEN
    assert node.circuit_breaker.state == CircuitState.OPEN

    # Next request should proceed in DEGRADED fallback mode
    res = node.process_request(client_id="client-degraded-test")
    assert "DEGRADED" in res["execution_mode"]
