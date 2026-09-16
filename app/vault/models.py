import time
from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class ActionIntent(BaseModel):
    action: str = Field(..., description="Action capability identifier (e.g. email.send, github.create_issue)")
    target: str = Field(..., description="Target service or resource (e.g. production-db, github/repo)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task parameters")
    requester: str = Field(..., description="Principal requesting action (e.g. laptop-agent-01)")
    timestamp: float = Field(default_factory=time.time, description="Client creation timestamp")
    nonce: str = Field(..., min_length=8, description="Unique client nonce to prevent replay attacks")


class SignedActionToken(BaseModel):
    action_hash: str = Field(..., description="SHA-256 canonical hash of the intent")
    signature: str = Field(..., description="HMAC-SHA256 signature produced by edge vault")
    signer_node_id: str = Field(..., description="ID of the edge node that authorized the action")
    issued_at: float
    expires_at: float
    nonce: str


class ActionVerificationRequest(BaseModel):
    intent: ActionIntent
    token: SignedActionToken


class ActionVerificationResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    action_hash: str
    verified_at: float = Field(default_factory=time.time)


class SecretStoreRequest(BaseModel):
    secret_id: str = Field(..., min_length=3, description="Unique identifier for the credential (e.g. github_token)")
    plaintext: str = Field(..., min_length=1, description="Raw secret to encrypt and store")
    description: Optional[str] = Field(None, description="Human-readable description of the credential's scope")


class SecretMetadata(BaseModel):
    secret_id: str
    description: Optional[str] = None
    created_at: float
    updated_at: float


class SecretListResponse(BaseModel):
    secrets: List[SecretMetadata]
    total: int


class BrokerRequest(BaseModel):
    url: str = Field(..., description="Target external API URL")
    method: str = Field(default="GET", description="HTTP method: GET, POST, PUT, DELETE, etc.")
    secret_id: Optional[str] = Field(None, description="Vault secret_id to inject into headers")
    header_name: str = Field(default="Authorization", description="Header name for secret injection")
    header_prefix: str = Field(default="Bearer ", description="Prefix before secret (e.g. 'Bearer ', 'token ', or '')")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional HTTP headers")
    json_body: Optional[Dict[str, Any]] = Field(None, description="Optional JSON request payload")
