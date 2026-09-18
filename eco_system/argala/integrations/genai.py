"""
Google GenAI (Gemini) SDK integration for Argala.
Provides auto-wired toolsets allowing Gemini models (e.g. gemini-3.8-flash)
to read edge telemetry, trigger physical haptics/voice, request physical human approvals,
and enqueue durable background jobs.
"""

from typing import Any, Callable, Dict, List, Optional
from argala.client import ArgalaClient


def create_argala_gemini_tools(client: Optional[ArgalaClient] = None) -> List[Callable]:
    """
    Returns a list of Python callable functions with type annotations and docstrings
    ready to be passed directly to the `tools` parameter of `google-genai` client:

        from google import genai
        from google.genai import types
        from argala.integrations.genai import create_argala_gemini_tools

        ai_client = genai.Client(...)
        tools = create_argala_gemini_tools()

        chat = ai_client.chats.create(
            model="gemini-3.8-flash",
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.2,
            )
        )
        response = chat.send_message("Check node battery and announce status aloud")
    """
    c = client or ArgalaClient()

    def get_phone_telemetry() -> Dict[str, Any]:
        """
        Retrieves real-time physical hardware sensors from the Android edge node.
        Returns battery percentage, charging state, battery temperature in Celsius, and RAM usage.
        """
        telemetry = c.get_telemetry()
        return telemetry.dict()

    def actuate_phone_hardware(
        vibrate_ms: Optional[int] = None,
        speak_text: Optional[str] = None,
        notification_title: Optional[str] = None,
        notification_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Triggers physical sensory actuation on the Android phone.
        Use this to provide tactile feedback (vibrate), speak aloud using Text-to-Speech (TTS),
        or post alerts to Android's notification shade.

        Args:
            vibrate_ms: Vibration duration in milliseconds (e.g. 500 for half a second).
            speak_text: Text sentence for the phone to speak out loud.
            notification_title: Title for notification shade card.
            notification_content: Detailed message for notification shade.
        """
        res = c.actuate(
            vibrate_ms=vibrate_ms,
            speak_text=speak_text,
            notification_title=notification_title,
            notification_content=notification_content,
        )
        return res.dict()

    def request_human_approval(
        action: str,
        target: str,
        risk_level: str = "high",
        prompt: str = "Please confirm this operation",
    ) -> Dict[str, Any]:
        """
        Pauses and gates a high-risk action behind physical human approval on the phone.
        Triggers phone vibration and voice prompt, displaying an interactive approval card.
        Blocks until the human physically approves or rejects on the mobile screen.

        Args:
            action: Dangerous action name (e.g. 'database.drop_table', 'cloud.terminate_vm').
            target: The resource or system target (e.g. 'prod_cluster_db').
            risk_level: 'low', 'medium', 'high', or 'critical'.
            prompt: Clear question/warning explaining why permission is required.
        """
        ticket = c.request_approval(
            action=action,
            target=target,
            risk_level=risk_level,
            prompt=prompt,
            timeout_seconds=60,
        )
        try:
            resolved = c.wait_for_approval(ticket.id, timeout=65.0)
            return {
                "ticket_id": resolved.id,
                "status": resolved.status.value,
                "approved": True,
                "signed_token": resolved.token,
            }
        except Exception as e:
            return {
                "ticket_id": ticket.id,
                "status": "REJECTED_OR_TIMEOUT",
                "approved": False,
                "error": str(e),
            }

    def enqueue_background_job(
        capability: str,
        payload_json_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submits a persistent task to the edge node's SQLite durable queue.
        The phone executes the task asynchronously in the background.

        Args:
            capability: Task type, e.g. 'telemetry.snapshot', 'hardware.actuate', 'system.echo'.
            payload_json_str: Optional JSON string of task arguments.
        """
        import json
        payload = json.loads(payload_json_str) if payload_json_str else {}
        job = c.submit_job(capability=capability, payload=payload)
        return {
            "job_id": job.id,
            "capability": job.capability,
            "status": job.status.value,
        }

    return [
        get_phone_telemetry,
        actuate_phone_hardware,
        request_human_approval,
        enqueue_background_job,
    ]
