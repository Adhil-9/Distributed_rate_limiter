"""
Rate Limiting Algorithms Implementation.
Includes Token Bucket (Primary algorithm), Leaky Bucket, Fixed Window, and Sliding Window Log.
"""

import time
import math
from typing import Tuple, List, Dict


class TokenBucket:
    """
    Token Bucket Algorithm
    - Tokens are added to the bucket at a constant refill_rate (tokens/sec).
    - Capacity defines the maximum burst allowance.
    - Each allowed request consumes 1 token.
    """

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(capacity)
        self.last_update = time.time()

    def _refill(self, now: float = None) -> None:
        if now is None:
            now = time.time()
        elapsed = now - self.last_update
        if elapsed > 0:
            added_tokens = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + added_tokens)
            self.last_update = now

    def allow_request(self, tokens_requested: float = 1.0, now: float = None) -> Tuple[bool, float, float]:
        """
        Returns:
            (allowed: bool, remaining_tokens: float, reset_in_seconds: float)
        """
        if now is None:
            now = time.time()
        self._refill(now)

        if self.tokens >= tokens_requested:
            self.tokens -= tokens_requested
            remaining = self.tokens
            reset_in = 0.0 if self.tokens >= 1.0 else (1.0 - self.tokens) / self.refill_rate
            return True, remaining, max(0.0, reset_in)
        else:
            needed = tokens_requested - self.tokens
            retry_after = needed / self.refill_rate
            return False, self.tokens, retry_after

    def deduct_external(self, count: float) -> None:
        """Adjust token count based on remote cluster sync."""
        self._refill()
        self.tokens = max(0.0, self.tokens - count)


class LeakyBucket:
    """
    Leaky Bucket Algorithm
    - Requests enter a bucket queue with a fixed capacity.
    - Queue leaks at a constant leak_rate (requests/sec).
    - Smooths out traffic, preventing any burstiness.
    """

    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.water_level = 0.0
        self.last_leak = time.time()

    def _leak(self, now: float = None) -> None:
        if now is None:
            now = time.time()
        elapsed = now - self.last_leak
        if elapsed > 0:
            leaked = elapsed * self.leak_rate
            self.water_level = max(0.0, self.water_level - leaked)
            self.last_leak = now

    def allow_request(self, now: float = None) -> Tuple[bool, float, float]:
        if now is None:
            now = time.time()
        self._leak(now)

        if self.water_level + 1 <= self.capacity:
            self.water_level += 1.0
            return True, float(self.capacity - int(self.water_level)), 0.0
        else:
            excess = (self.water_level + 1) - self.capacity
            retry_after = excess / self.leak_rate
            return False, 0.0, retry_after


class FixedWindowCounter:
    """
    Fixed Window Counting Algorithm
    - Resets counter every window_seconds.
    - Vulnerable to boundary burst issues (2x limit at window edges).
    """

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self.current_window = int(time.time() // window_seconds)
        self.count = 0

    def allow_request(self, now: float = None) -> Tuple[bool, float, float]:
        if now is None:
            now = time.time()
        window = int(now // self.window_seconds)

        if window > self.current_window:
            self.current_window = window
            self.count = 0

        if self.count < self.limit:
            self.count += 1
            remaining = self.limit - self.count
            return True, float(remaining), 0.0
        else:
            reset_at = (self.current_window + 1) * self.window_seconds
            retry_after = reset_at - now
            return False, 0.0, max(0.0, retry_after)


class SlidingWindowLog:
    """
    Sliding Window Log Algorithm
    - Keeps exact timestamp logs for every request within window.
    - Highly accurate, high memory consumption.
    """

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self.timestamps: List[float] = []

    def allow_request(self, now: float = None) -> Tuple[bool, float, float]:
        if now is None:
            now = time.time()
        cutoff = now - self.window_seconds
        # Filter out old logs
        self.timestamps = [t for t in self.timestamps if t > cutoff]

        if len(self.timestamps) < self.limit:
            self.timestamps.append(now)
            remaining = self.limit - len(self.timestamps)
            return True, float(remaining), 0.0
        else:
            oldest = self.timestamps[0]
            retry_after = (oldest + self.window_seconds) - now
            return False, 0.0, max(0.0, retry_after)
