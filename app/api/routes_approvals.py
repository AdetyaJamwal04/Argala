from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.api.deps import require_scope
from app.core.identity import Principal
from app.hitl.manager import approval_manager
from app.hitl.models import (
    ApprovalResolution,
    ApprovalStatus,
    ApprovalTicket,
    ApprovalTicketCreate,
    ApprovalTicketList,
)
from app.hitl.web_ui import HTML_TEMPLATE

router = APIRouter(prefix="/approvals", tags=["Human-in-the-Loop (HITL)"])


@router.get("/ui", response_class=HTMLResponse)
async def serve_mobile_console():
    """
    Serves the mobile-optimized dark-mode web console for human review.
    Accessible from any phone browser on the mesh at http://<phone-ip>:8000/v1/approvals/ui.
    """
    return HTMLResponse(content=HTML_TEMPLATE)


@router.post("/request", response_model=ApprovalTicket, status_code=status.HTTP_201_CREATED)
async def request_approval(
    req: ApprovalTicketCreate,
    principal: Principal = Depends(require_scope("hitl:request")),
) -> ApprovalTicket:
    """
    Creates an approval ticket and physically alerts the user (vibration + TTS announcement + notification).
    Requires 'hitl:request' capability.
    """
    return approval_manager.create_ticket(req)


@router.get("/{ticket_id}", response_model=ApprovalTicket)
async def get_ticket_status(
    ticket_id: str,
    principal: Principal = Depends(require_scope("hitl:read")),
) -> ApprovalTicket:
    """
    Polls the current status of an approval ticket.
    Once approved, the 'token' field contains the cryptographic HMAC signature.
    Requires 'hitl:read' capability.
    """
    ticket = approval_manager.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval ticket '{ticket_id}' not found",
        )
    return ticket


@router.get("", response_model=ApprovalTicketList)
async def list_tickets(
    limit: int = 50,
    status: Optional[ApprovalStatus] = None,
    principal: Principal = Depends(require_scope("hitl:read")),
) -> ApprovalTicketList:
    """Lists recent approval tickets with optional status filtering."""
    tickets = approval_manager.list_tickets(limit=limit, status=status)
    return ApprovalTicketList(tickets=tickets, total=len(tickets))


@router.post("/{ticket_id}/resolve", response_model=ApprovalTicket)
async def resolve_ticket(
    ticket_id: str,
    resolution: ApprovalResolution,
    principal: Principal = Depends(require_scope("hitl:resolve")),
) -> ApprovalTicket:
    """
    Human operator endpoint to Approve or Reject a pending action.
    Approving automatically triggers cryptographic token issuance.
    Requires 'hitl:resolve' capability (owner/mobile only).
    """
    try:
        return approval_manager.resolve_ticket(ticket_id, resolution)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
