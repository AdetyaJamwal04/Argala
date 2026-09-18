# Argala Sovereign Ecosystem: End-to-End Application Flow

This document describes how data and control pass between components at runtime across the primary user journeys.

---

## Flow 1: Cyber-Physical Function Gating (`@requires_approval`)

Used when a Python function performs a sensitive operation (e.g. database migration, infrastructure termination, high-value transfer).

```text
[Developer App]              [Argala SDK Client]           [Argala Edge Gateway]           [Physical Phone / Human]
       │                              │                              │                                  │
       │─── 1. Call gated func() ────>│                              │                                  │
       │    e.g. drop_db()            │                              │                                  │
       │                              │─── 2. POST /v1/approvals ───>│                                  │
       │                              │    (action, risk, prompt)    │                                  │
       │                              │                              │─── 3. Termux Actuation ─────────>│
       │                              │                              │    • termux-vibrate              │ (Vibration)
       │                              │                              │    • termux-tts-speak            │ ("Approval required...")
       │                              │                              │    • termux-notification         │ (Notification Shade)
       │                              │                              │                                  │
       │                              │<── 4. Return Ticket (PENDING)│                                  │
       │                              │                              │                                  │
       │                              │─── 5. Poll /v1/approvals/{id} (every 1s)                        │
       │                              │                              │                                  │
       │                              │                              │<── 6. Human Taps "APPROVE" ──────│
       │                              │                              │    on Mobile Web UI              │
       │                              │                              │                                  │
       │                              │<── 7. Return (APPROVED) ─────│                                  │
       │                              │       + Signed Action Token  │                                  │
       │                              │                              │                                  │
       │<── 8. Execute Original Func ─│                              │                                  │
       │    Return result             │                              │                                  │
```

### Error / Edge-Case Handling:
- **Human Rejection**: If the human taps "REJECT" on the phone, the SDK raises `ArgalaApprovalDeniedError`. The gated function is **never executed**.
- **Timeout**: If no action is taken within the timeout period (e.g. 60 seconds), the ticket transitions to `EXPIRED`. The SDK raises `ArgalaTimeoutError`, aborting execution.
- **Gateway Lockdown**: If the gateway is in `EMERGENCY_LOCKDOWN`, the approval creation request returns `HTTP 423 Locked`. The SDK immediately aborts.

---

## Flow 2: Secretless AI Inference via Sovereign Local Proxy

Used when local tools (Cursor, VS Code extensions, LangChain, CLI tools) need LLM inference without holding API keys on the laptop.

```text
[Cursor / IDE]              [Sovereign Local Proxy]       [Argala Phone Vault]           [Google Gemini API]
      │                                │                                │                                │
      │─── 1. POST /v1/chat/compl ────>│                                │                                │
      │    (No API key needed)         │                                │                                │
      │                                │─── 2. POST /v1/vault/broker ──>│                                │
      │                                │    service="gemini", path=...  │                                │
      │                                │                                │─── 3. Decrypt Key in Vault ────│
      │                                │                                │    (AES-256 / PBKDF2)          │
      │                                │                                │                                │
      │                                │                                │─── 4. Outbound HTTPS Call ────>│
      │                                │                                │    (Carries Decrypted Key)     │
      │                                │                                │                                │
      │                                │                                │<── 5. Inference Response ──────│
      │                                │                                │                                │
      │                                │<── 6. Return Clean Body ───────│                                │
      │                                │                                │                                │
      │<── 7. Return Standard JSON ────│                                │                                │
      │    (OpenAI / Gemini format)    │                                │                                │
```

### Error / Edge-Case Handling:
- **SSRF Boundary Rejection**: If an agent attempts to pass a destination URL resolving to `127.0.0.1`, `localhost`, link-local (`169.254.169.254`), or private RFC 1918 subnets, the phone vault immediately aborts the call with `HTTP 400 Bad Request` or `HTTP 502 Bad Gateway` ("Access to private/local/metadata network addresses is forbidden").
- **Phone Unreachable**: If the phone is offline, the proxy returns `503 Service Unavailable` with a clear explanation: "Argala Edge Node unreachable over WireGuard mesh".
- **Quota / Rate Limit**: If Google returns `429 Too Many Requests`, the phone vault relays the upstream status code and headers cleanly to the local proxy.
- **Laptop Compromise**: An attacker gaining root on the laptop can only access the local proxy interface while connected to the mesh. They **cannot extract the underlying Gemini/OpenAI API key** because it is never transmitted to or stored on the laptop.

---

## Flow 3: Autonomous Agent Feedback & Telemetry Loop

Used when an autonomous agent (e.g. Gemini 3.8 Flash) operates with sensory feedback and physical actuation on the edge node.

```text
[Autonomous Gemini Agent]      [Argala SDK / Tools]       [FastAPI Gateway]            [Phone Hardware Sensors]
           │                            │                         │                               │
           │─── 1. Query Node State ───>│                         │                               │
           │    get_telemetry()         │─── 2. GET /v1/telemetry>│                               │
           │                            │                         │─── 3. termux-battery-status ─>│
           │                            │                         │<── 4. Battery: 100%, 29.8°C ──│
           │                            │<── 5. Telemetry JSON ───│                               │
           │<── 6. Formulate Plan ──────│                         │                               │
           │                            │                         │                               │
           │─── 7. Actuate Phone ──────>│                         │                               │
           │    actuate(vibrate, speak) │─── 8. POST /actuate ───>│                               │
           │                            │                         │─── 9. TTS: "Plan formulated"─>│ (Voice Out loud)
           │                            │<── 10. OK (200) ────────│                               │
           │                                                                                      │
           │─── 11. Request Approval for High-Risk Action ───────────────────────────────────────>│
           │    (Transitions into Flow 1)                                                         │
```

---

## Flow 4: Durable Background Job Queue Execution

Used when asynchronous background tasks are offloaded to the phone's edge worker:

```text
[Client / Agent]                [FastAPI Gateway (/v1/queue)]     [SQLite WAL Queue]          [Edge Worker Task]
       │                                     │                            │                           │
       │─── 1. POST /v1/queue/jobs ─────────>│                            │                           │
       │    (capability, payload, requester) │─── 2. INSERT (QUEUED) ────>│                           │
       │<── 3. Return JobRecord (job_id) ────│                            │                           │
       │                                                                  │─── 4. Acquire Lease ─────>│
       │                                                                  │    (Status -> RUNNING)    │
       │                                                                  │                           │── 5. Dispatch (e.g. vault.broker)
       │                                                                  │<── 6. UPDATE (COMPLETED) ─│
       │─── 7. GET /v1/queue/jobs/{id} ─────>│                            │
       │<── 8. Return Job with Output ───────│─── Read result ───────────>│
```

