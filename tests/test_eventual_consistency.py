"""
Tests for eventual consistency synchronization across multi-node cluster.
"""

import pytest
from src.config import SystemConfig
from src.distributed.cluster import ClusterManager


def test_eventual_consistency_convergence():
    cfg = SystemConfig(default_capacity=20, default_refill_rate=10.0, burst_threshold_multiplier=5.0)
    cluster = ClusterManager(node_count=3, cfg=cfg)

    client_id = "test-client-sync"

    # Send 4 requests to Node 1
    for _ in range(4):
        res1 = cluster.nodes[0].process_request(client_id=client_id)
        assert res1["allowed"] is True

    # Send 4 requests to Node 2
    for _ in range(4):
        res2 = cluster.nodes[1].process_request(client_id=client_id)
        assert res2["allowed"] is True

    # Before sync, shared store has 0
    assert cluster.shared_store.get_count(client_id) == 0.0

    # Execute sync across all nodes
    cluster.sync_all_nodes()

    # After sync, shared store count should equal 8.0
    assert cluster.shared_store.get_count(client_id) == 8.0
