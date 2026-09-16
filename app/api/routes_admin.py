from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_scope
from app.core.identity import Principal, lockdown_manager

router = APIRouter(prefix="/admin", tags=["Sovereign Administration & Kill Switch"])


class LockdownRequest(BaseModel):
    reason: str = Field(default="Suspicious activity detected", description="Reason for triggering lockdown")
    initiated_by: str = Field(default="admin-console", description="Entity initiating lockdown")


class UnlockRequest(BaseModel):
    cleared_by: str = Field(default="admin-console", description="Admin confirming restoration")


class RevokeRequest(BaseModel):
    target: str = Field(..., description="Target identifier (Principal ID or token nonce)")
    revocation_type: str = Field(default="PRINCIPAL", description="'PRINCIPAL', 'NONCE', or 'TOKEN'")
    reason: str = Field(default="Manual revocation by admin", description="Reason for revocation")


@router.get("", summary="Admin Root Status")
@router.get("/status", summary="Admin Operational Status")
async def get_admin_status(
    principal: Principal = Depends(require_scope("admin:status")),
) -> Dict[str, Any]:
    """
    Returns global gateway operational state, lockdown status, and revocation metrics.
    Accessible via header or ?api_key= query parameter.
    """
    return lockdown_manager.get_status()



@router.post("/lockdown")
async def trigger_emergency_lockdown(
    req: LockdownRequest,
    principal: Principal = Depends(require_scope("admin:lockdown")),
) -> Dict[str, Any]:
    """
    EMERGENCY KILL SWITCH:
    Instant remote session quarantine and vault lockdown.
    Revokes in-flight agent access, halts queue processing, and sounds physical mobile alarms.
    """
    result = await lockdown_manager.trigger_lockdown(
        reason=req.reason,
        initiated_by=f"{principal.id} ({req.initiated_by})",
    )
    return {
        "status": "EMERGENCY_LOCKDOWN_ACTIVATED",
        "lockdown": result,
        "message": "Gateway successfully quarantined. All agent capabilities revoked.",
    }


@router.post("/unlock")
async def restore_from_lockdown(
    req: UnlockRequest,
    principal: Principal = Depends(require_scope("admin:unlock")),
) -> Dict[str, Any]:
    """
    Restores gateway from Emergency Lockdown to NORMAL state.
    Requires administrative scope authorization.
    """
    result = await lockdown_manager.restore_system(
        cleared_by=f"{principal.id} ({req.cleared_by})",
    )
    return {
        "status": "NORMAL",
        "restored": result,
        "message": "Emergency lockdown disarmed. Sovereign control plane restored.",
    }


@router.post("/revoke")
async def revoke_entity(
    req: RevokeRequest,
    principal: Principal = Depends(require_scope("admin:revoke")),
) -> Dict[str, Any]:
    """
    Adds a principal ID or token/nonce to the immutable revocation ledger.
    """
    lockdown_manager.revoke(
        target=req.target,
        revocation_type=req.revocation_type,
        reason=req.reason,
    )
    return {
        "status": "REVOKED",
        "target": req.target,
        "type": req.revocation_type,
        "reason": req.reason,
    }
