"""
Resilience & Fallback Handler.
Implements Fail-Open, Fail-Closed, and Degraded Local Limit strategies.
"""

from typing import Tuple
from src.config import FailureStrategy
from src.core.algorithms import TokenBucket


class DegradedModeHandler:
    def __init__(self, strategy: FailureStrategy = FailureStrategy.DEGRADED, degraded_factor: float = 0.3):
        self.strategy = strategy
        self.degraded_factor = degraded_factor

    def handle_fallback(
        self,
        local_bucket: TokenBucket,
        tokens_requested: float = 1.0
    ) -> Tuple[bool, float, float, str]:
        """
        Handles rate limit decisions when distributed store is unreachable.
        Returns:
            (allowed: bool, remaining_tokens: float, retry_after: float, mode: str)
        """
        if self.strategy == FailureStrategy.FAIL_OPEN:
            return True, local_bucket.tokens, 0.0, "FAIL_OPEN"

        elif self.strategy == FailureStrategy.FAIL_CLOSED:
            return False, 0.0, 60.0, "FAIL_CLOSED"

        elif self.strategy == FailureStrategy.DEGRADED:
            # Evaluate using local token bucket with conservative quota limit
            conservative_capacity = local_bucket.capacity * self.degraded_factor
            conservative_refill = local_bucket.refill_rate * self.degraded_factor

            # Create temporary degraded token bucket context
            degraded_bucket = TokenBucket(capacity=conservative_capacity, refill_rate=conservative_refill)
            degraded_bucket.tokens = min(local_bucket.tokens, conservative_capacity)

            allowed, remaining, retry_after = degraded_bucket.allow_request(tokens_requested)
            return allowed, remaining, retry_after, "DEGRADED_LOCAL"

        return False, 0.0, 1.0, "UNKNOWN_STRATEGY"
