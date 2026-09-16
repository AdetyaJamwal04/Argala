import asyncio
import logging
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


async def vibrate_phone(duration_ms: int = 500) -> bool:
    """
    Triggers physical haptic vibration on the Android phone.
    Non-blocking async subprocess call to termux-vibrate.
    """
    binary = shutil.which("termux-vibrate")
    if not binary:
        logger.debug("termux-vibrate not available in environment")
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            "-d", str(duration_ms),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=2.0)
        return proc.returncode == 0
    except Exception as e:
        logger.warning("Failed to trigger phone vibration: %s", e)
        return False


async def speak_tts(text: str, pitch: float = 1.0, rate: float = 1.0) -> bool:
    """
    Speaks text aloud using Android's native Text-to-Speech (TTS) engine.
    Non-blocking async subprocess call to termux-tts-speak.
    """
    binary = shutil.which("termux-tts-speak")
    if not binary:
        logger.debug("termux-tts-speak not available in environment")
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            "-p", str(pitch),
            "-r", str(rate),
            text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5.0)
        return proc.returncode == 0
    except Exception as e:
        logger.warning("Failed to trigger TTS speech: %s", e)
        return False


async def send_android_notification(
    title: str,
    content: str,
    notification_id: str = "argala_approval",
    priority: str = "high",
) -> bool:
    """
    Creates an interactive notification in Android's notification shade.
    Non-blocking async subprocess call to termux-notification.
    """
    binary = shutil.which("termux-notification")
    if not binary:
        logger.debug("termux-notification not available in environment")
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--id", notification_id,
            "--title", title,
            "--content", content,
            "--priority", priority,
            "--vibrate", "400,200,400",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=3.0)
        return proc.returncode == 0
    except Exception as e:
        logger.warning("Failed to send Android notification: %s", e)
        return False


async def emergency_lockdown_alert():
    """Triggers physical alerts across haptics, voice, and notification for emergency lockdown."""
    await asyncio.gather(
        vibrate_phone(1200),
        speak_tts("Warning! Emergency lockdown initiated. All agent capabilities revoked."),
        send_android_notification(
            title="🚨 EMERGENCY LOCKDOWN",
            content="Agent access terminated and sovereign vault locked.",
            notification_id="argala_lockdown",
            priority="max",
        ),
        return_exceptions=True,
    )


async def system_restored_alert():
    """Triggers physical alert when administrative unlock restores the gateway."""
    await asyncio.gather(
        vibrate_phone(300),
        speak_tts("Emergency lockdown disarmed. Sovereign control plane restored."),
        send_android_notification(
            title="🛡️ Argala Restored",
            content="Normal operation restored by administrator.",
            notification_id="argala_lockdown",
            priority="high",
        ),
        return_exceptions=True,
    )


