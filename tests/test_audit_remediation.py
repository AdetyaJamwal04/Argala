"""
Unit tests verifying the audit remediation fixes:
1. MCP android_vault_broker and android_request_approval handlers
2. Queue worker vault.broker capability
3. SDK JobRecord and BrokerResponse models
4. SDK store_secret payload formatting
5. SSRF validation on vault broker
6. Nonce pruning in vault manager
"""

import asyncio
import os
import sys
import unittest

# Ensure repo root and eco_system are on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
ECO_PATH = os.path.join(REPO_ROOT, "eco_system")
if ECO_PATH not in sys.path:
    sys.path.insert(0, ECO_PATH)

from app.mcp.tools import tool_registry
from app.hitl.models import RiskLevel
from app.vault.models import BrokerRequest
from app.vault.manager import vault_manager
from eco_system.argala.models import JobRecord, JobStatus, BrokerResponse
from eco_system.argala.client import ArgalaClient


class TestAuditRemediation(unittest.IsolatedAsyncioTestCase):

    def test_mcp_tool_schemas_registered(self):
        """Verify that android_vault_broker and android_request_approval are correctly registered."""
        tools = tool_registry.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("android_vault_broker", tool_names)
        self.assertIn("android_request_approval", tool_names)

        broker_tool = next(t for t in tools if t["name"] == "android_vault_broker")
        props = broker_tool["inputSchema"].get("properties", {})
        self.assertIn("url", props)
        self.assertIn("method", props)
        self.assertIn("secret_id", props)

    async def test_mcp_request_approval_handler(self):
        """Verify _handle_request_approval parses lowercase risk_level and handles prompt/timeout."""
        import json
        mcp_res = await tool_registry.call_tool(
            "android_request_approval",
            {
                "action": "test.deploy",
                "target": "cluster_alpha",
                "risk_level": "medium",
                "prompt": "Please confirm deployment",
                "timeout_seconds": 90,
            }
        )
        self.assertFalse(mcp_res.get("isError"))
        ticket_dict = json.loads(mcp_res["content"][0]["text"])
        self.assertEqual(ticket_dict["action"], "test.deploy")
        self.assertEqual(ticket_dict["target"], "cluster_alpha")
        self.assertEqual(ticket_dict["summary"], "Please confirm deployment")
        self.assertEqual(ticket_dict["risk_level"], "MEDIUM")
        self.assertEqual(ticket_dict["requester"], "agent-mcp")

    async def test_ssrf_protection_vault_broker(self):
        """Verify that vault broker blocks loopback and invalid schemes."""
        with self.assertRaises(ValueError) as ctx:
            await vault_manager.broker_http_request(
                BrokerRequest(url="http://127.0.0.1:8000/v1/health")
            )
        self.assertIn("prohibited", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            await vault_manager.broker_http_request(
                BrokerRequest(url="http://localhost:8000/v1/health")
            )
        self.assertIn("prohibited", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            await vault_manager.broker_http_request(
                BrokerRequest(url="file:///etc/passwd")
            )
        self.assertIn("invalid url scheme", str(ctx.exception).lower())

    def test_sdk_job_record_and_status(self):
        """Verify SDK JobRecord parses gateway payloads with retry_count and RUNNING status."""
        gateway_payload = {
            "id": "job-1234",
            "capability": "test.job",
            "payload": {"key": "val"},
            "status": "RUNNING",
            "retry_count": 1,
            "max_retries": 3,
            "worker_id": "worker-1",
            "created_at": 1700000000.0,
            "updated_at": 1700000010.0,
        }
        record = JobRecord(**gateway_payload)
        self.assertEqual(record.status, JobStatus.RUNNING)
        self.assertEqual(record.retry_count, 1)
        self.assertEqual(record.attempt_count, 1)

    def test_sdk_broker_response_with_headers(self):
        """Verify SDK BrokerResponse correctly accepts headers."""
        resp_data = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"status": "ok"},
        }
        res = BrokerResponse(**resp_data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/json")
        self.assertEqual(res.body, {"status": "ok"})

    def test_sdk_store_secret_payload_format(self):
        """Verify store_secret sends secret_id and plaintext matching gateway model."""
        captured_requests = []

        class MockClient(ArgalaClient):
            def _request(self, method, path, body=None, **kwargs):
                captured_requests.append({"method": method, "path": path, "body": body})
                return {"secret_id": body["secret_id"], "created_at": 1.0, "updated_at": 1.0}

        client = MockClient(base_url="http://mock:8000")
        client.store_secret(secret_id="gemini_key", plaintext="secret123", description="My key")

        self.assertEqual(len(captured_requests), 1)
        req = captured_requests[0]
        self.assertEqual(req["path"], "/v1/vault/secrets")
        self.assertEqual(req["body"]["secret_id"], "gemini_key")
        self.assertEqual(req["body"]["plaintext"], "secret123")
        self.assertEqual(req["body"]["description"], "My key")


    async def test_worker_vault_broker_capability(self):
        """Verify queue worker executes vault.broker capability by awaiting broker_http_request."""
        from unittest.mock import patch
        from app.queue.worker import queue_worker

        mock_resp = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"success": True},
        }
        with patch.object(vault_manager, "broker_http_request", return_value=mock_resp) as mock_broker:
            result = await queue_worker._dispatch_capability(
                "vault.broker",
                {"url": "https://api.example.com/data", "method": "GET"}
            )
            mock_broker.assert_called_once()
            self.assertEqual(result["status"], "brokered")
            self.assertEqual(result["broker_response"]["status_code"], 200)

    def test_nonce_pruning(self):
        """Verify that expired nonces are pruned during action verification."""
        import time
        from app.db.database import db_session
        from app.vault.models import ActionIntent
        from app.vault.crypto import compute_action_hash, sign_action_hash
        from app.config import settings

        import uuid
        expired_nonce = f"expired-{uuid.uuid4()}"
        valid_nonce = f"valid-{uuid.uuid4()}"

        now = time.time()
        # Seed an expired nonce directly into used_nonces
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO used_nonces (nonce, used_at, expires_at) VALUES (?, ?, ?);",
                (expired_nonce, now - 600, now - 300),
            )

        # Issue and verify a new valid action
        intent = ActionIntent(
            action="test.prune",
            target="test.target",
            requester="laptop-agent",
            timestamp=now,
            nonce=valid_nonce,
        )
        token = vault_manager.sign_action(intent, validity_seconds=60)
        res = vault_manager.verify_action(intent, token)
        self.assertTrue(res.valid)

        # Check that expired nonce was pruned from DB
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nonce FROM used_nonces WHERE nonce = ?;", (expired_nonce,))
            self.assertIsNone(cursor.fetchone())


if __name__ == "__main__":
    unittest.main()
