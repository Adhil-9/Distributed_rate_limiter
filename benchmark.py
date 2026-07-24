"""
Automated Performance & Reliability Benchmark Script.
Evaluates throughput, latency percentiles (P50, P95, P99), cross-node load distribution,
and resilience under simulated storage outages.
"""

import time
import math
from typing import List, Dict
from src.config import config, SystemConfig, FailureStrategy
from src.distributed.cluster import ClusterManager


def run_performance_benchmark(num_requests: int = 1000, num_clients: int = 10):
    print("===============================================================")
    print("   DISTRIBUTED RATE LIMITER & ABUSE DETECTOR BENCHMARK          ")
    print("===============================================================")

    # Initialize Cluster
    cfg = SystemConfig(default_capacity=500, default_refill_rate=50)
    cluster = ClusterManager(node_count=3, cfg=cfg)

    print(f"Cluster Configuration:")
    print(f" - Gateway Nodes: 3")
    print(f" - Client Buckets: {num_clients}")
    print(f" - Default Capacity: {cfg.default_capacity} tokens")
    print(f" - Default Refill Rate: {cfg.default_refill_rate} tokens/sec")
    print(f" - Consistency Model: {cfg.consistency_model.value}")
    print(f" - Failure Strategy: {cfg.failure_strategy.value}")
    print("---------------------------------------------------------------")

    # Phase 1: High-Throughput Baseline Run
    print(f"\n[Phase 1] Executing {num_requests} requests (Healthy Cluster)...")
    latencies: List[float] = []
    allowed_count = 0
    throttled_count = 0

    start_total = time.time()
    for i in range(num_requests):
        client_id = f"client-bench-{i % num_clients}"
        
        t0 = time.perf_counter()
        res = cluster.route_request(client_id=client_id)
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)  # ms
        if res["allowed"]:
            allowed_count += 1
        else:
            throttled_count += 1

        if i % 100 == 0:
            cluster.sync_all_nodes()

    total_duration = time.time() - start_total
    latencies.sort()

    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    rps = num_requests / total_duration if total_duration > 0 else 0

    print(f"Phase 1 Results:")
    print(f" - Total Time: {total_duration:.4f} seconds")
    print(f" - Throughput: {rps:,.2f} req/sec")
    print(f" - Allowed: {allowed_count} | Throttled: {throttled_count}")
    print(f" - Latency P50: {p50:.4f} ms")
    print(f" - Latency P95: {p95:.4f} ms")
    print(f" - Latency P99: {p99:.4f} ms")

    # Phase 2: Fault Injection & Degraded Mode Fallback
    print(f"\n[Phase 2] Simulating Centralized Storage Outage & Failover...")
    cluster.simulate_storage_outage(outage=True)

    outage_latencies: List[float] = []
    degraded_allowed = 0
    degraded_throttled = 0

    t_outage_start = time.time()
    for i in range(200):
        client_id = f"client-outage-{i % 5}"
        
        t0 = time.perf_counter()
        # Force sync attempt to trip circuit breaker
        cluster.sync_all_nodes()
        res = cluster.route_request(client_id=client_id)
        t1 = time.perf_counter()

        outage_latencies.append((t1 - t0) * 1000.0)
        if res["allowed"]:
            degraded_allowed += 1
        else:
            degraded_throttled += 1

    outage_duration = time.time() - t_outage_start
    outage_latencies.sort()

    p50_out = outage_latencies[int(len(outage_latencies) * 0.50)]
    p95_out = outage_latencies[int(len(outage_latencies) * 0.95)]

    print(f"Phase 2 Results (Degraded Fallback Mode):")
    print(f" - Circuit Breaker State: {cluster.nodes[0].circuit_breaker.state.value}")
    print(f" - Allowed (Degraded Local Quota): {degraded_allowed}")
    print(f" - Throttled: {degraded_throttled}")
    print(f" - Fallback Latency P50: {p50_out:.4f} ms")
    print(f" - Fallback Latency P95: {p95_out:.4f} ms")

    print("\n===============================================================")
    print("   BENCHMARK COMPLETED SUCCESSFULLY                            ")
    print("===============================================================")


if __name__ == "__main__":
    run_performance_benchmark(num_requests=1000, num_clients=10)
