import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

from app.config import settings
from app.hardware.telemetry import get_node_telemetry

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ToolRegistry:
    """
    Registry for MCP Tools.
    Handles dynamic discovery, JSON Schema generation, and dispatching execution.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_default_tools()

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
    ):
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            inputSchema=input_schema,
        )
        self._handlers[name] = handler
        logger.info("Registered MCP tool: %s", name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns tool definitions conforming to the MCP tools/list specification."""
        return [tool.dict() for tool in self._tools.values()]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a registered tool and wraps the result in MCP's standard content format.
        """
        if name not in self._handlers:
            raise KeyError(f"Tool '{name}' is not registered")

        handler = self._handlers[name]
        args = arguments or {}

        try:
            result = await handler(**args)
            
            # Format result according to MCP standard: content array of text/json
            if isinstance(result, (dict, list)):
                content_text = json.dumps(result, indent=2)
            else:
                content_text = str(result)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": content_text,
                    }
                ],
                "isError": False,
            }
        except Exception as e:
            logger.error("Error executing MCP tool '%s': %s", name, e, exc_info=True)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool execution failed: {str(e)}",
                    }
                ],
                "isError": True,
            }

    def _register_default_tools(self):
        """Registers the baseline Android edge tools."""
        
        # Tool 1: Live Hardware Telemetry
        self.register_tool(
            name="android_get_telemetry",
            description="Retrieves live hardware telemetry from the Android phone including battery percentage, charging state, thermals, and RAM usage.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
            handler=self._handle_telemetry,
        )

        # Tool 2: Ping / Liveness
        self.register_tool(
            name="android_ping",
            description="Pings the Android control plane over the mesh network to verify liveness and check latency.",
            input_schema={
                "type": "object",
                "properties": {
                    "echo": {
                        "type": "string",
                        "description": "Optional text to echo back from the phone",
                    }
                },
                "required": [],
            },
            handler=self._handle_ping,
        )

        # Tool 3: Submit Asynchronous Job
        self.register_tool(
            name="android_submit_job",
            description="Submits an asynchronous task to the durable SQLite queue. Returns a job_id with initial PENDING status.",
            input_schema={
                "type": "object",
                "properties": {
                    "capability": {
                        "type": "string",
                        "description": "Task capability to execute: 'telemetry.snapshot', 'system.echo', etc.",
                    },
                    "payload": {
                        "type": "object",
                        "description": "JSON arguments for the task",
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional unique client key to prevent duplicate job execution on retry",
                    },
                },
                "required": ["capability"],
            },
            handler=self._handle_submit_job,
        )

        # Tool 4: Query Job Status & Result
        self.register_tool(
            name="android_get_job",
            description="Queries the execution status, output, and error state of a queued background job.",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The unique UUID of the job",
                    }
                },
                "required": ["job_id"],
            },
            handler=self._handle_get_job,
        )

        # Tool 5: Request Cyber-Physical Human Approval (HITL)
        self.register_tool(
            name="android_request_approval",
            description="Requests physical Human-in-the-Loop (HITL) approval on the Android phone. Triggers haptic vibration, TTS voice announcement, and displays an interactive approval ticket on the phone screen.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action being requested, e.g. 'database.drop_schema' or 'deploy.production'",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target resource, e.g. 'prod_database_cluster'",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Risk level of the requested action",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Human-readable question or warning displayed on the phone",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Timeout in seconds before the ticket expires (default 60)",
                    },
                },
                "required": ["action", "target"],
            },
            handler=self._handle_request_approval,
        )

        # Tool 6: Direct Hardware Actuation
        self.register_tool(
            name="android_actuate",
            description="Directly triggers physical sensory cues on the Android phone: haptic vibration, voice TTS announcement, or notification shade alerts.",
            input_schema={
                "type": "object",
                "properties": {
                    "vibrate_ms": {
                        "type": "integer",
                        "description": "Haptic vibration duration in milliseconds (e.g. 500)",
                    },
                    "speak_text": {
                        "type": "string",
                        "description": "Text to speak aloud via Android Text-to-Speech",
                    },
                    "notification_title": {
                        "type": "string",
                        "description": "Title for Android notification alert",
                    },
                    "notification_content": {
                        "type": "string",
                        "description": "Body message for notification alert",
                    },
                },
                "required": [],
            },
            handler=self._handle_actuate,
        )

        # Tool 7: Sovereign Vault Broker
        self.register_tool(
            name="android_vault_broker",
            description="Proxies an outbound API request through the Android phone's sovereign vault. The phone decrypts the requested service secret (e.g. 'gemini') and forwards the call without exposing credentials to the agent.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full target URL to invoke (e.g. 'https://api.github.com/user')",
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE (default GET)",
                    },
                    "secret_id": {
                        "type": "string",
                        "description": "Registered vault secret name (e.g. 'gemini', 'github_token')",
                    },
                    "header_name": {
                        "type": "string",
                        "description": "Header name for secret injection (default 'Authorization')",
                    },
                    "header_prefix": {
                        "type": "string",
                        "description": "Prefix before secret (default 'Bearer ')",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional HTTP headers",
                    },
                    "json_body": {
                        "type": "object",
                        "description": "JSON body payload for outbound request",
                    },
                    "service": {
                        "type": "string",
                        "description": "Alias for secret_id",
                    },
                    "path": {
                        "type": "string",
                        "description": "Alias for url",
                    },
                    "body": {
                        "type": "object",
                        "description": "Alias for json_body",
                    },
                },
                "required": [],
            },
            handler=self._handle_vault_broker,
        )

    async def _handle_telemetry(self) -> Dict[str, Any]:
        telemetry = await get_node_telemetry()
        return telemetry.dict()

    async def _handle_ping(self, echo: Optional[str] = None) -> Dict[str, Any]:
        return {
            "node_id": settings.NODE_ID,
            "gateway_name": settings.GATEWAY_NAME,
            "pong": True,
            "echo": echo,
            "timestamp": time.time(),
        }

    async def _handle_submit_job(
        self,
        capability: str,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.queue.models import JobCreate
        from app.queue.repository import queue_repo
        job_create = JobCreate(capability=capability, payload=payload or {}, idempotency_key=idempotency_key)
        job, is_new = queue_repo.enqueue(job_create)
        res = job.dict()
        res["_is_new"] = is_new
        return res

    async def _handle_get_job(self, job_id: str) -> Dict[str, Any]:
        from app.queue.repository import queue_repo
        job = queue_repo.get_job(job_id)
        if not job:
            raise KeyError(f"Job '{job_id}' not found")
        return job.dict()

    async def _handle_request_approval(
        self,
        action: str,
        target: str,
        risk_level: str = "HIGH",
        prompt: Optional[str] = None,
        summary: Optional[str] = None,
        requester: str = "agent-mcp",
        timeout_seconds: Optional[int] = None,
        ttl_seconds: int = 120,
        parameters: Optional[Dict[str, Any]] = None,
        sound_alert: bool = True,
        vibrate: bool = True,
    ) -> Dict[str, Any]:
        from app.hitl.manager import approval_manager
        from app.hitl.models import ApprovalTicketCreate, RiskLevel

        ticket_summary = summary or prompt or f"Agent requests permission for '{action}' on '{target}'"
        actual_ttl = ttl_seconds if timeout_seconds is None else timeout_seconds

        try:
            parsed_risk = RiskLevel(risk_level.upper())
        except (ValueError, KeyError, AttributeError):
            parsed_risk = RiskLevel.HIGH

        req = ApprovalTicketCreate(
            action=action,
            target=target,
            parameters=parameters or {},
            requester=requester,
            risk_level=parsed_risk,
            summary=ticket_summary,
            ttl_seconds=max(10, min(3600, actual_ttl)),
            sound_alert=sound_alert,
            vibrate=vibrate,
        )
        ticket = approval_manager.create_ticket(req)
        return ticket.dict()

    async def _handle_actuate(
        self,
        vibrate_ms: Optional[int] = None,
        speak_text: Optional[str] = None,
        notification_title: Optional[str] = None,
        notification_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        import asyncio
        from app.hardware.actuation import vibrate_phone, speak_tts, send_android_notification

        tasks = []
        task_keys = []
        if vibrate_ms:
            tasks.append(vibrate_phone(vibrate_ms))
            task_keys.append("vibrated")
        if speak_text:
            tasks.append(speak_tts(speak_text))
            task_keys.append("spoken")
        if notification_title and notification_content:
            tasks.append(send_android_notification(notification_title, notification_content))
            task_keys.append("notified")

        results = {}
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            for k, r in zip(task_keys, task_results):
                results[k] = bool(r) if not isinstance(r, Exception) else False

        return {"status": "success", "actuated": results}

    async def _handle_vault_broker(
        self,
        url: Optional[str] = None,
        method: str = "GET",
        secret_id: Optional[str] = None,
        header_name: str = "Authorization",
        header_prefix: str = "Bearer ",
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        service: Optional[str] = None,
        path: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.vault.manager import vault_manager
        from app.vault.models import BrokerRequest

        target_url = url or path
        if not target_url:
            raise ValueError("Parameter 'url' (or 'path') is required for vault broker.")

        target_secret = secret_id or service
        target_body = json_body if json_body is not None else body

        req = BrokerRequest(
            url=target_url,
            method=method.upper(),
            secret_id=target_secret,
            header_name=header_name,
            header_prefix=header_prefix,
            headers=headers or {},
            json_body=target_body,
        )
        return await vault_manager.broker_http_request(req)


# Global Tool Registry singleton
tool_registry = ToolRegistry()
