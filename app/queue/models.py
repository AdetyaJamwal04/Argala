from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobCreate(BaseModel):
    capability: str = Field(..., description="Target capability or task type (e.g. telemetry.snapshot, alert.send)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task arguments")
    idempotency_key: Optional[str] = Field(None, description="Unique client key to prevent duplicate execution on retry")
    max_retries: int = Field(default=3, description="Maximum retry attempts before routing to Dead-Letter Queue")


class JobRecord(BaseModel):
    id: str
    idempotency_key: Optional[str] = None
    capability: str
    payload: Dict[str, Any]
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    worker_id: Optional[str] = None
    lease_expires_at: Optional[float] = None
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None


class JobListResponse(BaseModel):
    jobs: List[JobRecord]
    total: int
