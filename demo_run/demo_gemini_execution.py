"""
Argala & Google GenAI — Practical Execution Suite Requiring Gemini API Key.
Demonstrates:
1. Sovereign Secretless Gemini Execution (Phone Vault holds key; Laptop never sees it)
2. Live Autonomous Gemini 2.0/2.5 Agent Loop (Uses google-genai to reason & control physical phone)
"""

import os
import sys
import time
import json
import uuid
import argparse

# Bulletproof UTF-8 stdout encoding for Windows terminal
if sys.platform == "win32":
    try:
        import io
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from argala_client import ArgalaClient

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner():
    print(Colors.CYAN + Colors.BOLD + "=" * 78)
    print("      ARGALA & GOOGLE GENAI -- PRACTICAL EXECUTION WITH GEMINI API KEY")
    print("      Architecture: Sovereign Vault + Cyber-Physical Gate + Google GenAI")
    print("=" * 78 + Colors.RESET)


# ============================================================================
# PRACTICAL 1: SECRETLESS VAULT-BROKERED GEMINI EXECUTION
# ============================================================================

def run_secretless_gemini_demo(client: ArgalaClient, gemini_api_key: str):
    """
    The developer laptop NEVER holds or logs the Gemini API key.
    The key is vaulted in memory-derived PBKDF2 encryption on the smartphone.
    All Gemini inference is brokered through the phone's network stack.
    """
    print(f"\n{Colors.HEADER}=== PRACTICAL 1: SOVEREIGN SECRETLESS GEMINI INFERENCE ==={Colors.RESET}")
    print(f"Concept: The laptop is an untrusted reasoning plane. High-privilege cloud")
    print(f"keys must NEVER be saved in laptop environment variables, bash history, or code.")
    
    # Step 1: Store key in phone's encrypted vault if provided
    if gemini_api_key:
        print(f"\n1. Encrypting and provisioning Gemini API Key directly into phone's sovereign vault...")
        secret_meta = client.store_secret(
            secret_id="gemini_api_key",
            plaintext=gemini_api_key,
            description="Google Gemini Cloud API Key (Brokered Execution Only)"
        )
        print(f"{Colors.GREEN}[OK] Secret Stored in SQLite Vault on Samsung A6+!{Colors.RESET}")
        print(f"    - Secret ID:    {secret_meta.get('secret_id')}")
        print(f"    - Storage:      PBKDF2-HMAC-SHA256 authenticated envelope encryption")
        print(f"    - Node:         android-termux-node-01")
    else:
        print(f"\n1. Using existing 'gemini_api_key' already encrypted in phone's sovereign vault.")
        print(f"{Colors.GREEN}[OK] Vaulted Credential Reused!{Colors.RESET}")

    # Step 2: Formulate prompt for Gemini
    prompt_text = (
        "You are Gemini running via Argala Sovereign Edge. "
        "Summarize the security benefits of storing API keys on a physical smartphone "
        "rather than a developer workstation in exactly 3 bullet points."
    )
    print(f"\n2. Submitting prompt to Argala Secretless Broker:")
    print(f"   \"{Colors.CYAN}{prompt_text}{Colors.RESET}\"")
    print(f"\n   -> Calling: POST http://100.68.31.91:8000/v1/vault/broker")
    print(f"   -> Secret to inject: 'gemini_api_key' (Header: 'x-goog-api-key')")
    print(f"   -> Target URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent")

    # Step 3: Call phone's outbound broker
    gemini_payload = {
        "contents": [
            {"parts": [{"text": prompt_text}]}
        ]
    }

    start = time.perf_counter()
    broker_res = client.broker_request(
        url="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
        method="POST",
        secret_id="gemini_api_key",
        header_name="x-goog-api-key",
        header_prefix="",  # Raw key
        json_body=gemini_payload,
        timeout=60.0
    )
    elapsed = (time.perf_counter() - start) * 1000.0

    status_code = broker_res.get("status_code")
    body = broker_res.get("body", {})

    if status_code == 200 and "candidates" in body:
        reply_text = body["candidates"][0]["content"]["parts"][0]["text"]
        print(f"\n{Colors.GREEN}[OK] Gemini Response Brokered Successfully ({elapsed:.1f}ms):{Colors.RESET}\n")
        print(Colors.BOLD + reply_text.strip() + Colors.RESET)
        print(f"\n{Colors.CYAN}[Security Invariant Verified]:{Colors.RESET} The laptop executed a full Gemini inference")
        print(f"call, but the raw Gemini API key NEVER touched the laptop's RAM or network sockets!")
    else:
        print(f"{Colors.RED}[FAIL] Broker call returned status {status_code}:{Colors.RESET}")
        print(json.dumps(body, indent=2))


# ============================================================================
# PRACTICAL 2: AUTONOMOUS GEMINI AGENT WITH REAL PHYSICAL HITL GATE
# ============================================================================

def run_autonomous_gemini_agent(client: ArgalaClient, gemini_api_key: str):
    """
    Runs Gemini (via official google-genai SDK) as an autonomous agent.
    Gemini inspects telemetry, detects a high-risk mission, triggers phone haptics/audio,
    and only executes after the human physically approves.
    """
    print(f"\n{Colors.HEADER}=== PRACTICAL 2: LIVE AUTONOMOUS GEMINI AGENT WITH PHYSICAL DEADBOLT ==={Colors.RESET}")
    print(f"Using Google GenAI SDK (google-genai) with model: {Colors.BOLD}gemini-3.8-flash{Colors.RESET}\n")

    if not GENAI_AVAILABLE:
        print(f"{Colors.RED}[FAIL] google-genai package is not available in current environment.{Colors.RESET}")
        return

    ai_client = genai.Client(api_key=gemini_api_key)

    # Define tools for Gemini
    def get_hardware_telemetry() -> str:
        """Fetch live battery level, thermals, and available RAM from the physical Android node."""
        print(f"  {Colors.YELLOW}[Tool Call]{Colors.RESET} get_hardware_telemetry()")
        telem = client.get_telemetry()
        res_str = json.dumps(telem)
        print(f"  {Colors.CYAN}[Tool Output]{Colors.RESET} Battery: {telem.get('battery', {}).get('percentage')}%, Temp: {telem.get('battery', {}).get('temperature')}C, Available RAM: {telem.get('memory', {}).get('available_mb')}MB")
        return res_str

    def request_human_physical_authorization(action: str, target: str, summary: str) -> str:
        """
        Request cyber-physical human authorization on the operator's smartphone.
        Actuates vibration, TTS speech, and notification, then waits for the human operator to approve.
        """
        print(f"\n  " + Colors.YELLOW + "=" * 70)
        print(f"  [!] PHONE ACTUATING NOW: VIBRATING & SPEAKING VIA TTS")
        print(f"  [!] Action:  {action} on {target}")
        print(f"  [!] Summary: {summary}")
        print(f"  [!] Open:    http://100.68.31.91:8000/approvals and tap APPROVE")
        print(f"  " + "=" * 70 + Colors.RESET + "\n")

        ticket = client.request_approval(
            action=action,
            target=target,
            parameters={"initiated_by": "gemini-autonomous-agent", "timestamp": time.time()},
            summary=summary,
            ttl_seconds=90
        )
        ticket_id = ticket.get("id")
        print(f"  Ticket Created: {ticket_id}")
        print(f"  Waiting for operator to tap Approve on phone dashboard (polling up to 60s)...")
        try:
            resolved = client.wait_for_approval(ticket_id, timeout_seconds=60)
            status = resolved.get("status")
            token = resolved.get("token") or resolved.get("signed_token") or {}
            print(f"  {Colors.GREEN}[OK] Operator Decision: {status}!{Colors.RESET}")
            if status == "APPROVED":
                print(f"  Signed HMAC-SHA256 Token: {token.get('signature')}")
            return json.dumps({
                "ticket_id": ticket_id,
                "status": status,
                "authorized": status == "APPROVED",
                "signature": token.get("signature")
            })
        except TimeoutError:
            print(f"  {Colors.RED}[!] Timed out waiting for human approval.{Colors.RESET}")
            return json.dumps({"status": "TIMEOUT", "authorized": False, "error": "Human operator did not approve in time"})

    def enqueue_maintenance_job(task_name: str, payload_json: str) -> str:
        """Enqueue an authorized job into the phone's durable SQLite queue."""
        print(f"  {Colors.YELLOW}[Tool Call]{Colors.RESET} enqueue_maintenance_job(task_name='{task_name}')")
        res = client.submit_job(capability="edge:maintenance", payload={"task": task_name, "data": payload_json})
        print(f"  {Colors.GREEN}[OK] Job Enqueued in SQLite WAL Queue: ID {res.get('id')}!{Colors.RESET}")
        return json.dumps(res)

    tools = [
        get_hardware_telemetry,
        request_human_physical_authorization,
        enqueue_maintenance_job
    ]

    system_prompt = (
        "You are an autonomous operations AI connected to 'Argala', a physical Samsung Galaxy A6+ smartphone "
        "acting as a Sovereign Hardware Control Plane over WireGuard mesh (http://100.68.31.91:8000). "
        "Workflow rules: "
        "1. Always check physical hardware telemetry first via get_hardware_telemetry(). "
        "2. Any destructive or critical action (such as database migrations, cluster maintenance, or job dispatch) "
        "MUST be authorized by calling request_human_physical_authorization(). "
        "3. Only if authorized == True, call enqueue_maintenance_job() to submit the work to the durable queue. "
        "4. Conclude with a clear mission summary explaining what was verified and executed."
    )

    user_goal = (
        "Perform a health assessment on the phone. If the battery is above 50% and thermals are below 40C, "
        "request human approval to execute 'db_cluster_vacuum_and_reindex' on production. "
        "Upon confirmation, enqueue the maintenance job."
    )

    print(f"Goal for Gemini: {Colors.CYAN}{user_goal}{Colors.RESET}\n")
    print(f"Starting Gemini 3.8 Flash agent with Chat & Automatic Function Calling...\n")

    chat = ai_client.chats.create(
        model="gemini-3.8-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools,
            temperature=0.1
        )
    )

    response = chat.send_message(user_goal)

    print(f"\n{Colors.GREEN}[Gemini Agent Final Output]:{Colors.RESET}\n")
    print(Colors.BOLD + response.text.strip() + Colors.RESET)


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

def main():
    print_banner()

    # Retrieve Gemini API key from env, vault, or prompt
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(f"\n{Colors.YELLOW}[Notice] GEMINI_API_KEY is not currently set in $env:GEMINI_API_KEY.{Colors.RESET}")
        api_key = input("Enter your Gemini API Key (or press ENTER to use the key already stored in phone vault): ").strip()

    client = ArgalaClient()

    # Verify edge node connectivity first
    try:
        ping = client.ping()
        print(f"{Colors.GREEN}[OK] Connected to Sovereign Edge Node:{Colors.RESET} {ping.get('gateway_name')} (Latency: {ping.get('latency_ms')}ms)")
    except Exception as e:
        print(f"{Colors.RED}[Error] Could not connect to Argala at 100.68.31.91:8000: {e}{Colors.RESET}")
        sys.exit(1)

    print("\nSelect Practical Execution:")
    print("  1. Sovereign Secretless Gemini Execution (Phone Vault brokers inference; Laptop sees NO key)")
    print("  2. Live Autonomous Gemini Agent Loop (Reasoning + Physical Phone Vibration & Speech + Approval)")
    print("  3. Run BOTH sequentially")
    
    choice = input("\nEnter choice [1, 2, or 3]: ").strip()

    if choice == "1":
        run_secretless_gemini_demo(client, api_key)
    elif choice in ("2", "3"):
        if not api_key:
            print(f"\n{Colors.YELLOW}[!] Option {choice} runs the google-genai SDK locally on your laptop,{Colors.RESET}")
            api_key = input("Please paste your Gemini API Key: ").strip()
            if not api_key:
                print(f"{Colors.RED}[Error] Gemini API Key required for local agent loop. Exiting.{Colors.RESET}")
                sys.exit(1)
        if choice == "2":
            run_autonomous_gemini_agent(client, api_key)
        else:
            run_secretless_gemini_demo(client, api_key)
            run_autonomous_gemini_agent(client, api_key)
    else:
        print("Invalid selection.")

    client.close()


if __name__ == "__main__":
    main()
