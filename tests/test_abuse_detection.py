"""
Tests for burst spike and path scan abuse detection.
"""

import time
import pytest
from src.core.abuse_detector import AbuseDetector


def test_burst_spike_detection():
    detector = AbuseDetector(burst_threshold_per_sec=10, penalty_seconds=5.0)
    client_id = "attacker-1"
    now = time.time()

    # Send 9 requests within 1 second -> Normal
    for _ in range(9):
        is_abusive, tier, _ = detector.check_abuse(client_id, path="/api", status_code=200, now=now)
        assert is_abusive is False

    # 11th request within same second -> Abusive
    for _ in range(2):
        is_abusive, tier, reason = detector.check_abuse(client_id, path="/api", status_code=200, now=now)
    
    assert is_abusive is True
    assert tier == "BLOCKED"


def test_suspicious_path_scanning():
    detector = AbuseDetector(penalty_seconds=5.0)
    client_id = "scanner-bot"
    now = time.time()

    # Simulate 10 hitting 404
    for _ in range(10):
        detector.check_abuse(client_id, path="/admin/config", status_code=404, now=now)

    _, tier, _ = detector.check_abuse(client_id, path="/api", status_code=200, now=now)
    assert tier == "RESTRICTED"
