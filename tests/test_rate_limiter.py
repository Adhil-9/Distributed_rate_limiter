"""
Unit tests for Token Bucket algorithm & single-node decision flow.
"""

import time
import pytest
from src.core.algorithms import TokenBucket, LeakyBucket, FixedWindowCounter, SlidingWindowLog


def test_token_bucket_initial_capacity():
    bucket = TokenBucket(capacity=10.0, refill_rate=2.0)
    allowed, remaining, reset_in = bucket.allow_request(1.0)
    assert allowed is True
    assert remaining == 9.0


def test_token_bucket_throttling():
    bucket = TokenBucket(capacity=2.0, refill_rate=1.0)
    
    # Consume all tokens
    bucket.allow_request(1.0)
    bucket.allow_request(1.0)
    
    # 3rd request should fail
    allowed, remaining, retry_after = bucket.allow_request(1.0)
    assert allowed is False
    assert retry_after > 0.0


def test_token_bucket_refill():
    bucket = TokenBucket(capacity=5.0, refill_rate=10.0)
    now = time.time()
    
    # Exhaust bucket
    for _ in range(5):
        bucket.allow_request(1.0, now=now)
    
    # Advance time by 0.5s -> Should refill 5 tokens
    future = now + 0.5
    allowed, remaining, _ = bucket.allow_request(1.0, now=future)
    assert allowed is True
    assert remaining >= 3.9


def test_fixed_window_boundary_behavior():
    fw = FixedWindowCounter(limit=2, window_seconds=10.0)
    assert fw.allow_request()[0] is True
    assert fw.allow_request()[0] is True
    assert fw.allow_request()[0] is False
