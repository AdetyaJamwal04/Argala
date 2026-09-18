import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import require_scope
from app.core.identity import Principal
from app.hardware.actuation import vibrate_phone, speak_tts, send_android_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hardware", tags=["Hardware Actuation"])


class ActuationRequest(BaseModel):
    """Payload for triggering physical hardware actuation on the Android phone."""
    vibrate_ms: Optional[int] = Field(None, ge=50, le=5000, description="Haptic vibration duration in milliseconds")
    speak_text: Optional[str] = Field(None, max_length=500, description="Text to speak aloud via Android TTS engine")
    tts_pitch: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="TTS pitch multiplier")
    tts_rate: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="TTS speaking speed multiplier")
    notification_title: Optional[str] = Field(None, max_length=100, description="Title for notification shade alert")
    notification_content: Optional[str] = Field(None, max_length=500, description="Body content for notification alert")
    notification_id: Optional[str] = Field("argala_custom_alert", description="Notification shade group/id")


class ActuationResponse(BaseModel):
    status: str = "success"
    vibrated: bool = False
    spoken: bool = False
    notified: bool = False


@router.post("/actuate", response_model=ActuationResponse, status_code=status.HTTP_200_OK)
async def actuate_hardware(
    payload: ActuationRequest,
    principal: Principal = Depends(require_scope("hardware:actuate")),
):
    """
    Directly triggers cyber-physical actuation (haptic vibration, voice TTS, notification)
    on the physical Android device. Scoped under 'hardware:actuate'.
    """
    logger.info("Principal '%s' requested hardware actuation: %s", principal.id, payload.dict(exclude_none=True))

    tasks = []
    task_keys = []

    if payload.vibrate_ms:
        tasks.append(vibrate_phone(payload.vibrate_ms))
        task_keys.append("vibrated")

    if payload.speak_text:
        tasks.append(speak_tts(payload.speak_text, pitch=payload.tts_pitch, rate=payload.tts_rate))
        task_keys.append("spoken")

    if payload.notification_title and payload.notification_content:
        tasks.append(send_android_notification(
            title=payload.notification_title,
            content=payload.notification_content,
            notification_id=payload.notification_id,
        ))
        task_keys.append("notified")

    results = {}
    if tasks:
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for key, res in zip(task_keys, task_results):
            results[key] = bool(res) if not isinstance(res, Exception) else False

    return ActuationResponse(
        status="success",
        vibrated=results.get("vibrated", False),
        spoken=results.get("spoken", False),
        notified=results.get("notified", False),
    )
