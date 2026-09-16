from fastapi import APIRouter, Depends

from app.api.deps import require_scope
from app.hardware.telemetry import NodeTelemetry, get_node_telemetry

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("", response_model=NodeTelemetry, dependencies=[Depends(require_scope("telemetry:read"))])
async def read_telemetry() -> NodeTelemetry:
    """
    Returns live hardware telemetry (battery, memory, uptime, android runtime flag).
    Protected by Zero-Trust capability scope 'telemetry:read' to prevent unauthorized environmental reconnaissance.
    """
    return await get_node_telemetry()
