from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.mcp.sse import mcp_manager

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


@router.get("/sse")
async def mcp_sse_endpoint():
    """
    MCP Server-Sent Events (SSE) stream endpoint.
    Clients (Antigravity IDE, Claude Desktop, Cursor) connect here to open
    a persistent channel for receiving JSON-RPC messages from the phone.
    """
    session_id = mcp_manager.create_session()
    
    return StreamingResponse(
        mcp_manager.stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages")
async def mcp_message_endpoint(
    body: dict,
    sessionId: str = Query(..., description="Active MCP session UUID"),
):
    """
    Receives JSON-RPC 2.0 messages from the client and dispatches them
    to the MCP protocol engine, pushing the response down the active SSE stream.
    """
    if not mcp_manager.has_session(sessionId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP Session '{sessionId}' not found or expired",
        )

    # Process JSON-RPC request and push result into the client's SSE queue
    response = await mcp_manager.handle_message(sessionId, body)
    await mcp_manager.send_to_session(sessionId, response.dict(exclude_none=True))

    return {"status": "accepted"}
