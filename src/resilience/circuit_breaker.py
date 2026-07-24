"""
Circuit Breaker Pattern for Distributed Store Connection.
Manages state transitions: CLOSED -> OPEN -> HALF_OPEN.
"""

import time
from enum import Enum
from typing import Callable, Any


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal state: requests pass through to distributed store
    OPEN = "OPEN"            # Store down: bypass store and fallback to local degraded mode
    HALF_OPEN = "HALF_OPEN"  # Testing store recovery with trial request


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time_s: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_time_s = recovery_time_s
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_state_change = time.time()

    def record_success(self) -> None:
        if self.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
            self.consecutive_failures = 0
            if self.state != CircuitState.CLOSED:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def allows_execution(self) -> bool:
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery window has passed
            if now - self.last_state_change >= self.recovery_time_s:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False
