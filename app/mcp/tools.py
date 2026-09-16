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


# Global Tool Registry singleton
tool_registry = ToolRegistry()
