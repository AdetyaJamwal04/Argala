import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.db.database import db_session
from app.hardware.actuation import send_android_notification, speak_tts, vibrate_phone
from app.hitl.models import (
    ApprovalResolution,
    ApprovalStatus,
    ApprovalTicket,
    ApprovalTicketCreate,
    RiskLevel,
)
from app.vault.manager import vault_manager
from app.vault.models import ActionIntent, SignedActionToken

logger = logging.getLogger(__name__)


def _row_to_ticket(row) -> ApprovalTicket:
    token = None
    if row["signed_token"]:
        token = SignedActionToken(**json.loads(row["signed_token"]))

    return ApprovalTicket(
        id=row["id"],
        action=row["action"],
        target=row["target"],
        parameters=json.loads(row["parameters"]) if row["parameters"] else {},
        requester=row["requester"],
        risk_level=RiskLevel(row["risk_level"]),
        summary=row["summary"],
        status=ApprovalStatus(row["status"]),
        token=token,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        resolved_at=row["resolved_at"],
        resolved_by=row["resolved_by"],
    )


class ApprovalManager:
    """
    Human-in-the-Loop Approval Ticket Manager.
    Coordinates physical actuation (vibration, TTS), state transitions,
    countdown expiration, and automatic cryptographic signing upon approval.
    """

    def __init__(self):
        self._init_table()

    def _init_table(self):
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_tickets (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                parameters TEXT NOT NULL,
                requester TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                signed_token TEXT,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                resolved_at REAL,
                resolved_by TEXT
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_tickets(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_expires ON approval_tickets(expires_at);")
            cursor.close()

    def create_ticket(self, req: ApprovalTicketCreate) -> ApprovalTicket:
        """
        Creates an approval ticket and immediately triggers physical device actuation.
        """
        now = time.time()
        ticket_id = str(uuid.uuid4())
        expires_at = now + req.ttl_seconds

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO approval_tickets (
                    id, action, target, parameters, requester, risk_level,
                    summary, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ticket_id,
                    req.action,
                    req.target,
                    json.dumps(req.parameters),
                    req.requester,
                    req.risk_level.value,
                    req.summary,
                    ApprovalStatus.PENDING.value,
                    now,
                    expires_at,
                ),
            )
            cursor.close()

        logger.info("Created approval ticket [%s] for action: %s (TTL: %ss)", ticket_id, req.action, req.ttl_seconds)

        # Trigger Physical Actuation Asynchronously
        try:
            loop = asyncio.get_running_loop()
            if req.vibrate:
                loop.create_task(vibrate_phone(duration_ms=600))
            if req.sound_alert:
                announcement = f"Approval required: {req.requester} requests {req.action} on {req.target}."
                loop.create_task(speak_tts(announcement))
            loop.create_task(send_android_notification(f"Approval: {req.action}", req.summary, ticket_id))
        except RuntimeError:
            pass  # No running event loop in test/sync context

        return ApprovalTicket(
            id=ticket_id,
            action=req.action,
            target=req.target,
            parameters=req.parameters,
            requester=req.requester,
            risk_level=req.risk_level,
            summary=req.summary,
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=expires_at,
        )

    def get_ticket(self, ticket_id: str) -> Optional[ApprovalTicket]:
        """
        Retrieves ticket and automatically enforces expiration if TTL passed.
        """
        now = time.time()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approval_tickets WHERE id = ?;", (ticket_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return None

            ticket = _row_to_ticket(row)

            # Check if pending ticket has expired
            if ticket.status == ApprovalStatus.PENDING and now > ticket.expires_at:
                cursor.execute(
                    "UPDATE approval_tickets SET status = ? WHERE id = ?;",
                    (ApprovalStatus.EXPIRED.value, ticket_id),
                )
                ticket.status = ApprovalStatus.EXPIRED
                logger.info("Ticket [%s] automatically expired at %s", ticket_id, now)

            cursor.close()
            return ticket

    def list_tickets(self, limit: int = 50, status: Optional[ApprovalStatus] = None) -> List[ApprovalTicket]:
        now = time.time()
        with db_session() as conn:
            cursor = conn.cursor()
            
            # Lazy expiration: update all pending expired tickets
            cursor.execute(
                "UPDATE approval_tickets SET status = ? WHERE status = ? AND expires_at < ?;",
                (ApprovalStatus.EXPIRED.value, ApprovalStatus.PENDING.value, now),
            )

            if status:
                cursor.execute(
                    "SELECT * FROM approval_tickets WHERE status = ? ORDER BY created_at DESC LIMIT ?;",
                    (status.value, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM approval_tickets ORDER BY created_at DESC LIMIT ?;",
                    (limit,),
                )
            rows = cursor.fetchall()
            cursor.close()
            return [_row_to_ticket(r) for r in rows]

    def resolve_ticket(self, ticket_id: str, resolution: ApprovalResolution) -> ApprovalTicket:
        """
        Human decision handler:
        If approved: automatically invokes the vault to produce a signed execution token.
        If rejected: updates status to REJECTED.
        """
        now = time.time()
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise KeyError(f"Ticket '{ticket_id}' not found")

        if ticket.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot resolve ticket in '{ticket.status.value}' state")

        if now > ticket.expires_at:
            raise ValueError("Ticket has expired and cannot be approved")

        signed_token = None
        if resolution.approved:
            new_status = ApprovalStatus.APPROVED
            # Automatically cryptographically sign the approved action!
            intent = ActionIntent(
                action=ticket.action,
                target=ticket.target,
                parameters=ticket.parameters,
                requester=ticket.requester,
                timestamp=now,
                nonce=str(uuid.uuid4()),
            )
            signed_token = vault_manager.sign_action(intent, validity_seconds=300.0)
            token_json = signed_token.json()
            logger.info("Human APPROVED ticket [%s] -> Issued cryptographic token", ticket_id)
        else:
            new_status = ApprovalStatus.REJECTED
            token_json = None
            logger.info("Human REJECTED ticket [%s]", ticket_id)

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE approval_tickets
                SET status = ?,
                    signed_token = ?,
                    resolved_at = ?,
                    resolved_by = ?
                WHERE id = ?;
                """,
                (new_status.value, token_json, now, resolution.resolved_by, ticket_id),
            )
            cursor.close()

        ticket.status = new_status
        ticket.token = signed_token
        ticket.resolved_at = now
        ticket.resolved_by = resolution.resolved_by
        return ticket


# Global Approval Manager singleton
approval_manager = ApprovalManager()
