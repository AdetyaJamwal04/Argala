from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_scope
from app.core.identity import Principal
from app.vault.manager import vault_manager
from app.vault.models import (
    ActionIntent,
    ActionVerificationRequest,
    ActionVerificationResponse,
    BrokerRequest,
    SecretListResponse,
    SecretMetadata,
    SecretStoreRequest,
    SignedActionToken,
)

router = APIRouter(prefix="/vault", tags=["Sovereign Vault & Signer"])


@router.post("/sign", response_model=SignedActionToken)
async def sign_action_intent(
    intent: ActionIntent,
    principal: Principal = Depends(require_scope("vault:sign")),
) -> SignedActionToken:
    """
    Produces a canonical SHA-256 action hash and issues an HMAC-SHA256 signature.
    Cryptographically binds the requester, target, timestamp, nonce, and exact parameters.
    Requires 'vault:sign' capability.
    """
    return vault_manager.sign_action(intent)


@router.post("/verify", response_model=ActionVerificationResponse)
async def verify_action_token(
    req: ActionVerificationRequest,
    principal: Principal = Depends(require_scope("vault:verify")),
) -> ActionVerificationResponse:
    """
    Verifies that an action token has a valid HMAC signature, has not expired,
    has not had its parameters altered (TOCTOU prevention), and consumes the nonce to block replay attacks.
    Requires 'vault:verify' capability.
    """
    return vault_manager.verify_action(req.intent, req.token)


@router.post("/secrets", response_model=SecretMetadata, status_code=status.HTTP_201_CREATED)
async def store_secret(
    req: SecretStoreRequest,
    principal: Principal = Depends(require_scope("vault:secrets")),
) -> SecretMetadata:
    """
    Encrypts a credential using PBKDF2-derived authenticated encryption
    and stores it in the edge SQLite vault.
    Requires 'vault:secrets' capability.
    """
    return vault_manager.store_secret(req)


@router.get("/secrets", response_model=SecretListResponse)
async def list_stored_secrets(
    principal: Principal = Depends(require_scope("vault:secrets")),
) -> SecretListResponse:
    """
    Lists metadata for stored credentials.
    CRITICAL SECURITY INVARIANT: Never exposes plaintext secret values.
    Requires 'vault:secrets' capability.
    """
    secrets = vault_manager.list_secrets()
    return SecretListResponse(secrets=secrets, total=len(secrets))


@router.post("/broker")
async def broker_outbound_request(
    broker_req: BrokerRequest,
    principal: Principal = Depends(require_scope("vault:broker")),
) -> Dict[str, Any]:
    """
    Secretless Outbound API Broker:
    Executes an outbound HTTP request from the phone, securely injecting the requested vault credential.
    The calling agent receives the API output, never the raw credential.
    Requires 'vault:broker' capability.
    """
    try:
        return await vault_manager.broker_http_request(broker_req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Broker failed: {str(e)}")
