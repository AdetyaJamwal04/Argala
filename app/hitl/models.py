from enum import Enum
import time
from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from app.vault.models import SignedActionToken


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalTicketCreate(BaseModel):
    action: str = Field(..., description="Action capability identifier (e.g. database.drop, email.send)")
    target: str = Field(..., description="Target service or resource (e.g. production-db)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters that will be cryptographically bound")
    requester: str = Field(..., description="Agent or principal requesting authorization")
    risk_level: RiskLevel = Field(default=RiskLevel.HIGH, description="Risk assessment level")
    summary: str = Field(..., description="Plain-English explanation displayed on the phone")
    ttl_seconds: int = Field(default=120, ge=10, le=3600, description="Expiration countdown in seconds")
    sound_alert: bool = Field(default=True, description="Whether to speak the alert aloud via TTS")
    vibrate: bool = Field(default=True, description="Whether to physically vibrate the phone")


class ApprovalTicket(BaseModel):
    id: str
    action: str
    target: str
    parameters: Dict[str, Any]
    requester: str
    risk_level: RiskLevel
    summary: str
    status: ApprovalStatus
    token: Optional[SignedActionToken] = None
    created_at: float
    expires_at: float
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None


class ApprovalResolution(BaseModel):
    approved: bool = Field(..., description="True to authorize and issue cryptographic token; False to reject")
    resolved_by: str = Field(default="human-operator", description="Operator identity confirming action")
    notes: Optional[str] = Field(None, description="Optional explanation or audit notes")


class ApprovalTicketList(BaseModel):
    tickets: List[ApprovalTicket]
    total: int
