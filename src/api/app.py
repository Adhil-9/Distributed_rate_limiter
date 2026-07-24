"""
FastAPI Gateway Application.
Provides HTTP API endpoints for Rate Limiter simulation, cluster status monitoring,
fault injection, benchmarking, and interactive UI visualizer hosting.
"""

import os
import time
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.config import config, ConsistencyModel, FailureStrategy
from src.distributed.cluster import ClusterManager
from src.api.models import RequestSimPayload, OutageSimPayload, ConfigUpdatePayload

app = FastAPI(
    title="Distributed Rate Limiter & Abuse Detection API",
    description="Production-grade rate limiting gateway with eventual consistency token buckets and degraded fallback",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Cluster Manager with 3 Gateway Nodes
cluster = ClusterManager(node_count=3, cfg=config)


@app.post("/api/v1/request")
def process_request(payload: RequestSimPayload, response: Response):
    result = cluster.route_request(
        client_id=payload.client_id,
        endpoint=payload.endpoint,
        status_code=payload.status_code,
        tokens_requested=payload.tokens_requested,
        node_id=payload.node_id
    )

    # Set Rate Limit HTTP Headers
    for header_key, header_val in result["headers"].items():
        response.headers[header_key] = header_val

    if not result["allowed"]:
        return JSONResponse(
            status_code=429,
            content=result,
            headers=result["headers"]
        )

    return result


@app.post("/api/v1/sync")
def trigger_sync():
    sync_results = cluster.sync_all_nodes()
    return {"status": "SUCCESS", "node_sync_results": sync_results}


@app.post("/api/v1/sim/outage")
def toggle_outage(payload: OutageSimPayload):
    cluster.simulate_storage_outage(payload.storage_down)
    return {
        "status": "UPDATED",
        "storage_healthy": cluster.shared_store.is_healthy,
        "message": f"Storage outage set to {payload.storage_down}"
    }


@app.get("/api/v1/cluster/status")
def get_cluster_status():
    return cluster.get_cluster_status()


@app.post("/api/v1/config")
def update_config(payload: ConfigUpdatePayload):
    if payload.capacity is not None:
        config.default_capacity = payload.capacity
    if payload.refill_rate is not None:
        config.default_refill_rate = payload.refill_rate
    if payload.consistency_model is not None:
        config.consistency_model = ConsistencyModel(payload.consistency_model)
    if payload.failure_strategy is not None:
        config.failure_strategy = FailureStrategy(payload.failure_strategy)

    return {"status": "CONFIG_UPDATED", "config": config.dict()}


@app.post("/api/v1/benchmark")
def run_benchmark(total_requests: int = 200, clients: int = 5):
    start_time = time.time()
    allowed_count = 0
    throttled_count = 0
    node_distribution = {}

    for i in range(total_requests):
        client_id = f"bench-client-{i % clients}"
        res = cluster.route_request(client_id=client_id)
        if res["allowed"]:
            allowed_count += 1
        else:
            throttled_count += 1
        
        node_id = res["node_id"]
        node_distribution[node_id] = node_distribution.get(node_id, 0) + 1

    duration = time.time() - start_time
    rps = total_requests / duration if duration > 0 else 0

    return {
        "total_requests": total_requests,
        "allowed_requests": allowed_count,
        "throttled_requests": throttled_count,
        "duration_seconds": round(duration, 4),
        "requests_per_second": round(rps, 2),
        "node_distribution": node_distribution
    }


# Mount visualizer frontend if static directory exists
visualizer_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "visualizer")
if os.path.exists(visualizer_dir):
    app.mount("/static", StaticFiles(directory=visualizer_dir), name="static")

    @app.get("/")
    def serve_visualizer():
        index_path = os.path.join(visualizer_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Distributed Rate Limiter API Active. Visualizer index.html not found."}
