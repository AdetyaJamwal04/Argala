import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Dict, Optional

from app.config import settings
from app.mcp.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    JsonRpcRequest,
    JsonRpcResponse,
    make_error_response,
    make_success_response,
)
from app.mcp.tools import tool_registry

logger = logging.getLogger(__name__)


class McpSessionManager:
    """
    Manages active SSE client sessions and JSON-RPC message dispatching.
    """

    def __init__(self):
        # Maps session_id -> asyncio.Queue of JSON strings to stream to the client
        self._sessions: Dict[str, asyncio.Queue] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = asyncio.Queue()
        logger.info("New MCP session created: %s", session_id)
        return session_id

    def remove_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("MCP session terminated: %s", session_id)

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    async def send_to_session(self, session_id: str, message: dict):
        """Pushes a JSON message into the client's SSE streaming queue."""
        if session_id in self._sessions:
            await self._sessions[session_id].put(message)

    async def stream_events(self, session_id: str) -> AsyncGenerator[str, None]:
        """
        Yields formatted SSE chunks:
        event: <event_type>
        data: <json_data>\n\n
        """
        queue = self._sessions.get(session_id)
        if not queue:
            return

        # First frame: advertise the message endpoint for this session according to MCP spec
        endpoint_url = f"/v1/mcp/messages?sessionId={session_id}"
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"

        try:
            while True:
                # Wait for next JSON-RPC frame to send to client
                message = await queue.get()
                message_str = json.dumps(message)
                yield f"event: message\ndata: {message_str}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.remove_session(session_id)

    async def handle_message(self, session_id: str, request_data: dict) -> JsonRpcResponse:
        """
        Core MCP Dispatcher:
        Processes standard MCP methods (initialize, tools/list, tools/call, ping).
        """
        try:
            req = JsonRpcRequest(**request_data)
        except Exception as e:
            return make_error_response(None, INVALID_PARAMS, f"Invalid JSON-RPC request: {str(e)}")

        req_id = req.id
        method = req.method
        params = req.params or {}

        # 1. MCP Initialization Handshake
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
                "serverInfo": {
                    "name": settings.GATEWAY_NAME,
                    "version": "0.1.0",
                },
            }
            return make_success_response(req_id, result)

        # 2. Client Initialization Notification (one-way, no id)
        elif method == "notifications/initialized":
            logger.info("MCP client session %s completed handshake", session_id)
            return make_success_response(req_id, {})

        # 3. Ping
        elif method == "ping":
            return make_success_response(req_id, {})

        # 4. List Tools
        elif method == "tools/list":
            tools = tool_registry.list_tools()
            return make_success_response(req_id, {"tools": tools})

        # 5. Call Tool
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return make_error_response(req_id, INVALID_PARAMS, "Missing tool 'name' in params")

            try:
                result = await tool_registry.call_tool(tool_name, arguments)
                return make_success_response(req_id, result)
            except KeyError:
                return make_error_response(req_id, METHOD_NOT_FOUND, f"Tool '{tool_name}' not found")
            except Exception as e:
                return make_error_response(req_id, INTERNAL_ERROR, f"Tool execution failed: {str(e)}")

        # Unknown method
        else:
            return make_error_response(req_id, METHOD_NOT_FOUND, f"Method '{method}' not implemented")


# Global MCP Session Manager singleton
mcp_manager = McpSessionManager()
