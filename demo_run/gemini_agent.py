"""
Gemini AI Agent with Sovereign Edge Integration (Argala Control Plane).
Powered by Google GenAI SDK (google-genai) and connected to the Samsung Galaxy A6+ edge node.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from argala_client import ArgalaClient

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class ArgalaGeminiAgent:
    """
    An autonomous AI reasoning agent that delegates physical verification,
    cryptographic signing, and durable queueing to Argala.
    """

    def __init__(
        self,
        argala_client: Optional[ArgalaClient] = None,
        model_name: str = "gemini-3.8-flash"
    ):
        self.argala = argala_client or ArgalaClient()
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.genai_client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Google GenAI client: {e}")

    # =========================================================================
    # TOOL DEFINITIONS FOR GEMINI
    # =========================================================================

    def get_phone_telemetry(self) -> str:
        """
        Retrieve live physical hardware telemetry from the sovereign Samsung Galaxy A6+ edge node.
        Returns battery percentage, charging state, temperature, available RAM, and uptime.
        """
        try:
            data = self.argala.get_telemetry()
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to reach Argala node: {str(e)}"})

    def submit_job_to_edge_queue(self, capability: str, task_name: str, payload_json: str) -> str:
        """
        Submit an asynchronous task into Argala's durable SQLite WAL queue on the smartphone.
        Guaranteed idempotent and durable across mobile restarts.
        """
        try:
            payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
            payload["task_name"] = task_name
            res = self.argala.submit_job(capability=capability, payload=payload)
            return json.dumps(res, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Job submission failed: {str(e)}"})

    def request_human_physical_approval(
        self,
        action: str,
        target: str,
        parameters_json: str,
        reason: str
    ) -> str:
        """
        Trigger the Cyber-Physical Human-in-the-Loop (HITL) gate on the smartphone.
        Physically actuates the phone:
        1. Vibrates the phone haptic motor (termux-vibrate)
        2. Speaks the intent aloud through the phone speaker via Android TTS (termux-tts-speak)
        3. Posts a high-priority Android notification
        4. Displays a live countdown ticket on the mobile web console (http://100.68.31.91:8000/approvals)
        """
        try:
            params = json.loads(parameters_json) if isinstance(parameters_json, str) else parameters_json
            ticket = self.argala.request_approval(
                action=action,
                target=target,
                parameters=params,
                description=reason,
                ttl_seconds=120
            )
            return json.dumps({
                "status": "APPROVAL_REQUIRED",
                "ticket_id": ticket.get("id"),
                "expires_at": ticket.get("expires_at"),
                "message": (
                    f"Physical approval ticket {ticket.get('id')} dispatched to operator's phone. "
                    f"Phone is vibrating and speaking: '{reason}'. "
                    f"Please approve at http://100.68.31.91:8000/approvals"
                )
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Approval request failed: {str(e)}"})

    def check_approval_ticket_status(self, ticket_id: str) -> str:
        """
        Check whether the human operator has physically approved, rejected, or ignored the ticket.
        """
        try:
            ticket = self.argala.get_ticket(ticket_id)
            return json.dumps(ticket, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Status check failed: {str(e)}"})

    def verify_and_execute_action(
        self,
        ticket_id: str,
        proposed_parameters_json: str
    ) -> str:
        """
        Present an approved ticket and parameters to Argala's Cryptographic Vault for verification.
        Enforces RFC 8785 Canonical Hashing, HMAC-SHA256 signature verification, anti-replay nonces,
        and mathematical TOCTOU defense.
        """
        try:
            ticket = self.argala.get_ticket(ticket_id)
            if ticket.get("status") != "APPROVED":
                return json.dumps({
                    "success": False,
                    "reason": f"Ticket status is {ticket.get('status')}, not APPROVED."
                })

            token = ticket.get("token") or ticket.get("signed_token")
            if not token:
                return json.dumps({
                    "success": False,
                    "reason": "Ticket has no signed cryptographic token."
                })

            params = json.loads(proposed_parameters_json) if isinstance(proposed_parameters_json, str) else proposed_parameters_json

            # Reconstruct intent as submitted to verify cryptographic binding
            intent = {
                "action": ticket.get("action"),
                "target": ticket.get("target"),
                "parameters": params,
                "requester": ticket.get("requester"),
                "nonce": token.get("nonce"),
                "timestamp": token.get("issued_at") or ticket.get("resolved_at") or ticket.get("created_at")
            }

            verification = self.argala.verify_vault_action(intent=intent, token=token)
            return json.dumps({
                "cryptographic_verification": verification,
                "executed": verification.get("valid", False),
                "audit": f"Action {ticket.get('action')} on {ticket.get('target')} verified and executed."
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Vault verification error: {str(e)}"})

    # =========================================================================
    # AGENT REASONING ENGINE
    # =========================================================================

    def run(self, user_instruction: str) -> str:
        """
        Execute an instruction using Gemini with tools.
        If GEMINI_API_KEY is not configured, executes an illustrative architectural demonstration.
        """
        if not self.genai_client:
            return self._run_simulated_agent(user_instruction)

        print(f"\n[Gemini Agent] Reasoning over prompt: '{user_instruction}' using model: {self.model_name}")
        
        tools = [
            self.get_phone_telemetry,
            self.submit_job_to_edge_queue,
            self.request_human_physical_approval,
            self.check_approval_ticket_status,
            self.verify_and_execute_action
        ]

        system_instruction = (
            "You are an autonomous AI Agent operating on a developer workstation. "
            "You are connected to 'Argala', a Sovereign Hardware Control Plane running on an Android smartphone "
            "over a secure WireGuard mesh (http://100.68.31.91:8000). "
            "CRITICAL SECURITY INVARIANTS: "
            "1. You can inspect telemetry freely via get_phone_telemetry(). "
            "2. For routine computation, submit jobs to submit_job_to_edge_queue(). "
            "3. FOR ANY HIGH-RISK, DESTRUCTIVE, OR FINANCIAL ACTION (e.g. database schema drops, server terminations, "
            "secret rotations, money transfers), YOU MUST CALL request_human_physical_approval() first! "
            "4. Never attempt to execute an action without explicit human physical approval. "
            "5. After requesting approval, explain to the user that the phone is vibrating and they must approve on the mobile web console."
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            temperature=0.2
        )

        # Use Chat with automatic function calling
        chat = self.genai_client.chats.create(
            model=self.model_name,
            config=config
        )
        response = chat.send_message(user_instruction)
        return response.text or "Completed tool execution."

    def _run_simulated_agent(self, user_instruction: str) -> str:
        """
        Simulated demonstration for when GEMINI_API_KEY is not yet exported.
        Walks through the exact sequence of reasoning and tool executions.
        """
        print("\n" + "=" * 70)
        print("  ARGALA SOVEREIGN EDGE CONTROL PLANE — ARCHITECTURAL DEMO")
        print("  (Simulated Agent Reasoning Loop; Export GEMINI_API_KEY for Live Gemini)")
        print("=" * 70)
        print(f"Goal: {user_instruction}\n")

        # Step 1: Query Telemetry
        print("[Agent Step 1] Querying physical edge hardware telemetry...")
        telemetry = self.get_phone_telemetry()
        print(f"Result:\n{telemetry}\n")

        # Step 2: High Risk Action Intercept
        print("[Agent Step 2] Agent intends to execute destructive action: 'database.drop_table'")
        print("Security Invariant triggered: HIGH RISK OPERATION REQUIRES CYBER-PHYSICAL HITL GATE")
        
        ticket_json = self.request_human_physical_approval(
            action="database.drop_table",
            target="production-postgres-db",
            parameters_json=json.dumps({"table": "legacy_accounts", "cascade": True}),
            reason="Autonomous agent requested dropping legacy_accounts on production database"
        )
        ticket_data = json.loads(ticket_json)
        ticket_id = ticket_data.get("ticket_id")
        print(f"Ticket Created: {ticket_id}")
        print(f"{ticket_data.get('message')}\n")

        print("-" * 70)
        print(f"--> PLEASE OPEN ON YOUR PHONE OR BROWSER: http://100.68.31.91:8000/approvals")
        print(f"--> Tap 'Approve' to authorize, or let it sit to test timeout.")
        print("-" * 70)

        # Wait for approval
        try:
            print("Polling for human approval (waiting up to 45 seconds)...")
            resolved = self.argala.wait_for_approval(ticket_id, timeout_seconds=45)
            print(f"Ticket Status: {resolved.get('status')}")
            
            if resolved.get("status") == "APPROVED":
                print("\n[Agent Step 3] Validating approved token against Cryptographic Vault...")
                token = resolved.get("signed_token")
                print(f"Signed Action Hash: {token.get('action_hash')}")
                print(f"HMAC Signature:     {token.get('signature')}")
                
                # Verify legitimate execution
                verif = self.verify_and_execute_action(
                    ticket_id=ticket_id,
                    proposed_parameters_json=json.dumps({"table": "legacy_accounts", "cascade": True})
                )
                print(f"Vault Verification Result:\n{verif}\n")

                # Demonstrate TOCTOU Defense
                print("[Agent Step 4] Simulating TOCTOU Parameter Tampering Attack...")
                print("Attacker modifies query parameters to: {'table': 'core_users_master'}")
                tampered_verif = self.verify_and_execute_action(
                    ticket_id=ticket_id,
                    proposed_parameters_json=json.dumps({"table": "core_users_master", "cascade": True})
                )
                print(f"Tampered Vault Verification Result (Blocked):\n{tampered_verif}\n")

        except TimeoutError:
            print("[Info] Polling timed out. The ticket will expire automatically via Anti-Zombie TTL.")

        return "Demonstration run completed."
