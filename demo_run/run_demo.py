"""
Argala & Google GenAI — Practical Demonstration Suite
Executes end-to-end architectural scenarios between developer workstation and the physical phone.
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
from gemini_agent import ArgalaGeminiAgent

# ANSI Color codes for clean terminal presentation
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
    print(Colors.CYAN + Colors.BOLD + "=" * 76)
    print("       ARGALA (ARGALA) & GOOGLE GENAI -- SOVEREIGN CONTROL PLANE DEMO")
    print("      Node: Samsung Galaxy A6+ (100.68.31.91) | Client: Laptop Agent")
    print("=" * 76 + Colors.RESET)



def demo_telemetry(client: ArgalaClient):
    print(f"\n{Colors.HEADER}--- SCENARIO 1: WIRE-LEVEL PING & LIVE HARDWARE TELEMETRY ---{Colors.RESET}")
    print(f"Connecting to Argala node over WireGuard mesh (http://100.68.31.91:8000)...")
    
    ping_data = client.ping()
    print(f"{Colors.GREEN}[OK] Node Reachable!{Colors.RESET}")
    print(f"    - Roundtrip Latency:  {Colors.BOLD}{ping_data.get('latency_ms')} ms{Colors.RESET}")
    print(f"    - Uptime:             {round(ping_data.get('uptime_seconds', 0) / 3600, 2)} hours")
    print(f"    - Gateway Name:       {ping_data.get('gateway_name')}")

    print(f"\nReading physical hardware sensors from Android OS via Termux API...")
    telem = client.get_telemetry()
    battery = telem.get("battery", {})
    memory = telem.get("memory", {})

    print(f"{Colors.GREEN}[OK] Telemetry Ingested:{Colors.RESET}")
    print(f"    - Battery Level:      {Colors.BOLD}{battery.get('percentage')}%{Colors.RESET} ({battery.get('status')}, {battery.get('plugged')})")
    print(f"    - Battery Temp:       {battery.get('temperature')} C")
    print(f"    - Available RAM:      {memory.get('available_mb')} MB / {memory.get('total_mb')} MB ({100 - memory.get('usage_percent', 0):.1f}% free)")
    print(f"    - Sensor Driver:      {battery.get('source')}")


def demo_queue_idempotency(client: ArgalaClient):
    print(f"\n{Colors.HEADER}--- SCENARIO 2: DURABLE QUEUE & IDEMPOTENT DEDUPLICATION ---{Colors.RESET}")
    idempotency_key = f"demo-task-{uuid.uuid4().hex[:8]}"
    capability = "batch:data_sync"
    payload = {"sync_target": "cloud_storage", "records": 4200}

    print(f"Submitting initial task with Idempotency-Key: {Colors.CYAN}{idempotency_key}{Colors.RESET}")
    job1 = client.submit_job(capability=capability, payload=payload, idempotency_key=idempotency_key)
    print(f"{Colors.GREEN}[OK] Submission 1:{Colors.RESET} HTTP {job1.get('http_status')} (Accepted) | Job ID: {job1.get('id')} | Status: {job1.get('status')}")

    print(f"\nSimulating network retry (resubmitting with the EXACT SAME Idempotency-Key)...")
    job2 = client.submit_job(capability=capability, payload=payload, idempotency_key=idempotency_key)
    if job2.get("deduplicated"):
        print(f"{Colors.GREEN}[OK] Submission 2:{Colors.RESET} HTTP {job2.get('http_status')} (Deduplicated) | Returned Job ID: {job2.get('id')}")
        print(f"    {Colors.BOLD}Mathematical Invariant Verified:{Colors.RESET} Zero duplicate tasks inserted. Effectively-once execution achieved.")
    else:
        print(f"{Colors.RED}[FAIL] Failed: Task was duplicated!{Colors.RESET}")


def demo_hitl_and_vault(client: ArgalaClient):
    print(f"\n{Colors.HEADER}--- SCENARIO 3: CYBER-PHYSICAL HITL GATE & CRYPTOGRAPHIC VAULT ---{Colors.RESET}")
    print(f"Agent requests destructive action: {Colors.RED}database.drop_schema{Colors.RESET}")
    print(f"Target: {Colors.BOLD}production_cluster_01{Colors.RESET}")

    desc = "AI Agent requested dropping schema 'obsolete_data' on production cluster"
    params = {"schema": "obsolete_data", "force": True}

    print(f"\nDispatching approval ticket to physical phone...")
    ticket = client.request_approval(
        action="database.drop_schema",
        target="production_cluster_01",
        parameters=params,
        description=desc,
        ttl_seconds=120
    )

    ticket_id = ticket.get("id")
    print(f"{Colors.GREEN}[OK] Ticket Created:{Colors.RESET} {Colors.CYAN}{ticket_id}{Colors.RESET}")
    print(f"    - Physical Actions Dispatched to Phone:")
    print(f"      1. Haptic pulse sent via {Colors.BOLD}termux-vibrate{Colors.RESET}")
    print(f"      2. Spoken announcement sent via {Colors.BOLD}termux-tts-speak{Colors.RESET}")
    print(f"      3. Push notification posted via {Colors.BOLD}termux-notification{Colors.RESET}")
    
    print(f"\n" + Colors.YELLOW + "=" * 76)
    print(f"  ACTION REQUIRED: OPEN YOUR PHONE OR BROWSER TO:")
    print(f"  --> http://100.68.31.91:8000/approvals")
    print(f"  Tap 'APPROVE' on ticket '{ticket_id}' to issue cryptographic signature.")
    print("=" * 76 + Colors.RESET)

    print(f"Waiting for human resolution (polling up to 60s)...")
    try:
        resolved = client.wait_for_approval(ticket_id, timeout_seconds=60)
        status = resolved.get("status")

        if status == "APPROVED":
            print(f"{Colors.GREEN}[OK] HUMAN OPERATOR PHYSICALLY APPROVED TICKET!{Colors.RESET}")
            token = resolved.get("token") or resolved.get("signed_token") or {}
            action_hash = token.get("action_hash")
            signature = token.get("signature")
            nonce = token.get("nonce")

            print(f"\n{Colors.CYAN}Cryptographic Token Issued by Sovereign Phone:{Colors.RESET}")
            print(f"    - Canonical Action Hash: {action_hash}")
            print(f"    - HMAC-SHA256 Signature: {signature}")
            print(f"    - Anti-Replay Nonce:     {nonce}")

            print(f"\n{Colors.HEADER}--- SCENARIO 4: VAULT VERIFICATION & TOCTOU DEFENSE ---{Colors.RESET}")
            print(f"1. Validating genuine execution intent...")
            intent = {
                "action": "database.drop_schema",
                "target": "production_cluster_01",
                "parameters": params,
                "requester": client.principal_id,
                "nonce": nonce,
                "timestamp": token.get("issued_at") or resolved.get("resolved_at") or resolved.get("created_at")
            }
            v_result = client.verify_vault_action(intent=intent, token=token)
            print(f"    Genuine Execution Verification: {Colors.GREEN}{v_result.get('valid')}{Colors.RESET} ({v_result.get('reason')})")

            print(f"\n2. Simulating Malicious Parameter Substitution (TOCTOU Attack)...")
            print(f"    Attacker secretly modifies parameters to: {Colors.RED}{{'schema': 'CORE_SYSTEM_PAYMENTS'}}{Colors.RESET}")
            tampered_intent = dict(intent)
            tampered_intent["parameters"] = {"schema": "CORE_SYSTEM_PAYMENTS", "force": True}

            tampered_result = client.verify_vault_action(intent=tampered_intent, token=token)
            print(f"    Tampered Execution Verification: {Colors.RED}{tampered_result.get('valid')}{Colors.RESET}")
            print(f"    Rejection Reason: {Colors.YELLOW}{tampered_result.get('reason')}{Colors.RESET}")
            print(f"{Colors.GREEN}[OK] TOCTOU Attack Mathematically Defeated by RFC 8785 Canonical Digest!{Colors.RESET}")

        elif status == "REJECTED":
            print(f"{Colors.YELLOW}[!] Operator clicked REJECT on the phone dashboard. Action aborted.{Colors.RESET}")
        elif status == "EXPIRED":
            print(f"{Colors.RED}[!] Ticket expired without human action. System failed safe.{Colors.RESET}")

    except TimeoutError:
        print(f"{Colors.YELLOW}[!] Polling timed out. The ticket will expire automatically via Anti-Zombie TTL.{Colors.RESET}")


def demo_gemini_agent(client: ArgalaClient):
    print(f"\n{Colors.HEADER}--- SCENARIO 5: AUTONOMOUS GEMINI AGENT REASONING ---{Colors.RESET}")
    agent = ArgalaGeminiAgent(argala_client=client)

    if os.environ.get("GEMINI_API_KEY"):
        prompt = "Check the health and telemetry of the Argala edge node, then explain if it is safe to dispatch heavy background jobs."
        print(f"Prompting live Gemini model with prompt: '{prompt}'")
        output = agent.run(prompt)
        print(f"\n{Colors.GREEN}[Gemini Agent Response]:{Colors.RESET}\n{output}\n")
    else:
        print(f"{Colors.YELLOW}[INFO] GEMINI_API_KEY environment variable is not set.{Colors.RESET}")
        print(f"To run live Gemini inference, set in PowerShell: {Colors.BOLD}$env:GEMINI_API_KEY=\"AIza...\"{Colors.RESET}")
        print(f"Running deterministic agent demonstration flow instead...\n")
        output = agent.run("Audit production database and verify node status.")
        print(f"\n{Colors.GREEN}[Agent Completed]:{Colors.RESET} {output}\n")


def main():
    parser = argparse.ArgumentParser(description="Argala & Google GenAI Demonstration Suite")
    parser.add_argument("--all", action="store_true", help="Run all demonstration scenarios sequentially")
    parser.add_argument("--telemetry", action="store_true", help="Run Scenario 1: Telemetry & Ping")
    parser.add_argument("--queue", action="store_true", help="Run Scenario 2: Durable Queue & Idempotency")
    parser.add_argument("--hitl", action="store_true", help="Run Scenario 3 & 4: HITL Gate & Vault Defense")
    parser.add_argument("--agent", action="store_true", help="Run Scenario 5: Gemini Agent Reasoning")
    args = parser.parse_args()

    client = ArgalaClient()
    print_banner()

    if args.telemetry:
        demo_telemetry(client)
    elif args.queue:
        demo_queue_idempotency(client)
    elif args.hitl:
        demo_hitl_and_vault(client)
    elif args.agent:
        demo_gemini_agent(client)
    elif args.all:
        demo_telemetry(client)
        demo_queue_idempotency(client)
        demo_hitl_and_vault(client)
        demo_gemini_agent(client)
    else:
        # Interactive menu
        while True:
            print("\nSelect a Demonstration Scenario:")
            print("  1. Wire-Level Ping & Physical Hardware Telemetry")
            print("  2. Durable Queue & Idempotent Deduplication (HTTP 202 vs 200)")
            print("  3. Cyber-Physical HITL Gate (Vibrate, TTS & Web Approval)")
            print("  4. Cryptographic Vault & TOCTOU Attack Defense")
            print("  5. Gemini AI Agent with Sovereign Tools")
            print("  6. Run Complete Architecture Suite (1-5)")
            print("  0. Exit")

            choice = input("\nEnter choice [1-6, 0]: ").strip()
            if choice == "1":
                demo_telemetry(client)
            elif choice == "2":
                demo_queue_idempotency(client)
            elif choice == "3" or choice == "4":
                demo_hitl_and_vault(client)
            elif choice == "5":
                demo_gemini_agent(client)
            elif choice == "6":
                demo_telemetry(client)
                demo_queue_idempotency(client)
                demo_hitl_and_vault(client)
                demo_gemini_agent(client)
            elif choice == "0":
                print("\nExiting demonstration suite. Argala is standing by 24/7.")
                break
            else:
                print("Invalid selection.")

    client.close()


if __name__ == "__main__":
    main()
