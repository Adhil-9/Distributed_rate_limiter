# Distributed Rate Limiting & Abuse Detection Engine

![Python Version](https://img.shields.io/badge/Python-3.14%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139%2B-009688)
![Build Status](https://img.shields.io/badge/Tests-8%2F8%20Passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-purple)

A production-grade, microsecond-latency **Distributed Rate Limiter & Abuse Detection Engine** built in Python with FastAPI. The system implements an **Eventual Consistency Token Bucket Architecture**, **Circuit Breaker Resilience**, **Degraded Local Mode Fallback**, and **Pattern-Based Abuse Detection** to protect backend APIs from excessive traffic spikes, bot attacks, and path-scanning anomalies.

---

## 🌟 Executive Architectural Summary

In modern high-scale API gateways, rate limiting functions like a **traffic police system**, preventing heavy jams, server crashes, and malicious DoS attacks while keeping traffic flowing smoothly.

### Key Trade-offs & Engineering Decisions

1. **Eventual Consistency Over Strong Consistency**:
   - *Decision*: Prioritize microsecond-level request evaluation ($< 0.05\text{ ms}$) and horizontal scalability by using asynchronous delta batch syncing ($100\text{ ms}$ flush intervals).
   - *Trade-off*: Tolerates temporary sub-second request over-counting bounded by $\Delta E \le (N-1) \times R \times T_{\text{sync}}$ in exchange for $99.999\%$ gateway availability and near-zero latency impact.

2. **Token Bucket Algorithm**:
   - *Decision*: Selected Token Bucket over Leaky Bucket, Fixed Window, and Sliding Window Log.
   - *Trade-off*: Allows short, natural traffic bursts up to capacity while enforcing a strict sustained refill rate.

3. **Degraded Local Mode on Storage Failure**:
   - *Decision*: Avoids both **Fail-Closed** (which causes total API downtime) and **Fail-Open** (which risks backend server overload).
   - *Trade-off*: Automatically trips a **Circuit Breaker** on storage failure and converts global quotas into conservative local per-node limits ($30\%$ capacity).

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- `pip` package manager

### 1. Clone & Setup Project
```bash
cd /home/adhil/Downloads/distributed_rate_limiter

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the API Gateway & Interactive Visualizer
```bash
# Start FastAPI server on port 8000
python3 -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and visit:
👉 **`http://localhost:8000`** to launch the **Interactive Web Visualizer Dashboard**!

---

## 📁 Repository Structure

```
distributed_rate_limiter/
├── HLD.md                             # Comprehensive High-Level Design Document
├── README.md                          # Main Project Documentation & Setup Guide
├── requirements.txt                   # Project Dependencies (FastAPI, Pytest, Uvicorn, etc.)
├── benchmark.py                       # High-Throughput & Fault Simulation Benchmark Script
├── src/
│   ├── config.py                      # System Configuration & Rate Limiting Settings
│   ├── core/
│   │   ├── algorithms.py              # Token Bucket, Leaky Bucket, Fixed Window, Sliding Log
│   │   ├── rate_limiter.py            # Primary Rate Limiting Orchestration Engine
│   │   └── abuse_detector.py          # Velocity Spike & 404/403 Path Scan Abuse Detector
│   ├── distributed/
│   │   ├── storage.py                 # Distributed State Store (Redis Cluster Abstraction)
│   │   ├── sync.py                    # Asynchronous Eventual Consistency Batch Sync Engine
│   │   ├── node.py                    # Gateway Node Engine & HTTP Response Builder
│   │   └── cluster.py                 # Multi-Node Cluster Manager & Round-Robin Router
│   ├── resilience/
│   │   ├── circuit_breaker.py         # Circuit Breaker State Machine (CLOSED -> OPEN -> HALF_OPEN)
│   │   └── degraded_mode.py           # Degraded Local Quota & Fallback Strategy Handler
│   └── api/
│       ├── models.py                  # Pydantic Request/Response Schemas
│       └── app.py                     # FastAPI REST API Gateway Routes & Visualizer Host
├── visualizer/
│   ├── index.html                     # Sleek Dark-Mode Web Dashboard UI
│   ├── styles.css                     # Custom Modern CSS Theme & Animations
│   └── app.js                         # Dynamic UI Controls & API Communication Engine
└── tests/
    ├── test_rate_limiter.py           # Unit tests for Token Bucket & boundary logic
    ├── test_eventual_consistency.py   # Multi-node cross-sync convergence tests
    ├── test_degraded_mode.py          # Storage outage & circuit breaker tests
    └── test_abuse_detection.py        # Burst spike & path scanning abuse detector tests
```

---

## 📡 REST API Reference & Headers

### Process API Request
`POST /api/v1/request`

#### Request Payload:
```json
{
  "client_id": "client-usr-99",
  "endpoint": "/api/v1/resource",
  "status_code": 200,
  "tokens_requested": 1.0,
  "node_id": "gateway-node-1"
}
```

#### HTTP Response Headers:
- `X-RateLimit-Limit`: Maximum token bucket capacity (e.g., `100`).
- `X-RateLimit-Remaining`: Remaining available tokens (e.g., `99`).
- `X-RateLimit-Reset`: Time in seconds until bucket fully refills.
- `Retry-After`: Seconds client must wait before retrying when throttled (`429`).
- `X-Abuse-Tier`: Current client abuse classification (`STANDARD`, `RESTRICTED`, `BLOCKED`).
- `X-RateLimit-Execution-Mode`: Execution context (`DISTRIBUTED_EVENTUAL`, `FALLBACK_DEGRADED_LOCAL`).

---

## 🧪 Running Unit Tests & Benchmarks

### Execute Unit Test Suite
```bash
python3 -m pytest tests/ -v
```
Output:
```
tests/test_abuse_detection.py::test_burst_spike_detection PASSED         [ 12%]
tests/test_abuse_detection.py::test_suspicious_path_scanning PASSED      [ 25%]
tests/test_degraded_mode.py::test_circuit_breaker_tripping_on_storage_failure PASSED [ 37%]
tests/test_eventual_consistency.py::test_eventual_consistency_convergence PASSED [ 50%]
tests/test_rate_limiter.py::test_token_bucket_initial_capacity PASSED    [ 62%]
tests/test_rate_limiter.py::test_token_bucket_throttling PASSED          [ 75%]
tests/test_rate_limiter.py::test_token_bucket_refill PASSED              [ 87%]
tests/test_rate_limiter.py::test_fixed_window_boundary_behavior PASSED   [100%]
============================== 8 passed in 0.15s ===============================
```

### Execute Performance & Reliability Benchmark
```bash
python3 benchmark.py
```
Benchmark Results Summary:
- **Throughput**: `13,445+ req/sec`
- **P50 Latency**: `0.0110 ms` (11 microseconds)
- **P95 Latency**: `0.0187 ms`
- **P99 Latency**: `0.0507 ms`
- **Fault Recovery**: Seamless transition to **DEGRADED_LOCAL** fallback mode when shared storage is disconnected.

---

## 🎨 Interactive Web Visualizer

The project includes an interactive web dashboard available at `http://localhost:8000`:
- **Live Multi-Node Topology**: Inspect active gateway nodes (`gateway-node-1`, `gateway-node-2`, `gateway-node-3`) and their circuit breaker states.
- **Fault Injection Controls**: Simulate centralized storage outages with one click and observe nodes instantly transition to degraded local limits.
- **Real-Time Request Inspector**: Track incoming HTTP headers, remaining tokens, reset windows, and decision audit logs.

---

## 📜 Documentation Reference

For an in-depth exploration of system trade-offs, consistency models, sequence diagrams, and mathematical consistency bounds, refer to the [High Level Design Document (HLD.md)](file:///home/adhil/Downloads/distributed_rate_limiter/HLD.md).
