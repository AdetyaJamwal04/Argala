"""
Sovereign Python client for the Argala Edge Gateway.
Uses Python's standard library for zero-dependency portability across desktop and Termux environments.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from argala.models import (
    ActuationRequest,
    ActuationResponse,
    ApprovalStatus,
    ApprovalTicket,
    BrokerRequest,
    BrokerResponse,
    JobRecord,
    NodeTelemetry,
)

logger = logging.getLogger(__name__)


# Custom Exceptions
class ArgalaError(Exception):
    """Base exception for all Argala client errors."""
    pass


class ArgalaConnectionError(ArgalaError):
    """Raised when the Argala edge node is unreachable."""
    pass


class ArgalaAuthError(ArgalaError):
    """Raised when authentication or capability scope check fails (401/403)."""
    pass


class ArgalaLockdownError(ArgalaError):
    """Raised when the gateway is under active Emergency Lockdown (HTTP 423)."""
    pass


class ArgalaApprovalDeniedError(ArgalaError):
    """Raised when a human rejects an approval ticket on the mobile screen."""
    pass


class ArgalaTimeoutError(ArgalaError):
    """Raised when an operation or approval ticket times out."""
    pass


class ArgalaClient:
    """
    Client for interacting with the Argala Android Edge Gateway.
    Handles timing-safe API key authentication, capability scoping, and response parsing.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        principal_id: Optional[str] = None,
        default_timeout: float = 15.0,
        base_url: Optional[str] = None,
    ):
        self.endpoint = (endpoint or base_url or os.environ.get("ARGALA_ENDPOINT") or "http://100.68.31.91:8000").rstrip("/")
        self.api_key = api_key or os.environ.get("ARGALA_API_KEY") or "argala-laptop-agent-key"
        self.principal_id = principal_id or os.environ.get("ARGALA_PRINCIPAL_ID") or "laptop-agent"
        self.default_timeout = default_timeout

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Internal HTTP request helper with unified error handling."""
        url = f"{self.endpoint}{path}"
        headers = {
            "User-Agent": "Argala-Python-SDK/0.1.0",
            "X-API-Key": self.api_key,
            "X-Principal-ID": self.principal_id,
            "Content-Type": "application/json",
        }
        if custom_headers:
            headers.update(custom_headers)

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        effective_timeout = timeout or self.default_timeout
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                raw_data = resp.read().decode("utf-8")
                if not raw_data:
                    return {}
                return json.loads(raw_data)
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(raw_err)
                err_detail = err_json.get("detail", raw_err)
            except Exception:
                err_detail = raw_err

            if e.code in (401, 403):
                raise ArgalaAuthError(f"Authentication/Scope Error ({e.code}): {err_detail}") from e
            elif e.code == 423:
                raise ArgalaLockdownError(f"Gateway Locked (423): {err_detail}") from e
            elif e.code == 404:
                raise ArgalaError(f"Resource Not Found (404): {err_detail}") from e
            else:
                raise ArgalaError(f"HTTP Error ({e.code}): {err_detail}") from e
        except urllib.error.URLError as e:
            raise ArgalaConnectionError(
                f"Failed to connect to Argala node at {self.endpoint}: {e.reason}"
            ) from e
        except Exception as e:
            raise ArgalaError(f"Request failed: {str(e)}") from e

    # --- Telemetry & Liveness ---

    def ping(self, echo: Optional[str] = None) -> Dict[str, Any]:
        """Pings the edge node to verify network connectivity and measure latency."""
        start = time.time()
        resp = self._request("GET", "/v1/health")
        resp["_client_latency_ms"] = round((time.time() - start) * 1000, 2)
        return resp

    def get_telemetry(self) -> NodeTelemetry:
        """Retrieves live physical hardware telemetry (battery, RAM, thermals)."""
        data = self._request("GET", "/v1/telemetry")
        return NodeTelemetry(**data)

    # --- Cyber-Physical Actuation ---

    def actuate(
        self,
        vibrate_ms: Optional[int] = None,
        speak_text: Optional[str] = None,
        tts_pitch: float = 1.0,
        tts_rate: float = 1.0,
        notification_title: Optional[str] = None,
        notification_content: Optional[str] = None,
    ) -> ActuationResponse:
        """Directly triggers physical sensory cues on the phone."""
        payload = {
            "vibrate_ms": vibrate_ms,
            "speak_text": speak_text,
            "tts_pitch": tts_pitch,
            "tts_rate": tts_rate,
            "notification_title": notification_title,
            "notification_content": notification_content,
        }
        resp = self._request("POST", "/v1/hardware/actuate", body=payload)
        return ActuationResponse(**resp)

    def vibrate(self, duration_ms: int = 500) -> bool:
        """Triggers phone vibration."""
        res = self.actuate(vibrate_ms=duration_ms)
        return res.vibrated

    def speak(self, text: str) -> bool:
        """Speaks text aloud using the phone's TTS engine."""
        res = self.actuate(speak_text=text)
        return res.spoken

    def notify(self, title: str, content: str) -> bool:
        """Sends an interactive Android notification shade alert."""
        res = self.actuate(notification_title=title, notification_content=content)
        return res.notified

    # --- Cyber-Physical Human-in-the-Loop (HITL) ---

    def request_approval(
        self,
        action: str,
        target: str,
        risk_level: str = "HIGH",
        prompt: Optional[str] = None,
        timeout_seconds: int = 120,
        parameters: Optional[Dict[str, Any]] = None,
        sound_alert: bool = True,
        vibrate: bool = True,
    ) -> ApprovalTicket:
        """
        Creates an approval ticket and alerts the user physically on the phone.
        Returns the pending ticket.
        """
        payload = {
            "action": action,
            "target": target,
            "parameters": parameters or {},
            "requester": self.principal_id,
            "risk_level": risk_level.upper(),
            "summary": prompt or f"Approval required for '{action}' on '{target}'",
            "ttl_seconds": timeout_seconds,
            "sound_alert": sound_alert,
            "vibrate": vibrate,
        }
        resp = self._request("POST", "/v1/approvals/request", body=payload)
        return ApprovalTicket(**resp)

    def get_approval(self, ticket_id: str) -> ApprovalTicket:
        """Fetches the current status of an approval ticket."""
        resp = self._request("GET", f"/v1/approvals/{ticket_id}")
        return ApprovalTicket(**resp)

    def list_approvals(self) -> List[ApprovalTicket]:
        """Lists active and historical approval tickets."""
        resp = self._request("GET", "/v1/approvals")
        tickets = resp.get("tickets", [])
        return [ApprovalTicket(**t) for t in tickets]

    def resolve_approval(self, ticket_id: str, approved: bool, notes: Optional[str] = None) -> ApprovalTicket:
        """Resolves an approval ticket (approve or reject). Requires 'hitl:resolve' scope."""
        payload = {
            "approved": approved,
            "resolved_by": self.principal_id,
            "notes": notes or ("Approved via SDK" if approved else "Rejected via SDK"),
        }
        resp = self._request("POST", f"/v1/approvals/{ticket_id}/resolve", body=payload)
        return ApprovalTicket(**resp)

    def wait_for_approval(
        self,
        ticket_id: str,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None,
        on_poll: Optional[Callable[[ApprovalTicket], None]] = None,
    ) -> ApprovalTicket:
        """
        Polls until the approval ticket is resolved by a human or expires.
        Raises ArgalaApprovalDeniedError if rejected, or ArgalaTimeoutError if expired.
        """
        start_time = time.time()
        effective_timeout = timeout or 65.0

        while time.time() - start_time < effective_timeout:
            ticket = self.get_approval(ticket_id)
            if on_poll:
                on_poll(ticket)

            if ticket.status == ApprovalStatus.APPROVED:
                return ticket
            elif ticket.status == ApprovalStatus.REJECTED:
                raise ArgalaApprovalDeniedError(
                    f"Action '{ticket.action}' on '{ticket.target}' was REJECTED by sovereign operator."
                )
            elif ticket.status == ApprovalStatus.EXPIRED:
                raise ArgalaTimeoutError(
                    f"Approval ticket '{ticket_id}' timed out after {ticket.timeout_seconds}s."
                )

            time.sleep(poll_interval)

        raise ArgalaTimeoutError(f"Exceeded wait timeout of {effective_timeout}s for ticket '{ticket_id}'.")

    # --- Sovereign Cryptographic Vault & Secretless Broker ---

    def broker_request(
        self,
        url: str,
        method: str = "POST",
        secret_id: Optional[str] = "gemini_api_key",
        header_name: str = "x-goog-api-key",
        header_prefix: str = "",
        body: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
    ) -> BrokerResponse:
        """
        Proxies an outbound request through the phone's sovereign vault.
        The phone injects the decrypted secret on-device. The client never holds the secret.
        """
        effective_json = json_body if json_body is not None else body
        broker_req = {
            "url": url,
            "method": method.upper(),
            "secret_id": secret_id,
            "header_name": header_name,
            "header_prefix": header_prefix,
            "headers": headers or {},
            "json_body": effective_json,
        }
        resp = self._request("POST", "/v1/vault/broker", body=broker_req, timeout=timeout)
        return BrokerResponse(**resp)

    def store_secret(
        self,
        secret_id: Optional[str] = None,
        plaintext: Optional[str] = None,
        description: Optional[str] = None,
        # Backward compatibility arguments:
        service: Optional[str] = None,
        secret_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Provisions an encrypted secret in the phone vault. Requires 'vault:secrets' scope."""
        target_id = secret_id or service
        target_value = plaintext or secret_value
        if not target_id or not target_value:
            raise ValueError("Both 'secret_id' and 'plaintext' are required to store a secret.")

        payload = {
            "secret_id": target_id,
            "plaintext": target_value,
            "description": description or f"Key for {target_id}",
        }
        return self._request("POST", "/v1/vault/secrets", body=payload)

    # --- Durable SQLite Queue ---

    def submit_job(
        self,
        capability: str,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> JobRecord:
        """Submits a persistent task to the edge SQLite queue."""
        body = {
            "capability": capability,
            "payload": payload or {},
            "idempotency_key": idempotency_key,
        }
        resp = self._request("POST", "/v1/jobs", body=body)
        return JobRecord(**resp)

    def get_job(self, job_id: str) -> JobRecord:
        """Retrieves current execution status of a queued task."""
        resp = self._request("GET", f"/v1/jobs/{job_id}")
        return JobRecord(**resp)

    def wait_for_job(self, job_id: str, poll_interval: float = 1.0, timeout: float = 60.0) -> JobRecord:
        """Polls until a queued job reaches COMPLETED or FAILED state."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            if job.status in ("COMPLETED", "FAILED", "DEAD_LETTER"):
                return job
            time.sleep(poll_interval)

        raise ArgalaTimeoutError(f"Job '{job_id}' did not complete within {timeout}s.")

    # --- Sovereign Admin & Lockdown ---

    def get_admin_status(self) -> Dict[str, Any]:
        """Retrieves global gateway operational state."""
        return self._request("GET", "/v1/admin")

    def emergency_lockdown(self, reason: str = "Triggered via Argala SDK") -> Dict[str, Any]:
        """Immediately locks the gateway and revokes all agent capability tokens."""
        return self._request("POST", "/v1/admin/lockdown", body={"reason": reason})

    def emergency_unlock(self) -> Dict[str, Any]:
        """Restores normal gateway operation."""
        return self._request("POST", "/v1/admin/unlock")
