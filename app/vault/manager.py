import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.database import db_session
from app.vault.crypto import (
    compute_action_hash,
    decrypt_payload,
    encrypt_payload,
    sign_action_hash,
    verify_action_signature,
)
from app.vault.models import (
    ActionIntent,
    ActionVerificationResponse,
    BrokerRequest,
    SecretMetadata,
    SecretStoreRequest,
    SignedActionToken,
)

logger = logging.getLogger(__name__)


class VaultManager:
    """
    Sovereign Vault & Cryptographic Signing Manager.
    Enforces Canonical Action Hashing, Anti-Replay Nonce Tracking,
    and Secretless Outbound API Brokering.
    """

    def __init__(self):
        self._init_vault_tables()

    def _init_vault_tables(self):
        """Creates vault tables if not already present."""
        with db_session() as conn:
            cursor = conn.cursor()

            # 1. Encrypted Secrets Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_secrets (
                secret_id TEXT PRIMARY KEY,
                encrypted_blob TEXT NOT NULL,
                description TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)

            # 2. Replay Prevention Nonce Cache
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS used_nonces (
                nonce TEXT PRIMARY KEY,
                used_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nonces_expires_at ON used_nonces(expires_at);")

            # 3. Append-Only Tamper-Evident Audit Ledger
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                requester TEXT NOT NULL,
                action_hash TEXT,
                details TEXT,
                timestamp REAL NOT NULL
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_ledger(timestamp DESC);")
            cursor.close()

    def _log_audit_event(
        self,
        event_type: str,
        requester: str,
        action_hash: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Appends an immutable entry to the audit ledger."""
        now = time.time()
        event_id = str(uuid.uuid4())
        details_str = json.dumps(details) if details else None

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_ledger (id, event_type, requester, action_hash, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (event_id, event_type, requester, action_hash, details_str, now),
            )
            cursor.close()

    # ------------------------------------------------------------------------
    # Cryptographic Action Signing & Verification
    # ------------------------------------------------------------------------

    def sign_action(self, intent: ActionIntent, validity_seconds: float = 300.0) -> SignedActionToken:
        """
        Calculates canonical action hash and produces an unforgeable HMAC signature.
        """
        from app.core.identity import lockdown_manager
        if lockdown_manager.is_locked():
            raise PermissionError("EMERGENCY LOCKDOWN ACTIVE: Sovereign Vault signing is frozen.")

        if lockdown_manager.is_revoked(intent.requester):
            raise PermissionError(f"Principal '{intent.requester}' has been revoked.")

        now = time.time()
        action_hash = compute_action_hash(
            action=intent.action,
            target=intent.target,
            parameters=intent.parameters,
            requester=intent.requester,
            timestamp=intent.timestamp,
            nonce=intent.nonce,
        )

        signature = sign_action_hash(action_hash, settings.API_KEY)
        expires_at = now + validity_seconds

        token = SignedActionToken(
            action_hash=action_hash,
            signature=signature,
            signer_node_id=settings.NODE_ID,
            issued_at=now,
            expires_at=expires_at,
            nonce=intent.nonce,
        )

        self._log_audit_event(
            event_type="ACTION_SIGNED",
            requester=intent.requester,
            action_hash=action_hash,
            details={
                "action": intent.action,
                "target": intent.target,
                "nonce": intent.nonce,
                "expires_at": expires_at,
            },
        )
        logger.info("Signed action [%s] for requester [%s] -> Hash: %s", intent.action, intent.requester, action_hash)
        return token

    def verify_action(self, intent: ActionIntent, token: SignedActionToken) -> ActionVerificationResponse:
        """
        Verifies that:
        1. Canonical hash of intent matches token.action_hash (detects TOCTOU parameter tampering).
        2. Token has not expired.
        3. Nonce has not been consumed (detects replay attacks).
        4. Cryptographic HMAC signature matches the gateway master key.
        5. Neither the requester nor the nonce has been revoked.
        """
        from app.core.identity import lockdown_manager

        expected_hash = compute_action_hash(
            action=intent.action,
            target=intent.target,
            parameters=intent.parameters,
            requester=intent.requester,
            timestamp=intent.timestamp,
            nonce=intent.nonce,
        )

        if lockdown_manager.is_revoked(intent.requester) or lockdown_manager.is_revoked(token.nonce):
            return ActionVerificationResponse(
                valid=False,
                reason=f"Action rejected: Requester '{intent.requester}' or token nonce is revoked",
                action_hash=expected_hash,
            )

        now = time.time()

        if not expected_hash == token.action_hash:
            logger.warning("Action verification failed: Parameter tampering detected! Hash mismatch.")
            return ActionVerificationResponse(
                valid=False,
                reason="Cryptographic hash mismatch: Parameters or target were altered after signing (TOCTOU violation)",
                action_hash=expected_hash,
            )

        # Step 2: Check expiration
        if token.expires_at < now:
            logger.warning("Action verification failed: Token expired at %s (now=%s)", token.expires_at, now)
            return ActionVerificationResponse(
                valid=False,
                reason=f"Action token has expired (expired {round(now - token.expires_at, 1)}s ago)",
                action_hash=expected_hash,
            )

        # Step 3: Anti-replay nonce check
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nonce FROM used_nonces WHERE nonce = ?;", (token.nonce,))
            if cursor.fetchone():
                cursor.close()
                logger.warning("Action verification failed: Replay attack detected! Nonce [%s] reused.", token.nonce)
                return ActionVerificationResponse(
                    valid=False,
                    reason=f"Replay attack detected: Nonce '{token.nonce}' has already been consumed",
                    action_hash=expected_hash,
                )

            # Check signature
            if not verify_action_signature(expected_hash, token.signature, settings.API_KEY):
                cursor.close()
                logger.warning("Action verification failed: Invalid cryptographic signature.")
                return ActionVerificationResponse(
                    valid=False,
                    reason="Invalid cryptographic signature: Signature does not match gateway signing key",
                    action_hash=expected_hash,
                )

            # Consume nonce
            cursor.execute(
                "INSERT INTO used_nonces (nonce, used_at, expires_at) VALUES (?, ?, ?);",
                (token.nonce, now, token.expires_at),
            )
            # Prune expired nonces to keep table bounded
            cursor.execute("DELETE FROM used_nonces WHERE expires_at < ?;", (now,))
            cursor.close()

        self._log_audit_event(
            event_type="ACTION_VERIFIED",
            requester=intent.requester,
            action_hash=expected_hash,
            details={"action": intent.action, "target": intent.target, "nonce": token.nonce},
        )
        logger.info("Successfully verified and consumed action token [%s]", expected_hash)
        return ActionVerificationResponse(valid=True, action_hash=expected_hash)

    # ------------------------------------------------------------------------
    # Encrypted Secrets & Secretless Execution
    # ------------------------------------------------------------------------

    def store_secret(self, req: SecretStoreRequest) -> SecretMetadata:
        """Encrypts plaintext with PBKDF2-derived KEK and stores in SQLite."""
        from app.core.identity import lockdown_manager
        if lockdown_manager.is_locked():
            raise PermissionError("EMERGENCY LOCKDOWN ACTIVE: Vault modifications are frozen.")

        now = time.time()
        encrypted_blob = encrypt_payload(req.plaintext, settings.API_KEY)

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO vault_secrets (secret_id, encrypted_blob, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(secret_id) DO UPDATE SET
                    encrypted_blob = excluded.encrypted_blob,
                    description = excluded.description,
                    updated_at = excluded.updated_at;
                """,
                (req.secret_id, encrypted_blob, req.description, now, now),
            )
            cursor.close()

        self._log_audit_event(
            event_type="SECRET_STORED",
            requester="admin",
            details={"secret_id": req.secret_id, "description": req.description},
        )
        logger.info("Encrypted and stored secret [%s]", req.secret_id)
        return SecretMetadata(
            secret_id=req.secret_id,
            description=req.description,
            created_at=now,
            updated_at=now,
        )

    def list_secrets(self) -> List[SecretMetadata]:
        """Lists metadata for all stored secrets. Never returns raw plaintext."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT secret_id, description, created_at, updated_at FROM vault_secrets ORDER BY secret_id ASC;")
            rows = cursor.fetchall()
            cursor.close()
            return [
                SecretMetadata(
                    secret_id=r["secret_id"],
                    description=r["description"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def _get_decrypted_secret(self, secret_id: str) -> str:
        """Internal only: Decrypts secret for outbound brokering."""
        from app.core.identity import lockdown_manager
        if lockdown_manager.is_locked():
            raise PermissionError("EMERGENCY LOCKDOWN ACTIVE: Secret decryption is frozen.")

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT encrypted_blob FROM vault_secrets WHERE secret_id = ?;", (secret_id,))
            row = cursor.fetchone()
            cursor.close()
            if not row:
                raise KeyError(f"Secret '{secret_id}' not found in vault")

            return decrypt_payload(row["encrypted_blob"], settings.API_KEY)

    async def broker_http_request(self, broker_req: BrokerRequest) -> Dict[str, Any]:
        """
        Secretless Execution Broker:
        The agent passes target URL and parameters. The phone injects the stored credential
        and performs the outbound HTTP call from the phone's network interface.
        The calling agent receives the API output, never the raw credential.
        """
        import urllib.parse
        parsed = urllib.parse.urlparse(broker_req.url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ValueError("Invalid target URL: missing hostname.")

        blocked_hosts = {"127.0.0.1", "localhost", "0.0.0.0", "169.254.169.254", "::1"}
        if hostname in blocked_hosts or hostname.startswith("127."):
            raise ValueError(f"Access to private/loopback address '{hostname}' is prohibited via vault broker.")

        headers = dict(broker_req.headers or {})

        # Inject credential if requested
        if broker_req.secret_id:
            plaintext_secret = self._get_decrypted_secret(broker_req.secret_id)
            header_value = f"{broker_req.header_prefix}{plaintext_secret}"
            headers[broker_req.header_name] = header_value

        data_bytes = json.dumps(broker_req.json_body).encode("utf-8") if broker_req.json_body else None
        if data_bytes and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        # Execute outbound HTTP call asynchronously using thread pool executor
        def _do_request():
            req = urllib.request.Request(
                broker_req.url,
                data=data_bytes,
                headers=headers,
                method=broker_req.method.upper(),
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    resp_data = resp.read().decode("utf-8", errors="ignore")
                    try:
                        parsed_body = json.loads(resp_data)
                    except Exception:
                        parsed_body = resp_data
                    return {
                        "status_code": resp.status,
                        "headers": dict(resp.headers),
                        "body": parsed_body,
                    }
            except urllib.error.HTTPError as e:
                err_data = e.read().decode("utf-8", errors="ignore")
                try:
                    parsed_err = json.loads(err_data)
                except Exception:
                    parsed_err = err_data
                return {
                    "status_code": e.code,
                    "headers": dict(e.headers),
                    "body": parsed_err,
                }

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _do_request)

        self._log_audit_event(
            event_type="SECRET_BROKERED",
            requester="agent",
            details={
                "target_url": broker_req.url,
                "method": broker_req.method,
                "secret_id_used": broker_req.secret_id,
                "status_code": result.get("status_code"),
            },
        )
        return result


# Global Vault Manager singleton
vault_manager = VaultManager()
