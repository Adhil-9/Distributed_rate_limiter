"""
Distributed In-Memory Shared State Store (Simulated Redis Cluster).
Supports atomic operations, latency simulation, and network partition failure injection.
"""

import time
import random
from typing import Dict, Optional, Tuple


class DistributedStateStore:
    def __init__(self):
        # Shared key-value store: { key: count }
        self._store: Dict[str, float] = {}
        self._last_reset: Dict[str, float] = {}
        self.is_healthy: bool = True
        self.simulated_latency_ms: float = 2.0  # Default 2ms inter-datacenter latency
        self.failure_mode: bool = False

    def toggle_health(self, healthy: bool) -> None:
        self.is_healthy = healthy

    def set_failure(self, fail: bool) -> None:
        self.failure_mode = fail

    def _simulate_network(self) -> None:
        if not self.is_healthy or self.failure_mode:
            raise ConnectionError("Distributed state store is unreachable or down (Network Partition)")
        if self.simulated_latency_ms > 0:
            time.sleep(self.simulated_latency_ms / 1000.0)

    def get_count(self, key: str) -> float:
        self._simulate_network()
        return self._store.get(key, 0.0)

    def increment(self, key: str, amount: float = 1.0) -> float:
        self._simulate_network()
        current = self._store.get(key, 0.0)
        new_val = current + amount
        self._store[key] = new_val
        return new_val

    def set_key(self, key: str, value: float) -> None:
        self._simulate_network()
        self._store[key] = value

    def sync_batch(self, deltas: Dict[str, float]) -> Dict[str, float]:
        """
        Batch flushes local node counter deltas and receives current global cluster counts.
        """
        self._simulate_network()
        global_counts = {}
        for key, delta in deltas.items():
            current = self._store.get(key, 0.0)
            updated = current + delta
            self._store[key] = updated
            global_counts[key] = updated
        
        # Fill in any missing keys
        for key in list(self._store.keys()):
            if key not in global_counts:
                global_counts[key] = self._store[key]

        return global_counts

    def clear(self) -> None:
        self._store.clear()
        self._last_reset.clear()
