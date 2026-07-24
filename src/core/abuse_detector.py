"""
Pattern-based Abuse & Anomaly Detection System.
Monitors client request velocity, burst spikes, and suspicious path scanning.
"""

import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ClientMetrics:
    request_timestamps: List[float] = field(default_factory=list)
    suspicious_hits: int = 0
    is_blocked: bool = False
    block_expiry: float = 0.0
    tier: str = "STANDARD"  # STANDARD, RESTRICTED, BLOCKED


class AbuseDetector:
    def __init__(self, burst_threshold_per_sec: int = 30, penalty_seconds: float = 60.0):
        self.burst_threshold_per_sec = burst_threshold_per_sec
        self.penalty_seconds = penalty_seconds
        self.client_store: Dict[str, ClientMetrics] = {}

    def _get_metrics(self, client_id: str) -> ClientMetrics:
        if client_id not in self.client_store:
            self.client_store[client_id] = ClientMetrics()
        return self.client_store[client_id]

    def check_abuse(self, client_id: str, path: str, status_code: int = 200, now: float = None) -> Tuple[bool, str, str]:
        """
        Evaluates whether client shows abusive behavior.
        Returns:
            (is_abusive: bool, tier: str, reason: str)
        """
        if now is None:
            now = time.time()

        metrics = self._get_metrics(client_id)

        # Check existing block status
        if metrics.is_blocked:
            if now < metrics.block_expiry:
                return True, "BLOCKED", f"Client blocked until {int(metrics.block_expiry - now)}s"
            else:
                # Block expired, reset to RESTRICTED tier
                metrics.is_blocked = False
                metrics.tier = "RESTRICTED"
                metrics.suspicious_hits = 0

        # Clean old timestamps (keep last 5 seconds)
        cutoff = now - 5.0
        metrics.request_timestamps = [t for t in metrics.request_timestamps if t > cutoff]
        metrics.request_timestamps.append(now)

        # Check 1-second burst rate
        one_sec_cutoff = now - 1.0
        burst_count = sum(1 for t in metrics.request_timestamps if t > one_sec_cutoff)
        if burst_count > self.burst_threshold_per_sec:
            metrics.is_blocked = True
            metrics.block_expiry = now + self.penalty_seconds
            metrics.tier = "BLOCKED"
            return True, "BLOCKED", f"Severe burst spike ({burst_count} req/sec exceeded threshold {self.burst_threshold_per_sec})"

        # Check suspicious path scanning (e.g. 404/403 hits)
        if status_code in (403, 404, 401):
            metrics.suspicious_hits += 1
            if metrics.suspicious_hits >= 10:
                metrics.tier = "RESTRICTED"

        if metrics.suspicious_hits >= 25:
            metrics.is_blocked = True
            metrics.block_expiry = now + self.penalty_seconds
            metrics.tier = "BLOCKED"
            return True, "BLOCKED", "Repeated path scanning / unauthorized probing detected"

        return False, metrics.tier, "Normal traffic"

    def get_tier_limits(self, tier: str, base_capacity: float, base_refill: float) -> Tuple[float, float]:
        """Returns adjusted capacity and refill rate according to tier."""
        if tier == "RESTRICTED":
            return base_capacity * 0.25, base_refill * 0.25
        elif tier == "BLOCKED":
            return 0.0, 0.0
        return base_capacity, base_refill
