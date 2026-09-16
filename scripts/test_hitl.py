"""
Interactive Cyber-Physical Human-in-the-Loop (HITL) Test Harness.
Triggers:
1. Submits high-risk action approval ticket to the phone.
2. Triggers phone physical vibration & TTS speech alert ("Approval required...").
3. Instructs user to open http://100.68.31.91:8000/approvals on their phone.
4. Polls until the human physically taps Approve or Reject on the phone screen!
Uses pure Python standard library.
"""

import json
import time
import urllib.request

SERVER_HOST = "100.68.31.91:8000"
APPROVALS_URL = f"http://{SERVER_HOST}/v1/approvals"
UI_URL = f"http://{SERVER_HOST}/approvals"
API_KEY = "argala-dev-key-change-me"


def make_request(url: str, method: str = "GET", data: dict = None) -> tuple:
    payload_bytes = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw_error": raw}
        return e.code, body


def main():
    print("==================================================")
    print("     ARGALA CYBER-PHYSICAL HITL DEMO HARNESS      ")
    print("==================================================")

    # 1. Submit high-risk action approval request
    print("\n[Step 1] Submitting Critical Action Intent to Edge Node...")
    ticket_payload = {
        "action": "cloud.terminate_cluster",
        "target": "aws/us-east-1/production-k8s",
        "parameters": {
            "cluster_name": "prod-workloads-alpha",
            "drain_nodes": True,
            "force_terminate": True,
            "cost_saving_monthly": "$4,200",
        },
        "requester": "autonomous-optimizer-agent",
        "risk_level": "CRITICAL",
        "summary": "Autonomous agent requests immediate shutdown of production Kubernetes cluster to optimize cloud budget.",
        "ttl_seconds": 120,
        "sound_alert": True,
        "vibrate": True,
    }

    status, ticket = make_request(f"{APPROVALS_URL}/request", method="POST", data=ticket_payload)
    if status != 201:
        print(f"[-] Failed to submit ticket (HTTP {status}): {ticket}")
        return

    ticket_id = ticket.get("id")
    print(f" -> Ticket Created: {ticket_id}")
    print(f" -> Risk Level: {ticket.get('risk_level')}")
    print(f" -> TTL: {ticket.get('expires_at') - ticket.get('created_at')} seconds")

    print("\n--------------------------------------------------")
    print(" 🔔 PHYSICAL ALERT TRIGGERED ON YOUR PHONE!")
    print(" -> Listen for your phone's voice announcement (TTS)")
    print(" -> Feel the haptic vibration alert")
    print(f"\n 📱 Open the Mobile Console on your phone's browser:")
    print(f"    {UI_URL}")
    print("--------------------------------------------------\n")

    # 2. Wait for human operator to approve or reject on the phone
    print("[Step 2] Waiting for human operator decision on phone screen...")
    resolved = False
    start_poll = time.time()

    while time.time() - start_poll < 120:
        time.sleep(2.0)
        _, current_ticket = make_request(f"{APPROVALS_URL}/{ticket_id}")
        current_status = current_ticket.get("status")
        remaining_time = max(0, int(current_ticket.get("expires_at") - time.time()))

        print(f" -> [{int(time.time() - start_poll)}s] Ticket Status: {current_status} | Time Left: {remaining_time}s")

        if current_status == "APPROVED":
            resolved = True
            print("\n==================================================")
            print(" 🎉 HUMAN OPERATOR APPROVED THE ACTION ON PHONE!")
            print("==================================================")
            token = current_ticket.get("token")
            print(f" -> Cryptographic HMAC Token: {token.get('signature')}")
            print(f" -> Canonical Hash Sealed:    {token.get('action_hash')}")
            print(f" -> Resolved By:              {current_ticket.get('resolved_by')}")
            print("\n[+] Autonomous Agent is now cryptographically authorized to execute.")
            break

        elif current_status == "REJECTED":
            resolved = True
            print("\n==================================================")
            print(" 🛑 HUMAN OPERATOR REJECTED THE ACTION ON PHONE!")
            print("==================================================")
            print(f" -> Resolved By: {current_ticket.get('resolved_by')}")
            print("[-] Autonomous Agent halted. No cryptographic signature was issued.")
            break

        elif current_status == "EXPIRED":
            resolved = True
            print("\n==================================================")
            print(" ⌛ TICKET EXPIRED! (No human response in 120s)")
            print("==================================================")
            print("[-] Anti-Zombie invariant triggered. Ticket voided.")
            break

    if not resolved:
        print("[-] Polling timed out after 120 seconds.")


if __name__ == "__main__":
    main()
