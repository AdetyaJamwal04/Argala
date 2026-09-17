"""
Argala Client — Sovereign Edge Control Plane API Client
Communicates securely over Tailscale WireGuard mesh with the Samsung Galaxy A6+ edge node.
"""

import time
import uuid
import httpx
from typing import Any, Dict, Optional


class ArgalaClient:
    def __init__(
        self,
        base_url: str = "http://100.68.31.91:8000",
        api_key: str = "argala-dev-key-change-me",
        principal_id: str = "laptop-agent",
        timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.principal_id = principal_id
        self.headers = {
            "X-API-Key": self.api_key,
            "X-Principal-ID": self.principal_id,
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers, timeout=timeout)

    def ping(self) -> Dict[str, Any]:
        """Ping the Argala node and measure roundtrip latency."""
        start = time.perf_counter()
        resp = self.client.get("/v1/health")
        latency_ms = (time.perf_counter() - start) * 1000.0
        resp.raise_for_status()
        data = resp.json()
        data["latency_ms"] = round(latency_ms, 2)
        return data

    def get_telemetry(self) -> Dict[str, Any]:
        """Fetch live hardware telemetry (battery, RAM, thermal, uptime) from the physical phone."""
        resp = self.client.get("/v1/telemetry")
        resp.raise_for_status()
        return resp.json()

    def get_admin_status(self) -> Dict[str, Any]:
        """Fetch admin gateway status, lockdown state, and registered principals."""
        resp = self.client.get("/v1/admin/status")
        resp.raise_for_status()
        return resp.json()

    def submit_job(self, capability: str, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Submit an asynchronous task into Argala's durable SQLite WAL queue."""
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())
            
        data = {
            "capability": capability,
            "payload": payload,
            "idempotency_key": idempotency_key
        }
        resp = self.client.post("/v1/jobs", json=data)
        resp.raise_for_status()
        res = resp.json()
        res["http_status"] = resp.status_code
        res["deduplicated"] = (resp.status_code == 200)
        return res

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Check status of a queued task."""
        resp = self.client.get(f"/v1/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()

    def request_approval(
        self,
        action: str,
        target: str,
        parameters: Dict[str, Any],
        summary: Optional[str] = None,
        description: Optional[str] = None,
        ttl_seconds: int = 120,
        risk_level: str = "HIGH",
        sound_alert: bool = True,
        vibrate: bool = True
    ) -> Dict[str, Any]:
        """
        Request physical human verification.
        Actuates Samsung Galaxy A6+ physical hardware:
        - Haptic vibration pulse via termux-vibrate
        - Text-to-Speech audio announcement via termux-tts-speak
        - High-priority push notification via termux-notification
        - Live ticket on mobile web console (http://100.68.31.91:8000/approvals)
        """
        summary_text = summary or description or f"Approval required for {action} on {target}"
        payload = {
            "action": action,
            "target": target,
            "parameters": parameters,
            "requester": self.principal_id,
            "summary": summary_text,
            "ttl_seconds": ttl_seconds,
            "risk_level": risk_level,
            "sound_alert": sound_alert,
            "vibrate": vibrate
        }
        resp = self.client.post("/v1/approvals/request", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Check status of an approval ticket."""
        resp = self.client.get(f"/v1/approvals/{ticket_id}")
        resp.raise_for_status()
        return resp.json()

    def wait_for_approval(self, ticket_id: str, timeout_seconds: int = 90, poll_interval: float = 2.0) -> Dict[str, Any]:
        """Poll until the human operator resolves the ticket on their phone dashboard."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            ticket = self.get_ticket(ticket_id)
            status = ticket.get("status")
            if status in ("APPROVED", "REJECTED", "EXPIRED"):
                return ticket
            time.sleep(poll_interval)
        raise TimeoutError(f"Timed out waiting {timeout_seconds}s for human approval on ticket {ticket_id}")

    def verify_vault_action(self, intent: Dict[str, Any], token: Dict[str, Any]) -> Dict[str, Any]:
        """Verify an approved signed token against Argala's Cryptographic Vault."""
        payload = {
            "intent": intent,
            "token": token
        }
        resp = self.client.post("/v1/vault/verify", json=payload)
        resp.raise_for_status()
        return resp.json()

    def store_secret(self, secret_id: str, plaintext: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt and store a credential in the phone's sovereign vault."""
        payload = {
            "secret_id": secret_id,
            "plaintext": plaintext,
            "description": description or f"Encrypted secret {secret_id}"
        }
        headers = dict(self.headers)
        headers["X-Principal-ID"] = "admin-console"
        resp = self.client.post("/v1/vault/secrets", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def broker_request(
        self,
        url: str,
        method: str = "POST",
        secret_id: Optional[str] = None,
        header_name: str = "Authorization",
        header_prefix: str = "Bearer ",
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Execute an outbound HTTP request from the phone, securely injecting the requested vault credential.
        The calling agent receives the API output, never the raw credential.
        """
        payload = {
            "url": url,
            "method": method,
            "secret_id": secret_id,
            "header_name": header_name,
            "header_prefix": header_prefix,
            "json_body": json_body,
            "headers": headers or {}
        }
        broker_headers = dict(self.headers)
        broker_headers["X-Principal-ID"] = "admin-console"
        resp = self.client.post("/v1/vault/broker", json=payload, headers=broker_headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self.client.close()

