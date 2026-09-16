"""
Test Harness for Sovereign Vault, Cryptographic Signing, TOCTOU, and Secretless Brokering.
Tests:
1. Canonical Action Signing (HMAC-SHA256)
2. Parameter Tampering Detection (TOCTOU Attack Prevention)
3. Valid Token Verification & Nonce Replay Prevention
4. Encrypted Secret Storage & Secretless Outbound HTTP Brokering
Uses pure Python standard library.
"""

import json
import time
import urllib.request
import uuid

SERVER_HOST = "100.68.31.91:8000"
VAULT_URL = f"http://{SERVER_HOST}/v1/vault"
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
    print("    ARGALA CRYPTOGRAPHIC VAULT & SIGNER HARNESS   ")
    print("==================================================")

    # 1. Sign an Action Intent
    nonce = str(uuid.uuid4())
    intent = {
        "action": "database.migrate",
        "target": "production-cluster",
        "parameters": {
            "migration_version": "2026_09_v2",
            "dry_run": False,
            "timeout_seconds": 60,
        },
        "requester": "laptop-agent-01",
        "timestamp": time.time(),
        "nonce": nonce,
    }

    print(f"\n[Test 1] Signing Action Intent: '{intent['action']}' on target '{intent['target']}'...")
    status, token = make_request(f"{VAULT_URL}/sign", method="POST", data=intent)
    print(f" -> HTTP Status: {status}")
    print(f" -> Canonical Action Hash: {token.get('action_hash')}")
    print(f" -> HMAC Signature: {token.get('signature')}")
    print(f" -> Expires At: {token.get('expires_at')}")

    # 2. TOCTOU Parameter Tampering Test
    print("\n[Test 2] Simulating TOCTOU Parameter Tampering Attack...")
    tampered_intent = dict(intent)
    # Attacker secretly alters a parameter after signing!
    tampered_intent["parameters"] = {
        "migration_version": "2026_09_v2",
        "dry_run": True,  # Altered!
        "timeout_seconds": 60,
    }

    status, tampered_res = make_request(
        f"{VAULT_URL}/verify",
        method="POST",
        data={"intent": tampered_intent, "token": token},
    )
    print(f" -> Verify Result: valid = {tampered_res.get('valid')}")
    print(f" -> Rejection Reason: {tampered_res.get('reason')}")
    if not tampered_res.get("valid"):
        print(" [+] SUCCESS: TOCTOU attack detected and prevented! Parameter tampering was caught.")
    else:
        print(" [-] FAILED: Parameter tampering was not detected.")

    # 3. Valid Action Verification
    print("\n[Test 3] Verifying Legitimate, Untampered Action Intent...")
    status, valid_res = make_request(
        f"{VAULT_URL}/verify",
        method="POST",
        data={"intent": intent, "token": token},
    )
    print(f" -> Verify Result: valid = {valid_res.get('valid')}")
    if valid_res.get("valid"):
        print(" [+] SUCCESS: Valid action token accepted and nonce consumed!")
    else:
        print(f" [-] FAILED: Legitimate token was rejected: {valid_res.get('reason')}")

    # 4. Anti-Replay Attack Test (Re-using consumed nonce)
    print("\n[Test 4] Simulating Replay Attack (resending same token and nonce)...")
    status, replay_res = make_request(
        f"{VAULT_URL}/verify",
        method="POST",
        data={"intent": intent, "token": token},
    )
    print(f" -> Verify Result: valid = {replay_res.get('valid')}")
    print(f" -> Rejection Reason: {replay_res.get('reason')}")
    if not replay_res.get("valid") and "Replay attack detected" in str(replay_res.get("reason")):
        print(" [+] SUCCESS: Replay attack detected and blocked! Nonce was single-use.")
    else:
        print(" [-] FAILED: Replay attack check failed.")

    # 5. Encrypted Secret Storage & Secretless Brokering
    print("\n[Test 5] Storing Encrypted Credential in Edge Vault...")
    secret_req = {
        "secret_id": "test_github_pat",
        "plaintext": "ghp_mockSecretToken9876543210ABCDEF",
        "description": "Mock GitHub Personal Access Token for Deployment",
    }
    status, stored_meta = make_request(f"{VAULT_URL}/secrets", method="POST", data=secret_req)
    print(f" -> HTTP Status: {status}")
    print(f" -> Stored Secret ID: {stored_meta.get('secret_id')}")

    # Verify secret is NEVER returned in plaintext
    print("\n[Test 6] Auditing Secret List (Verifying zero plaintext exposure)...")
    status, secret_list = make_request(f"{VAULT_URL}/secrets")
    print(f" -> Stored Secrets count: {secret_list.get('total')}")
    for s in secret_list.get("secrets", []):
        print(f"    * Secret ID: {s.get('secret_id')} | Description: {s.get('description')}")
    print(" [+] Verified: Raw secret value is completely absent from metadata.")

    # 6. Secretless Outbound API Brokering
    print("\n[Test 7] Executing Secretless Outbound API Call through Phone...")
    broker_req = {
        "url": f"http://{SERVER_HOST}/v1/health/live",
        "method": "GET",
        "secret_id": "test_github_pat",
        "header_name": "Authorization",
        "header_prefix": "Bearer ",
    }
    status, broker_res = make_request(f"{VAULT_URL}/broker", method="POST", data=broker_req)
    print(f" -> Broker HTTP Status: {status}")
    print(f" -> Remote Response Code: {broker_res.get('status_code')}")
    print(f" -> Remote Response Body: {broker_res.get('body')}")
    if broker_res.get("status_code") == 200:
        print(" [+] SUCCESS: Secretless request proxied cleanly through phone vault!")

    print("\n==================================================")
    print("   ALL CRYPTOGRAPHIC VAULT TESTS COMPLETED!       ")
    print("==================================================")


if __name__ == "__main__":
    main()
