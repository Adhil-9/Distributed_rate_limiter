"""
Eventual Consistency Asynchronous Batch Sync Engine.
Batches local count deltas and flushes them asynchronously to the distributed store.
"""

import time
from typing import Dict, Tuple
from src.distributed.storage import DistributedStateStore
from src.resilience.circuit_breaker import CircuitBreaker, CircuitState


class EventualConsistencySync:
    def __init__(self, store: DistributedStateStore, circuit_breaker: CircuitBreaker):
        self.store = store
        self.circuit_breaker = circuit_breaker
        self.pending_deltas: Dict[str, float] = {}
        self.last_sync_time = time.time()
        self.total_sync_count = 0
        self.sync_errors = 0

    def record_local_consumption(self, client_id: str, count: float = 1.0) -> None:
        self.pending_deltas[client_id] = self.pending_deltas.get(client_id, 0.0) + count

    def flush(self) -> Tuple[bool, Dict[str, float]]:
        """
        Flushes pending deltas to distributed store and fetches global counts.
        Returns:
            (success: bool, global_counts: dict)
        """
        if not self.pending_deltas:
            return True, {}

        if not self.circuit_breaker.allows_execution():
            return False, {}

        deltas_to_send = self.pending_deltas.copy()
        try:
            global_counts = self.store.sync_batch(deltas_to_send)
            # Clear flushed deltas
            for key, val in deltas_to_send.items():
                self.pending_deltas[key] -= val
                if self.pending_deltas[key] <= 0:
                    del self.pending_deltas[key]

            self.circuit_breaker.record_success()
            self.total_sync_count += 1
            self.last_sync_time = time.time()
            return True, global_counts
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.sync_errors += 1
            return False, {}
