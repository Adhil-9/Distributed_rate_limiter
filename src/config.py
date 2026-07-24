"""
Distributed Rate Limiter & Abuse Detection Configuration
"""

from enum import Enum
from pydantic import BaseModel


class ConsistencyModel(str, Enum):
    STRONG = "STRONG"
    EVENTUAL = "EVENTUAL"


class FailureStrategy(str, Enum):
    FAIL_CLOSED = "FAIL_CLOSED"
    FAIL_OPEN = "FAIL_OPEN"
    DEGRADED = "DEGRADED"


class SystemConfig(BaseModel):
    # Token Bucket Defaults
    default_capacity: float = 100.0          # Max tokens per client bucket
    default_refill_rate: float = 10.0        # Tokens added per second
    
    # Consistency & Sync Settings
    consistency_model: ConsistencyModel = ConsistencyModel.EVENTUAL
    sync_interval_ms: int = 100              # Sync with distributed store every 100ms
    replication_lag_ms: int = 50             # Simulated network/replication lag
    batch_sync_size: int = 50                # Max counter deltas per sync batch
    
    # Resilience & Failure Settings
    failure_strategy: FailureStrategy = FailureStrategy.DEGRADED
    degraded_local_factor: float = 0.3       # Limit to 30% of global quota when degraded
    circuit_breaker_failure_threshold: int = 3 # Consecutive failures before opening breaker
    circuit_breaker_recovery_time_s: float = 5.0 # Seconds before probing recovery
    
    # Abuse Detection Settings
    burst_threshold_multiplier: float = 3.0  # 3x refill rate within 1s triggers abuse flag
    abuse_penalty_duration_s: float = 60.0   # Penalty period duration
    suspicious_path_limit: int = 10          # Max 404/403 hits per minute before flagging


config = SystemConfig()
