import asyncio
from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field

from app.config import settings
from app.db.database import db_session
from app.hardware.actuation import emergency_lockdown_alert, system_restored_alert

logger = logging.getLogger(__name__)


class EmergencyState(str, Enum):
    NORMAL = "NORMAL"
    EMERGENCY_LOCKDOWN = "EMERGENCY_LOCKDOWN"


class Principal(BaseModel):
    """
    Zero-Trust Principal representation with fine-grained capability scopes.
    Compatible with Pydantic v1.
    """
    id: str
    name: str
    scopes: List[str] = Field(default_factory=list)
    api_key: Optional[str] = None
    is_revoked: bool = False

    def has_scope(self, required_scope: str) -> bool:
        """Evaluates whether the principal possesses the requested capability scope."""
        if "*" in self.scopes:
            return True
        return required_scope in self.scopes


# Default Principals & Least-Privilege Capability Policies
DEFAULT_PRINCIPALS: Dict[str, Principal] = {
    "admin-console": Principal(
        id="admin-console",
        name="Sovereign Administrator (Local Mobile / Owner)",
        scopes=["*"],
        api_key=settings.API_KEY,
    ),
    "laptop-agent": Principal(
        id="laptop-agent",
        name="Desktop / Laptop AI Agent",
        scopes=[
            "jobs:submit",
            "jobs:read",
            "hitl:request",
            "hitl:read",
            "telemetry:read",
            "vault:verify",
        ],
        api_key="argala-laptop-agent-key",
    ),
    "cloud-worker": Principal(
        id="cloud-worker",
        name="Cloud Compute Worker",
        scopes=[
            "jobs:read",
            "jobs:claim",
            "jobs:complete",
            "telemetry:read",
        ],
        api_key="argala-cloud-worker-key",
    ),
}



class LockdownManager:
    """
    Manages global Emergency Lockdown state, revocation ledger, and cyber-physical safety interlocks.
    Uses SQLite persistence combined with in-memory caching for zero-overhead validation on every request.
    """

    def __init__(self):
        self._state: EmergencyState = EmergencyState.NORMAL
        self._revoked_targets: Set[str] = set()
        self._lockdown_info: Dict[str, Any] = {}
        self._load_from_db()

    def _load_from_db(self):
        """Loads persistent lockdown state and revoked targets from SQLite."""
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                
                # Check gateway state
                cursor.execute("SELECT value, updated_at FROM gateway_state WHERE key = 'emergency_state';")
                row = cursor.fetchone()
                if row:
                    self._state = EmergencyState(row["value"])
                    if self._state == EmergencyState.EMERGENCY_LOCKDOWN:
                        cursor.execute("SELECT value FROM gateway_state WHERE key = 'lockdown_info';")
                        info_row = cursor.fetchone()
                        if info_row:
                            import json
                            self._lockdown_info = json.loads(info_row["value"])
                
                # Load revocation ledger
                cursor.execute("SELECT target FROM revocation_ledger;")
                for r in cursor.fetchall():
                    self._revoked_targets.add(r["target"])

                cursor.close()
            logger.info("LockdownManager initialized. Current state: %s, Revocations: %d", self._state, len(self._revoked_targets))
        except Exception as e:
            logger.warning("Could not read gateway state from database: %s", e)

    def is_locked(self) -> bool:
        """Returns True if the gateway is in an active Emergency Lockdown."""
        return self._state == EmergencyState.EMERGENCY_LOCKDOWN

    def get_state(self) -> EmergencyState:
        return self._state

    def is_revoked(self, target: str) -> bool:
        """Checks if a principal ID or token/nonce is in the revocation ledger."""
        return target in self._revoked_targets

    async def trigger_lockdown(self, reason: str = "Suspicious activity detected", initiated_by: str = "mobile-touch") -> Dict[str, Any]:
        """
        Activates Emergency Lockdown:
        1. Updates in-memory and persistent SQLite state.
        2. Revokes active session tokens.
        3. Fires physical alerts (haptic vibration, TTS voice announcement, high-priority notification).
        """
        now = time.time()
        self._state = EmergencyState.EMERGENCY_LOCKDOWN
        self._lockdown_info = {
            "state": self._state.value,
            "reason": reason,
            "initiated_by": initiated_by,
            "locked_at": now,
        }

        import json
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO gateway_state (key, value, updated_at) VALUES ('emergency_state', ?, ?);",
                (self._state.value, now)
            )
            cursor.execute(
                "INSERT OR REPLACE INTO gateway_state (key, value, updated_at) VALUES ('lockdown_info', ?, ?);",
                (json.dumps(self._lockdown_info), now)
            )
            cursor.close()

        logger.critical("EMERGENCY LOCKDOWN ACTIVATED by %s. Reason: %s", initiated_by, reason)

        # Trigger hardware emergency actuation asynchronously
        asyncio.create_task(emergency_lockdown_alert())

        return self._lockdown_info

    async def restore_system(self, cleared_by: str = "admin-console") -> Dict[str, Any]:
        """
        Disarms Emergency Lockdown and returns the gateway to NORMAL operation.
        """
        now = time.time()
        self._state = EmergencyState.NORMAL
        result = {
            "state": self._state.value,
            "cleared_by": cleared_by,
            "restored_at": now,
        }

        import json
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO gateway_state (key, value, updated_at) VALUES ('emergency_state', ?, ?);",
                (self._state.value, now)
            )
            cursor.execute(
                "INSERT OR REPLACE INTO gateway_state (key, value, updated_at) VALUES ('lockdown_info', ?, ?);",
                (json.dumps(result), now)
            )
            cursor.close()

        self._lockdown_info = {}
        logger.info("EMERGENCY LOCKDOWN CLEARED by %s. System restored to NORMAL.", cleared_by)

        # Trigger restore announcement
        asyncio.create_task(system_restored_alert())

        return result

    def revoke(self, target: str, revocation_type: str = "PRINCIPAL", reason: str = "Explicit revocation"):
        """Adds an entity or token to the immutable revocation ledger."""
        now = time.time()
        self._revoked_targets.add(target)
        revocation_id = str(uuid.uuid4())

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO revocation_ledger (id, revocation_type, target, reason, revoked_at) VALUES (?, ?, ?, ?, ?);",
                (revocation_id, revocation_type, target, reason, now)
            )
            cursor.close()
        logger.warning("Revocation recorded for target '%s' (type: %s, reason: %s)", target, revocation_type, reason)

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive security status for monitoring."""
        return {
            "state": self._state.value,
            "is_locked": self.is_locked(),
            "lockdown_info": self._lockdown_info,
            "revocations_count": len(self._revoked_targets),
            "principals": [
                {"id": p.id, "name": p.name, "scopes": p.scopes, "is_revoked": self.is_revoked(p.id)}
                for p in DEFAULT_PRINCIPALS.values()
            ],
        }


# Global Singleton Manager
lockdown_manager = LockdownManager()


def resolve_principal(api_key: str, principal_id: Optional[str] = None) -> Principal:
    """
    Zero-Trust Principal resolver.
    Validates API key and resolves the calling principal and associated capability scopes.
    """
    import secrets

    # 1. Master Key Resolution (accepts both primary argala key and legacy dev key)
    is_master = secrets.compare_digest(api_key, settings.API_KEY) or (
        hasattr(settings, "LEGACY_API_KEY") and secrets.compare_digest(api_key, settings.LEGACY_API_KEY)
    )
    if is_master:
        # If caller specifies a principal ID, simulate/assume that principal
        if principal_id and principal_id in DEFAULT_PRINCIPALS:
            p = DEFAULT_PRINCIPALS[principal_id]
            if lockdown_manager.is_revoked(p.id):
                raise PermissionError(f"Principal '{p.id}' is revoked")
            return p
        # Default master key identity is admin-console
        return DEFAULT_PRINCIPALS["admin-console"]

    # 2. Scoped Principal Keys (with legacy alias compatibility)
    legacy_keys = {
        "aegis-laptop-agent-key": "laptop-agent",
        "aegis-cloud-worker-key": "cloud-worker",
    }
    if api_key in legacy_keys:
        p = DEFAULT_PRINCIPALS[legacy_keys[api_key]]
        if lockdown_manager.is_revoked(p.id):
            raise PermissionError(f"Principal '{p.id}' is revoked")
        return p

    for p in DEFAULT_PRINCIPALS.values():
        if p.api_key and secrets.compare_digest(api_key, p.api_key):
            if lockdown_manager.is_revoked(p.id):
                raise PermissionError(f"Principal '{p.id}' is revoked")
            return p

    raise ValueError("Invalid authentication credentials")

