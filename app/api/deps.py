import logging
from typing import Callable, Optional
from fastapi import Header, HTTPException, Query, status

from app.core.identity import Principal, lockdown_manager, resolve_principal

logger = logging.getLogger(__name__)


async def get_current_principal(
    x_api_key: Optional[str] = Header(None, description="Gateway Ingress API Key"),
    api_key: Optional[str] = Query(None, description="Gateway Ingress API Key via query param"),
    x_principal_id: Optional[str] = Header(None, description="Optional Principal ID to assume with master key"),
    principal_id: Optional[str] = Query(None, description="Optional Principal ID via query param"),
) -> Principal:
    """
    Zero-Trust Principal resolver.
    Enforces authentication, principal revocation, and emergency quarantine.
    Accepts credentials via X-API-Key header or ?api_key= query parameter for browser testing.
    """
    effective_key = x_api_key or api_key
    effective_principal = x_principal_id or principal_id

    if not effective_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key (provide via X-API-Key header or ?api_key= query parameter)",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    try:
        principal = resolve_principal(effective_key, effective_principal)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return principal


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="Gateway Ingress API Key"),
    api_key: Optional[str] = Query(None, description="Optional API Key via query param"),
    x_principal_id: Optional[str] = Header(None, description="Optional Principal ID"),
    principal_id: Optional[str] = Query(None, description="Optional Principal ID via query param"),
) -> str:
    """
    Backward-compatible dependency for existing routes.
    Enforces active authentication and Emergency Lockdown check.
    """
    principal = await get_current_principal(x_api_key, api_key, x_principal_id, principal_id)

    if lockdown_manager.is_locked() and principal.id != "admin-console":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="EMERGENCY LOCKDOWN ACTIVE: All agent capabilities revoked. Vault is locked.",
        )

    return x_api_key or api_key


def require_scope(required_scope: str) -> Callable:
    """
    FastAPI dependency factory for granular capability enforcement.
    Blocks callers lacking the required scope or while under emergency quarantine.
    """
    async def dependency(
        x_api_key: Optional[str] = Header(None, description="Gateway Ingress API Key"),
        api_key: Optional[str] = Query(None, description="Optional API Key via query param"),
        x_principal_id: Optional[str] = Header(None, description="Optional Principal ID"),
        principal_id: Optional[str] = Query(None, description="Optional Principal ID via query param"),
    ) -> Principal:
        resolved = await get_current_principal(x_api_key, api_key, x_principal_id, principal_id)

        # Emergency Lockdown gate: All non-admin-unlock actions are blocked with HTTP 423
        if lockdown_manager.is_locked() and required_scope not in ("admin:unlock", "admin:status"):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="EMERGENCY LOCKDOWN ACTIVE: All agent capabilities revoked. Vault is locked.",
            )

        if not resolved.has_scope(required_scope):
            logger.warning(
                "Scope violation: Principal '%s' attempted to use '%s' but only has scopes %s",
                resolved.id, required_scope, resolved.scopes
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Principal '{resolved.id}' lacks required capability scope '{required_scope}'",
            )

        return resolved

    return dependency

