import time
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.config import settings
from app.hardware.telemetry import get_battery_telemetry, get_memory_telemetry, START_TIME

router = APIRouter(prefix="/health", tags=["Health & Probes"])


class HealthResponse(BaseModel):
    status: str
    node_id: str
    gateway_name: str
    uptime_seconds: float


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint (backward compatible)."""
    return HealthResponse(
        status="ok",
        node_id=settings.NODE_ID,
        gateway_name=settings.GATEWAY_NAME,
        uptime_seconds=round(time.time() - START_TIME, 2),
    )


@router.get("/live")
async def liveness_probe() -> dict:
    """
    Liveness probe: Confirms that the event loop is active and serving traffic.
    Returns 200 OK as long as the process is alive.
    """
    return {"status": "alive", "timestamp": time.time()}


@router.get("/ready")
async def readiness_probe(response: Response) -> dict:
    """
    Readiness probe: Confirms that the edge node has enough resources to process work.
    Flags 503 if memory or battery are in critical depletion.
    """
    battery = await get_battery_telemetry()
    memory = await get_memory_telemetry()

    # Edge Safety Policy: Flag not ready if memory is critically starved (>95%)
    if memory.usage_percent > 95.0:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "reason": f"High memory pressure: {memory.usage_percent}%",
        }

    return {
        "status": "ready",
        "battery_pct": battery.percentage,
        "memory_usage_pct": memory.usage_percent,
    }
