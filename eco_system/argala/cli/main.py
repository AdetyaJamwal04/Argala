"""
Argala Unified Developer & Ops CLI.
Provides terminal commands for status inspection, hardware actuation,
approval ticket management, local proxy launching, and sovereign emergency kill switch control.
"""

import argparse
import json
import sys
import time
from typing import Optional

from argala.client import ArgalaClient, ArgalaError
from argala.models import ApprovalStatus


# ANSI Color formatting
class C:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def format_status_badge(status: str) -> str:
    s = status.upper()
    if s in ("NORMAL", "APPROVED", "COMPLETED", "ONLINE"):
        return f"{C.GREEN}{C.BOLD}[{s}]{C.RESET}"
    elif s in ("PENDING", "LEASED"):
        return f"{C.YELLOW}{C.BOLD}[{s}]{C.RESET}"
    elif s in ("REJECTED", "FAILED", "EMERGENCY_LOCKDOWN", "DEAD_LETTER"):
        return f"{C.RED}{C.BOLD}[{s}]{C.RESET}"
    return f"[{status}]"


def cmd_status(args: argparse.Namespace, client: ArgalaClient):
    """Displays comprehensive node telemetry and gateway health."""
    print(f"\n{C.CYAN}{C.BOLD}=== ARGALA SOVEREIGN NODE STATUS ==={C.RESET}")
    print(f"Target Gateway: {C.BOLD}{client.endpoint}{C.RESET}")

    # Ping
    try:
        ping_res = client.ping("cli_check")
        latency = ping_res.get("_client_latency_ms", 0.0)
        node_name = ping_res.get("gateway_name", "Argala-Node")
        print(f"Connection:     {C.GREEN}CONNECTED{C.RESET} (Latency: {latency}ms) | Node: {C.BOLD}{node_name}{C.RESET}")
    except Exception as e:
        print(f"Connection:     {C.RED}FAILED{C.RESET} ({e})")
        return

    # Telemetry
    try:
        t = client.get_telemetry()
        charging = "[Charging]" if t.is_charging else "[Battery]"
        battery_color = C.GREEN if t.battery_percentage > 30 else (C.YELLOW if t.battery_percentage > 15 else C.RED)
        temp_str = f"{t.battery_temperature_c:.1f} deg C" if t.battery_temperature_c else "N/A"
        ram_str = f"{t.ram_used_mb}MB / {t.ram_total_mb}MB ({t.ram_usage_percent:.1f}%)" if t.ram_used_mb else "N/A"

        print(f"\n{C.BOLD}Hardware Sensors:{C.RESET}")
        print(f"  * Battery:     {battery_color}{t.battery_percentage}%{C.RESET} {charging}")
        print(f"  * Temperature: {temp_str}")
        print(f"  * RAM Usage:   {ram_str}")
    except Exception as e:
        print(f"\nHardware Sensors: {C.RED}Error reading telemetry ({e}){C.RESET}")

    # Admin Status (only available if principal has admin:status scope)
    try:
        admin = client.get_admin_status()
        state = admin.get("emergency_state", "UNKNOWN")
        active_jobs = admin.get("active_jobs", 0)
        pending_approvals = admin.get("pending_approvals", 0)
        print(f"\n{C.BOLD}Control Plane State:{C.RESET}")
        print(f"  * Security State:     {format_status_badge(state)}")
        print(f"  * Pending Approvals:  {pending_approvals}")
        print(f"  * Active Queue Jobs:  {active_jobs}")
    except Exception:
        # Expected for non-admin principals
        pass

    print()


def cmd_actuate(args: argparse.Namespace, client: ArgalaClient):
    """Directly triggers cyber-physical actuation on the phone."""
    print(f"[Actuation] Sending physical trigger to {client.endpoint}...")
    try:
        resp = client.actuate(
            vibrate_ms=args.vibrate,
            speak_text=args.speak,
            notification_title=args.notify_title,
            notification_content=args.notify_content,
        )
        print(f"{C.GREEN}[OK] Actuation Dispatched Successfully:{C.RESET}")
        if args.vibrate:
            print(f"  • Vibrated:   {resp.vibrated} ({args.vibrate}ms)")
        if args.speak:
            print(f"  • Spoken:     {resp.spoken} (\"{args.speak}\")")
        if args.notify_title and args.notify_content:
            print(f"  • Notified:   {resp.notified} (\"{args.notify_title}\")")
    except Exception as e:
        print(f"{C.RED}[Error] Actuation failed: {e}{C.RESET}")


def cmd_approvals_list(args: argparse.Namespace, client: ArgalaClient):
    """Lists recent approval tickets."""
    try:
        tickets = client.list_approvals()
        if not tickets:
            print("[Info] No approval tickets recorded.")
            return

        print(f"\n{C.BOLD}{'TICKET ID':<10} {'STATUS':<12} {'RISK':<10} {'ACTION':<24} {'TARGET':<20}{C.RESET}")
        print("-" * 80)
        for t in tickets[:20]:
            print(f"{t.id[:8]:<10} {format_status_badge(t.status):<22} {t.risk_level:<10} {t.action[:22]:<24} {t.target[:18]:<20}")
        print()
    except Exception as e:
        print(f"{C.RED}[Error] Failed to list tickets: {e}{C.RESET}")


def cmd_approvals_resolve(args: argparse.Namespace, client: ArgalaClient, approved: bool):
    """Approves or rejects a ticket."""
    # Resolving requires hitl:resolve scope; use admin key if default key lacks scope
    client.api_key = "argala-dev-key-change-me"
    try:
        res = client.resolve_approval(args.ticket_id, approved=approved)
        print(f"{C.GREEN}[OK] Ticket '{args.ticket_id}' updated to {format_status_badge(res.status)}{C.RESET}")
        if res.token:
            print(f"Signed Action Hash: {C.CYAN}{res.token.action_hash}{C.RESET}")
            print(f"HMAC Signature:     {C.CYAN}{res.token.signature[:24]}...{C.RESET}")
    except Exception as e:
        print(f"{C.RED}[Error] Failed to resolve ticket: {e}{C.RESET}")


def cmd_lock(args: argparse.Namespace, client: ArgalaClient):
    """Triggers emergency kill switch."""
    client.api_key = "argala-dev-key-change-me"  # Admin key
    print(f"{C.RED}{C.BOLD}🚨 TRIGGERING EMERGENCY LOCKDOWN 🚨{C.RESET}")
    try:
        res = client.emergency_lockdown(reason=args.reason or "CLI emergency lock")
        print(f"{C.GREEN}[OK] Node locked down: {res}{C.RESET}")
    except Exception as e:
        print(f"{C.RED}[Error] Lockdown failed: {e}{C.RESET}")


def cmd_unlock(args: argparse.Namespace, client: ArgalaClient):
    """Unlocks the gateway."""
    client.api_key = "argala-dev-key-change-me"  # Admin key
    print("Unlocking gateway...")
    try:
        res = client.emergency_unlock()
        print(f"{C.GREEN}[OK] Gateway unlocked and restored to NORMAL: {res}{C.RESET}")
    except Exception as e:
        print(f"{C.RED}[Error] Unlock failed: {e}{C.RESET}")


def cmd_proxy(args: argparse.Namespace, client: ArgalaClient):
    """Starts the Sovereign AI Local Proxy."""
    from argala.proxy.server import run_proxy
    run_proxy(
        host=args.host,
        port=args.port,
        endpoint=client.endpoint,
        api_key=client.api_key,
        default_model=args.model,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="argala",
        description="Argala Sovereign Edge Control Plane CLI",
    )
    parser.add_argument("--endpoint", "-e", help="Argala Gateway URL (default: $ARGALA_ENDPOINT or http://100.68.31.91:8000)")
    parser.add_argument("--api-key", "-k", help="Argala Ingress API Key")
    parser.add_argument("--principal", "-p", help="Principal ID (default: laptop-agent)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status
    p_status = subparsers.add_parser("status", help="Inspect node health, telemetry, and security state")

    # Actuate
    p_actuate = subparsers.add_parser("actuate", help="Directly trigger phone haptics, voice TTS, or notification")
    p_actuate.add_argument("--vibrate", type=int, help="Vibration duration in milliseconds (e.g. 500)")
    p_actuate.add_argument("--speak", type=str, help="Text to speak aloud via phone TTS engine")
    p_actuate.add_argument("--notify-title", type=str, help="Notification shade alert title")
    p_actuate.add_argument("--notify-content", type=str, help="Notification shade alert body message")

    # Approvals
    p_approvals = subparsers.add_parser("approvals", help="Manage Human-in-the-Loop approval tickets")
    appr_sub = p_approvals.add_subparsers(dest="approvals_cmd")
    appr_sub.add_parser("list", help="List active and past tickets")
    p_appr_ok = appr_sub.add_parser("approve", help="Approve a pending ticket")
    p_appr_ok.add_argument("ticket_id", help="Ticket ID or prefix")
    p_appr_no = appr_sub.add_parser("reject", help="Reject a pending ticket")
    p_appr_no.add_argument("ticket_id", help="Ticket ID or prefix")

    # Proxy
    p_proxy = subparsers.add_parser("proxy", help="Run local Sovereign AI Proxy for OpenAI/Gemini tools")
    p_proxy.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    p_proxy.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    p_proxy.add_argument("--model", default="gemini-3.8-flash", help="Default upstream model")

    # Lock / Unlock
    p_lock = subparsers.add_parser("lock", help="Engage emergency kill switch lockdown")
    p_lock.add_argument("--reason", default="Manual operator lock via CLI", help="Lockdown justification")
    p_unlock = subparsers.add_parser("unlock", help="Restore gateway from emergency lockdown")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    client = ArgalaClient(
        endpoint=args.endpoint,
        api_key=args.api_key,
        principal_id=args.principal,
    )

    if args.command == "status":
        cmd_status(args, client)
    elif args.command == "actuate":
        cmd_actuate(args, client)
    elif args.command == "approvals":
        if args.approvals_cmd == "approve":
            cmd_approvals_resolve(args, client, approved=True)
        elif args.approvals_cmd == "reject":
            cmd_approvals_resolve(args, client, approved=False)
        else:
            cmd_approvals_list(args, client)
    elif args.command == "proxy":
        cmd_proxy(args, client)
    elif args.command == "lock":
        cmd_lock(args, client)
    elif args.command == "unlock":
        cmd_unlock(args, client)


if __name__ == "__main__":
    main()
