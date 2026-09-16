"""
Test Queue & Idempotency Harness for Argala Gateway.
Tests:
1. Asynchronous Job Submission (HTTP 202)
2. Idempotency Key Deduping (HTTP 200 on retry)
3. Background Worker Execution & Result Retrieval
4. Automatic Retry & Dead-Letter Queue (DLQ) Routing
Uses pure Python standard library.
"""

import json
import time
import urllib.request
import uuid

SERVER_HOST = "100.68.31.91:8000"
BASE_URL = f"http://{SERVER_HOST}/v1/jobs"
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
    print("    ARGALA DISTRIBUTED QUEUE & DLQ TEST HARNESS   ")
    print("==================================================")

    # 1. Test Asynchronous Job Submission
    idempotency_key = f"client-req-{uuid.uuid4()}"
    print(f"\n[Test 1] Submitting asynchronous job with Idempotency Key: {idempotency_key}")
    job_payload = {
        "capability": "telemetry.snapshot",
        "payload": {"reason": "routine_health_audit"},
        "idempotency_key": idempotency_key,
    }
    status_code, job = make_request(BASE_URL, method="POST", data=job_payload)
    print(f" -> HTTP Status: {status_code} (Expected 202 Accepted)")
    job_id = job.get("id")
    print(f" -> Job ID: {job_id}")
    print(f" -> Initial Status: {job.get('status')}")

    # 2. Test Idempotency (Network Retry Simulation)
    print("\n[Test 2] Simulating client retry with EXACT SAME Idempotency Key...")
    status_code_retry, job_retry = make_request(BASE_URL, method="POST", data=job_payload)
    print(f" -> HTTP Status: {status_code_retry} (Expected 200 OK for duplicate)")
    print(f" -> Retried Job ID: {job_retry.get('id')}")
    if job_retry.get("id") == job_id and status_code_retry == 200:
        print(" [+] SUCCESS: Idempotency deduplicated the request! No duplicate job created.")
    else:
        print(" [-] FAILED: Idempotency check failed.")

    # 3. Test Worker Lease & Execution
    print(f"\n[Test 3] Polling job [{job_id}] for worker completion...")
    completed = False
    for i in range(10):
        time.sleep(1.0)
        _, current_job = make_request(f"{BASE_URL}/{job_id}")
        current_status = current_job.get("status")
        print(f" -> Poll #{i+1}: Status = {current_status} (Worker: {current_job.get('worker_id')})")
        if current_status == "COMPLETED":
            completed = True
            print(" [+] SUCCESS: Job completed by background worker!")
            print(f" -> Result output:\n{json.dumps(current_job.get('result'), indent=2)}")
            break

    if not completed:
        print(" [-] Job did not complete within 10 seconds.")

    # 4. Test Poison Pill & Dead-Letter Queue (DLQ)
    print("\n[Test 4] Submitting intentionally failing job (max_retries=2) to test DLQ...")
    fail_payload = {
        "capability": "test.fail",
        "payload": {"error": "Simulated hardware error"},
        "max_retries": 2,
    }
    _, fail_job = make_request(BASE_URL, method="POST", data=fail_payload)
    fail_id = fail_job.get("id")
    print(f" -> Enqueued Fail Job ID: {fail_id}")

    dlq_routed = False
    for i in range(10):
        time.sleep(1.0)
        _, current_job = make_request(f"{BASE_URL}/{fail_id}")
        current_status = current_job.get("status")
        retries = current_job.get("retry_count")
        print(f" -> Poll #{i+1}: Status = {current_status} | Retries: {retries}/2 | Error: {current_job.get('error')}")
        if current_status == "FAILED":
            dlq_routed = True
            print(" [+] SUCCESS: Poison pill retries exhausted -> Job routed to Dead-Letter Queue (DLQ)!")
            break

    if not dlq_routed:
        print(" [-] Job was not routed to DLQ in time.")

    print("\n==================================================")
    print("   ALL DISTRIBUTED QUEUE TESTS COMPLETED!         ")
    print("==================================================")


if __name__ == "__main__":
    main()
