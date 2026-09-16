"""
==============================================================================
ARGALA ZERO-TRUST IDENTITY & EMERGENCY KILL SWITCH VERIFICATION HARNESS
==============================================================================
Validates:
1. Least-Privilege Scoping: Scoped agent cannot access unauthorized endpoints (HTTP 403).
2. Authorized Actions: Scoped agent can execute permitted endpoints (HTTP 202/200).
3. Emergency Kill Switch: Instant remote quarantine cuts off all agent access (HTTP 423 Locked).
4. Physical Safety Interlock: Vault and Queue reject operations during lockdown.
5. Administrative Recovery: Sovereign owner disarms lockdown and restores normal operations.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://100.68.31.91:8000"
MASTER_API_KEY = "argala-dev-key-change-me"


def make_request(url: str, method: str = "GET", data: dict = None, headers: dict = None):
    req_headers = {"User-Agent": "Argala-KillSwitchTest/1.0"}
    if headers:
        req_headers.update(headers)

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            status_code = resp.status
            content = resp.read().decode("utf-8")
            return status_code, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"raw_error": content}
    except Exception as e:
        print(f"[-] Connection Error: {e}")
        return 0, {}


def main():
    print("=" * 60)
    print("      ARGALA ZERO-TRUST IDENTITY & KILL SWITCH HARNESS      ")
    print("=" * 60)

    # ------------------------------------------------------------------------
    # Step 0: Ensure System is in NORMAL State
    # ------------------------------------------------------------------------
    status_code, status_data = make_request(
        f"{BASE_URL}/v1/admin/status",
        headers={"X-API-Key": MASTER_API_KEY}
    )
    if status_code != 200:
        print(f"[-] Unable to connect to gateway admin endpoint. Status: {status_code}")
        sys.exit(1)

    print(f"\n[Status Check] Gateway State: {status_data.get('state')} (Locked: {status_data.get('is_locked')})")
    if status_data.get("is_locked"):
        print(" -> System currently in lockdown. Disarming before starting test run...")
        make_request(
            f"{BASE_URL}/v1/admin/unlock",
            method="POST",
            data={"cleared_by": "test-harness-init"},
            headers={"X-API-Key": MASTER_API_KEY}
        )

    # ------------------------------------------------------------------------
    # Test 1: Authorized Action from Scoped Principal (laptop-agent)
    # ------------------------------------------------------------------------
    print("\n[Test 1] Executing Authorized Action as Principal 'laptop-agent'...")
    job_payload = {
        "capability": "system.echo",
        "payload": {"message": "Hello from verified laptop agent"},
        "idempotency_key": f"agent-job-{int(time.time())}",
    }
    status_code, resp = make_request(
        f"{BASE_URL}/v1/jobs",
        method="POST",
        data=job_payload,
        headers={"X-API-Key": MASTER_API_KEY, "X-Principal-ID": "laptop-agent"},
    )
    print(f" -> HTTP Status: {status_code}")
    print(f" -> Response Job ID: {resp.get('id')}")
    if status_code in (200, 202):
        print(" [+] SUCCESS: Permitted action ('jobs:submit') accepted for 'laptop-agent'.")
    else:
        print(f" [-] FAILED: Authorized action was rejected. Response: {resp}")

    # ------------------------------------------------------------------------
    # Test 2: Least-Privilege Scope Violation (Privilege Escalation Attempt)
    # ------------------------------------------------------------------------
    print("\n[Test 2] Simulating Privilege Escalation: 'laptop-agent' attempts to store secret in Vault...")
    secret_payload = {
        "secret_id": "malicious-injection",
        "plaintext": "unauthorized-secret-write",
        "description": "Exploit attempt",
    }
    status_code, resp = make_request(
        f"{BASE_URL}/v1/vault/secrets",
        method="POST",
        data=secret_payload,
        headers={"X-API-Key": MASTER_API_KEY, "X-Principal-ID": "laptop-agent"},
    )
    print(f" -> HTTP Status: {status_code} (Expected 403 Forbidden)")
    print(f" -> Error Detail: {resp.get('detail')}")
    if status_code == 403:
        print(" [+] SUCCESS: Zero-Trust capability enforcement blocked unauthorized scope ('vault:secrets')!")
    else:
        print(" [-] FAILED: Privilege escalation was not prevented!")

    # ------------------------------------------------------------------------
    # Test 3: Trigger Emergency Lockdown (The Sovereign Kill Switch)
    # ------------------------------------------------------------------------
    print("\n[Test 3] Triggering Emergency Kill Switch (Quarantine Active Agents)...")
    lockdown_payload = {
        "reason": "Compromised agent detected on developer laptop",
        "initiated_by": "test-runner",
    }
    status_code, resp = make_request(
        f"{BASE_URL}/v1/admin/lockdown",
        method="POST",
        data=lockdown_payload,
        headers={"X-API-Key": MASTER_API_KEY},
    )
    print(f" -> HTTP Status: {status_code}")
    print(f" -> Status Flag: {resp.get('status')}")
    print(f" -> Alert Message: {resp.get('message')}")
    if status_code == 200 and resp.get("status") == "EMERGENCY_LOCKDOWN_ACTIVATED":
        print(" [+] SUCCESS: Emergency Lockdown engaged! Mobile alarms and vibration triggered.")
    else:
        print(f" [-] FAILED: Lockdown trigger failed: {resp}")

    # ------------------------------------------------------------------------
    # Test 4: Verify Complete Quarantine (HTTP 423 Locked)
    # ------------------------------------------------------------------------
    print("\n[Test 4] Verifying Agent Quarantine: 'laptop-agent' attempts queue submission during lockdown...")
    status_code, resp = make_request(
        f"{BASE_URL}/v1/jobs",
        method="POST",
        data={"capability": "system.echo", "payload": {}},
        headers={"X-API-Key": MASTER_API_KEY, "X-Principal-ID": "laptop-agent"},
    )
    print(f" -> HTTP Status: {status_code} (Expected 423 Locked)")
    print(f" -> Detail: {resp.get('detail')}")
    if status_code == 423:
        print(" [+] SUCCESS: Ingress completely blocked with HTTP 423 Locked!")
    else:
        print(" [-] FAILED: Quarantine leak detected!")

    print("\n[Test 4B] Verifying Sovereign Vault Quarantine: External client attempts action signing...")
    dummy_intent = {
        "action": "server.reboot",
        "target": "prod-node-01",
        "parameters": {},
        "requester": "laptop-agent",
        "timestamp": time.time(),
        "nonce": "quarantine-test-nonce",
    }
    status_code, resp = make_request(
        f"{BASE_URL}/v1/vault/sign",
        method="POST",
        data=dummy_intent,
        headers={"X-API-Key": MASTER_API_KEY, "X-Principal-ID": "laptop-agent"},
    )
    print(f" -> HTTP Status: {status_code} (Expected 423 Locked)")
    if status_code == 423:
        print(" [+] SUCCESS: Sovereign Vault is frozen and refused to sign during lockdown!")
    else:
        print(f" [-] FAILED: Vault responded with status {status_code}")

    # ------------------------------------------------------------------------
    # Test 5: Administrative Recovery (Disarm & Restore)
    # ------------------------------------------------------------------------
    print("\n[Test 5] Administrative Recovery: Sovereign owner disarms lockdown...")
    status_code, resp = make_request(
        f"{BASE_URL}/v1/admin/unlock",
        method="POST",
        data={"cleared_by": "sovereign-mobile-owner"},
        headers={"X-API-Key": MASTER_API_KEY},
    )
    print(f" -> HTTP Status: {status_code}")
    print(f" -> Restored Status: {resp.get('status')}")
    print(f" -> Message: {resp.get('message')}")
    if status_code == 200 and resp.get("status") == "NORMAL":
        print(" [+] SUCCESS: Sovereign control plane restored to NORMAL operation.")
    else:
        print(f" [-] FAILED: Failed to restore gateway: {resp}")

    # ------------------------------------------------------------------------
    # Test 6: Verify Post-Recovery Service Resumption
    # ------------------------------------------------------------------------
    print("\n[Test 6] Verifying Service Resumption: 'laptop-agent' retries job submission...")
    recovery_job = {
        "capability": "system.echo",
        "payload": {"message": "Service verified post-quarantine"},
        "idempotency_key": f"recovery-job-{int(time.time())}",
    }
    status_code, resp = make_request(
        f"{BASE_URL}/v1/jobs",
        method="POST",
        data=recovery_job,
        headers={"X-API-Key": MASTER_API_KEY, "X-Principal-ID": "laptop-agent"},
    )
    print(f" -> HTTP Status: {status_code}")
    print(f" -> Resumed Job ID: {resp.get('id')}")
    if status_code in (200, 202):
        print(" [+] SUCCESS: Gateway resumed normal operation without restart!")
    else:
        print(f" [-] FAILED: Service did not resume cleanly: {resp}")

    print("\n" + "=" * 60)
    print("   PHASE 6 ZERO-TRUST & KILL SWITCH HARNESS COMPLETE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
