"""
Data models and schemas for the Argala Python SDK.
Compatible with Pydantic v1 and v2.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class EmergencyState(str, Enum):
    NORMAL = "NORMAL"
    EMERGENCY_LOCKDOWN = "EMERGENCY_LOCKDOWN"


class BatteryInfo(BaseModel):
    percentage: int = 100
    plugged: str = "UNKNOWN"
    status: str = "UNKNOWN"
    temperature: float = 0.0
    health: str = "GOOD"
    source: str = "unknown"


class MemoryInfo(BaseModel):
    total_mb: int = 0
    available_mb: int = 0
    used_mb: int = 0
    usage_percent: float = 0.0


class NodeTelemetry(BaseModel):
    node_id: str
    gateway_name: str
    is_android: bool = True
    uptime_seconds: float = 0.0
    timestamp: float
    battery: BatteryInfo
    memory: MemoryInfo

    @property
    def battery_percentage(self) -> int:
        return self.battery.percentage

    @property
    def is_charging(self) -> bool:
        return self.battery.plugged not in ("UNPLUGGED", "NONE", "UNKNOWN", "") and self.battery.status in ("CHARGING", "FULL")

    @property
    def battery_temperature_c(self) -> float:
        return self.battery.temperature

    @property
    def ram_used_mb(self) -> int:
        return self.memory.used_mb

    @property
    def ram_total_mb(self) -> int:
        return self.memory.total_mb

    @property
    def ram_usage_percent(self) -> float:
        return self.memory.usage_percent


class SignedActionToken(BaseModel):
    action_hash: str
    signature: str
    signer_node_id: str = ""
    issued_at: float
    expires_at: float
    nonce: str


class ApprovalTicket(BaseModel):
    id: str
    action: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requester: str = ""
    risk_level: str = "HIGH"
    summary: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    token: Optional[SignedActionToken] = None
    created_at: float
    expires_at: float
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None

    @property
    def prompt(self) -> str:
        return self.summary

    @property
    def timeout_seconds(self) -> int:
        return int(self.expires_at - self.created_at) if self.expires_at and self.created_at else 60


class ApprovalTicketCreate(BaseModel):
    action: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requester: Optional[str] = None
    risk_level: str = "HIGH"
    summary: str
    ttl_seconds: int = 120
    sound_alert: bool = True
    vibrate: bool = True


class ActuationRequest(BaseModel):
    vibrate_ms: Optional[int] = Field(None, ge=50, le=5000)
    speak_text: Optional[str] = Field(None, max_length=500)
    tts_pitch: Optional[float] = 1.0
    tts_rate: Optional[float] = 1.0
    notification_title: Optional[str] = None
    notification_content: Optional[str] = None
    notification_id: Optional[str] = "argala_sdk_alert"


class ActuationResponse(BaseModel):
    status: str = "success"
    vibrated: bool = False
    spoken: bool = False
    notified: bool = False


class BrokerRequest(BaseModel):
    url: str
    method: str = "POST"
    secret_id: Optional[str] = "gemini_api_key"
    header_name: str = "x-goog-api-key"
    header_prefix: str = ""
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    json_body: Optional[Dict[str, Any]] = None


class BrokerResponse(BaseModel):
    status_code: int
    headers: Optional[Dict[str, str]] = None
    body: Any
    elapsed_ms: Optional[float] = None


class JobCreate(BaseModel):
    capability: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class JobRecord(BaseModel):
    id: str
    capability: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    idempotency_key: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    worker_id: Optional[str] = None
    lease_expires_at: Optional[float] = None
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    attempts: Optional[int] = None

    @property
    def attempt_count(self) -> int:
        return self.attempts if self.attempts is not None else self.retry_count


class AdminStatus(BaseModel):
    node_id: str
    gateway_name: str
    emergency_state: EmergencyState
    active_jobs: int = 0
    pending_approvals: int = 0
    revocation_count: int = 0
