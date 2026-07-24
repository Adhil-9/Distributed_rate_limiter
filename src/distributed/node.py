"""
Gateway Node Implementation.
Simulates a distributed API gateway instance with local token buckets, abuse detection,
circuit breaking, and eventual consistency sync.
"""

import time
from typing import Dict, Any, Tuple
from src.config import SystemConfig, config as default_config
from src.core.algorithms import TokenBucket
from src.core.abuse_detector import AbuseDetector
from src.resilience.circuit_breaker import CircuitBreaker, CircuitState
from src.resilience.degraded_mode import DegradedModeHandler
from src.distributed.storage import DistributedStateStore
from src.distributed.sync import EventualConsistencySync


class GatewayNode:
    def __init__(
        self,
        node_id: str,
        shared_store: DistributedStateStore,
        cfg: SystemConfig = default_config
    ):
        self.node_id = node_id
        self.shared_store = shared_store
        self.cfg = cfg
        
        # Local Token Buckets per client: { client_id: TokenBucket }
        self.local_buckets: Dict[str, TokenBucket] = {}
        
        # Components
        self.abuse_detector = AbuseDetector(
            burst_threshold_per_sec=int(cfg.default_refill_rate * cfg.burst_threshold_multiplier),
            penalty_seconds=cfg.abuse_penalty_duration_s
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cfg.circuit_breaker_failure_threshold,
            recovery_time_s=cfg.circuit_breaker_recovery_time_s
        )
        self.degraded_handler = DegradedModeHandler(
            strategy=cfg.failure_strategy,
            degraded_factor=cfg.degraded_local_factor
        )
        self.sync_engine = EventualConsistencySync(
            store=shared_store,
            circuit_breaker=self.circuit_breaker
        )

    def _get_local_bucket(self, client_id: str, capacity: float, refill_rate: float) -> TokenBucket:
        if client_id not in self.local_buckets:
            self.local_buckets[client_id] = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        return self.local_buckets[client_id]

    def process_request(
        self,
        client_id: str,
        endpoint: str = "/api/v1/resource",
        status_code: int = 200,
        tokens_requested: float = 1.0,
        now: float = None
    ) -> Dict[str, Any]:
        if now is None:
            now = time.time()

        # Step 1: Abuse & Anomaly Detection
        is_abusive, tier, reason = self.abuse_detector.check_abuse(
            client_id=client_id,
            path=endpoint,
            status_code=status_code,
            now=now
        )

        if is_abusive and tier == "BLOCKED":
            return {
                "allowed": False,
                "status_code": 429,
                "reason": f"ABUSE_DETECTED: {reason}",
                "tier": tier,
                "execution_mode": "ABUSE_BLOCKED",
                "node_id": self.node_id,
                "headers": {
                    "X-RateLimit-Limit": "0",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60",
                    "Retry-After": "60",
                    "X-Abuse-Tier": tier
                }
            }

        # Adjust capacity & refill according to tier
        cap, refill = self.abuse_detector.get_tier_limits(
            tier=tier,
            base_capacity=self.cfg.default_capacity,
            base_refill=self.cfg.default_refill_rate
        )

        bucket = self._get_local_bucket(client_id, capacity=cap, refill_rate=refill)

        # Step 2: Circuit Breaker & Execution Mode Selection
        cb_allowed = self.circuit_breaker.allows_execution()
        execution_mode = "DISTRIBUTED_EVENTUAL" if cb_allowed else f"DEGRADED_{self.cfg.failure_strategy.value}"

        if cb_allowed:
            # Normal Flow: Evaluate local bucket with eventual consistency sync
            allowed, remaining, retry_after = bucket.allow_request(tokens_requested, now=now)
            if allowed:
                self.sync_engine.record_local_consumption(client_id, tokens_requested)
            
            status = 200 if allowed else 429
            return {
                "allowed": allowed,
                "status_code": status,
                "reason": "OK" if allowed else "RATE_LIMIT_EXCEEDED",
                "tier": tier,
                "execution_mode": execution_mode,
                "node_id": self.node_id,
                "headers": {
                    "X-RateLimit-Limit": str(int(bucket.capacity)),
                    "X-RateLimit-Remaining": str(int(max(0, remaining))),
                    "X-RateLimit-Reset": f"{retry_after:.2f}",
                    "Retry-After": f"{retry_after:.2f}" if not allowed else "0",
                    "X-Abuse-Tier": tier
                }
            }
        else:
            # Circuit Breaker OPEN -> Trigger Degraded Mode Fallback
            allowed, remaining, retry_after, fallback_mode = self.degraded_handler.handle_fallback(
                local_bucket=bucket,
                tokens_requested=tokens_requested
            )
            status = 200 if allowed else 429
            return {
                "allowed": allowed,
                "status_code": status,
                "reason": f"DEGRADED_FALLBACK ({fallback_mode})",
                "tier": tier,
                "execution_mode": f"FALLBACK_{fallback_mode}",
                "node_id": self.node_id,
                "headers": {
                    "X-RateLimit-Limit": str(int(bucket.capacity * self.cfg.degraded_local_factor)),
                    "X-RateLimit-Remaining": str(int(max(0, remaining))),
                    "X-RateLimit-Reset": f"{retry_after:.2f}",
                    "Retry-After": f"{retry_after:.2f}" if not allowed else "0",
                    "X-Abuse-Tier": tier
                }
            }

    def sync_with_cluster(self) -> bool:
        """Triggers sync flush to distributed store."""
        success, global_counts = self.sync_engine.flush()
        return success
