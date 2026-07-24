"""
Multi-Node Distributed Cluster Simulation Manager.
Coordinates multiple GatewayNodes, round-robin load distribution, background synchronization,
and cluster fault injection (e.g., storage outages, network partitions).
"""

import time
import random
from typing import List, Dict, Any
from src.config import SystemConfig, config as default_config
from src.distributed.storage import DistributedStateStore
from src.distributed.node import GatewayNode


class ClusterManager:
    def __init__(self, node_count: int = 3, cfg: SystemConfig = default_config):
        self.cfg = cfg
        self.shared_store = DistributedStateStore()
        self.nodes: List[GatewayNode] = []
        
        for i in range(node_count):
            node_id = f"gateway-node-{i + 1}"
            self.nodes.append(GatewayNode(node_id=node_id, shared_store=self.shared_store, cfg=cfg))

        self.round_robin_index = 0

    def get_next_node(self) -> GatewayNode:
        node = self.nodes[self.round_robin_index % len(self.nodes)]
        self.round_robin_index += 1
        return node

    def route_request(
        self,
        client_id: str,
        endpoint: str = "/api/v1/resource",
        status_code: int = 200,
        tokens_requested: float = 1.0,
        node_id: str = None
    ) -> Dict[str, Any]:
        """Routes request to specific node or next load-balanced node."""
        if node_id:
            target_node = next((n for n in self.nodes if n.node_id == node_id), self.get_next_node())
        else:
            target_node = self.get_next_node()

        response = target_node.process_request(
            client_id=client_id,
            endpoint=endpoint,
            status_code=status_code,
            tokens_requested=tokens_requested
        )
        return response

    def sync_all_nodes(self) -> Dict[str, bool]:
        """Flushes sync deltas for all gateway nodes to shared store."""
        results = {}
        for node in self.nodes:
            results[node.node_id] = node.sync_with_cluster()
        return results

    def simulate_storage_outage(self, outage: bool) -> None:
        """Injects or heals storage failure across cluster."""
        self.shared_store.toggle_health(not outage)

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "storage_healthy": self.shared_store.is_healthy,
            "consistency_model": self.cfg.consistency_model.value,
            "failure_strategy": self.cfg.failure_strategy.value,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "circuit_breaker_state": n.circuit_breaker.state.value,
                    "consecutive_failures": n.circuit_breaker.consecutive_failures,
                    "active_buckets": len(n.local_buckets)
                }
                for n in self.nodes
            ]
        }
