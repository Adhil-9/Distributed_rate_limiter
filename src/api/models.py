"""
Pydantic Schemas for Rate Limiter REST API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class RequestSimPayload(BaseModel):
    client_id: str = Field(..., example="client-usr-99")
    endpoint: str = Field(default="/api/v1/resource", example="/api/v1/resource")
    status_code: int = Field(default=200, example=200)
    tokens_requested: float = Field(default=1.0, example=1.0)
    node_id: Optional[str] = Field(default=None, example="gateway-node-1")


class OutageSimPayload(BaseModel):
    storage_down: bool = Field(..., example=True)


class ConfigUpdatePayload(BaseModel):
    capacity: Optional[float] = None
    refill_rate: Optional[float] = None
    consistency_model: Optional[str] = None
    failure_strategy: Optional[str] = None
