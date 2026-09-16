# Argala (अर्गला) 🛡️

> **The Sovereign Deadbolt & 24/7 Cyber-Physical AI Control Plane**  
> *"The laptop thinks. The cloud computes. Argala authorizes, protects, queues, and connects."*

**Argala** (*अर्गला* — ancient Sanskrit for the heavy locking bar / deadbolt that seals fortified fortress gates) is an always-on, hardware-isolated edge API gateway, sovereign credential vault, and cyber-physical Human-in-the-Loop (HITL) gatekeeper running on Android Termux, accessible globally via private WireGuard mesh networking.

---

## 🏛️ Architecture Overview

```text
                               ┌────────────────────────────────────────┐
                               │             ARGALA GATEWAY             │
                               │          Android 10 + Termux           │
                               │                                        │
                               │  ┌──────────────────────────────────┐  │
                               │  │ API Gateway & Zero-Trust Auth    │  │
                               │  │ Cryptographic Intent Signer      │  │
                               │  │ Envelope-Encrypted Vault         │  │
                               │  │ Durable SQLite Queue (WAL)       │  │
                               │  │ HITL Physical Actuation Bridge   │  │
                               │  │ Remote Model Context Protocol    │  │
                               │  │ Sovereign Emergency Kill Switch  │  │
                               │  └──────────────────┬───────────────┘  │
                               └─────────────────────┼──────────────────┘
                                                     │
                                           Encrypted Mesh (WireGuard)
                                                     │
                     ┌───────────────────────────────┼───────────────────────────────┐
                     │                               │                               │
           ┌─────────▼─────────┐           ┌─────────▼─────────┐           ┌─────────▼─────────┐
           │ Laptop AI Runtime │           │ Cloud Worker Node │           │ External APIs     │
           │ (Antigravity/Lang)│           │ (Heavy Inference) │           │ (Secretless Proxy)│
           └───────────────────┘           └───────────────────┘           └───────────────────┘
```

Argala turns a spare Android phone into a dedicated hardware security appliance. High-privilege credentials never leave the phone. External AI agents submit action tickets and request cryptographic authorization, while critical actions trigger physical haptics, voice announcements, and mobile approval prompts.

---

## ✨ Core Capabilities

1. **Global Zero-Trust Transport**:
   - Secure peer-to-peer WireGuard mesh via Tailscale. Accessible from any authorized device worldwide without public port forwarding.
   - Fine-grained capability scopes (`jobs:submit`, `vault:sign`, `hitl:request`, `telemetry:read`).
2. **Model Context Protocol (MCP)**:
   - Full Anthropic MCP standard implementation over Server-Sent Events (SSE) and JSON-RPC 2.0.
   - Native integration for AI agents (Antigravity IDE, Claude Desktop, Cursor).
3. **Durable SQLite Queue & Lease Manager**:
   - SQLite in Write-Ahead Logging (WAL) mode for resilient, concurrent task ingestion.
   - Idempotency deduplication, lease-based claiming with automatic crash recovery, and Dead-Letter Queue (DLQ).
4. **Sovereign Cryptographic Vault & Signer**:
   - Canonical JSON serialization (RFC 8785) & SHA-256 action hashing.
   - Anti-replay nonce tracking and TOCTOU (Time-of-Check to Time-of-Use) parameter tampering detection.
   - Secretless outbound HTTP broker injecting credentials on-device without exposing keys to calling agents.
5. **Cyber-Physical Human-in-the-Loop (HITL)**:
   - Physical actuation bridge calling Android native APIs via Termux: haptic vibration (`termux-vibrate`), Text-to-Speech announcements (`termux-tts-speak`), and notification shade alerts.
   - Responsive, dark-mode mobile web dashboard with one-tap approval and cryptographic token issuance.
6. **Sovereign Emergency Kill Switch**:
   - Instant remote session revocation and vault lockdown.
   - Single-tap panic button (`🚨 KILL SWITCH`) physically accessible on the phone web console.
   - Halts active queue workers and rejects all agent traffic with `HTTP 423 Locked`.
7. **24/7 Unattended Boot & Supervision**:
   - `scripts/watchdog.sh` supervisor with `termux-wake-lock` and auto-restart loop.
   - `Termux:Boot` automation script launching Argala automatically on Android reboot.

---

## 📁 Repository Structure

```text
.
├── app/
│   ├── api/                     # FastAPI route definitions
│   │   ├── deps.py              # Zero-Trust Principal & scope enforcement
│   │   ├── router.py            # API router aggregator
│   │   ├── routes_admin.py      # Emergency Kill Switch & status endpoints
│   │   ├── routes_approvals.py  # HITL ticket creation & resolution
│   │   ├── routes_health.py     # Liveness & readiness probes
│   │   ├── routes_jobs.py       # Durable queue endpoints
│   │   ├── routes_mcp.py        # Model Context Protocol endpoints
│   │   ├── routes_telemetry.py  # Android hardware sensor telemetry
│   │   └── routes_vault.py      # Cryptographic signing & secret broker
│   ├── core/
│   │   └── identity.py          # Principal policies, LockdownManager, revocation ledger
│   ├── db/
│   │   └── database.py          # SQLite WAL connection & schema initialization
│   ├── hardware/
│   │   ├── actuation.py         # Subprocess bridge for termux-api (vibrate, TTS, notification)
│   │   └── telemetry.py         # Hardware telemetry (battery, RAM, thermal state)
│   ├── hitl/
│   │   ├── manager.py           # Approval ticket state machine & timeout manager
│   │   ├── models.py            # Pydantic ticket & resolution schemas
│   │   └── web_ui.py            # Embedded dark-mode mobile approval dashboard
│   ├── mcp/
│   │   ├── protocol.py          # JSON-RPC 2.0 message framing
│   │   ├── sse.py               # SSE transport session manager
│   │   └── tools.py             # Registered MCP tools
│   ├── queue/
│   │   ├── models.py            # Queue job records & schemas
│   │   ├── repository.py        # SQLite atomic job lease & claim engine
│   │   └── worker.py            # Background async edge worker
│   ├── vault/
│   │   ├── crypto.py            # RFC 8785 canonical hash, PBKDF2 envelope encryption
│   │   ├── manager.py           # Replay nonce cache, action signer, secretless broker
│   │   └── models.py            # ActionIntent, SignedActionToken schemas
│   ├── config.py                # Pydantic v1 BaseSettings configuration
│   └── main.py                  # Application factory, lifespan, and exception handlers
├── scripts/
│   ├── setup_boot.sh            # Termux:Boot autostart installer
│   ├── stop_gateway.sh          # Clean daemon shutdown script
│   ├── sync_to_phone.ps1        # Fast SCP sync over Tailscale (Port 8022)
│   ├── test_hitl.py             # Cyber-physical actuation & approval test
│   ├── test_killswitch.py       # Zero-Trust scoping & Kill Switch test
│   ├── test_mcp_client.py       # Pure-Python MCP SSE client test
│   ├── test_queue.py            # SQLite queue & DLQ test
│   ├── test_vault.py            # Cryptographic signer & TOCTOU prevention test
│   └── watchdog.sh              # 24/7 supervisor loop for Termux
├── main.py                      # Root entrypoint shim
├── requirements.txt             # Pydantic v1 & FastAPI locked dependencies
└── android_termux_personal_gateway_architecture.md # Technical architecture specification
```

---

## 🚀 Getting Started

### 1. Requirements
* **Android Device**: Android 8.0+ (Tested on Samsung Galaxy A6+, Android 10, 32-bit ARM).
* **Apps**: [Termux](https://github.com/termux/termux-app) (F-Droid) + [Termux:API](https://github.com/termux/termux-api) + [Termux:Boot](https://github.com/termux/termux-boot).
* **Python Runtime**: Python 3.11+ (Python 3.14 on Termux).

### 2. Termux Environment Setup
```bash
pkg update -y
pkg install python git termux-api openssh -y
sshd
```

### 3. Deploy from Workstation
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync_to_phone.ps1
```

### 4. Running Argala on the Phone

#### Interactive Mode:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 24/7 Background Daemon Mode:
```bash
nohup bash scripts/watchdog.sh > /dev/null 2>&1 &
```

---

## 🧪 Verification & Testing

Run the automated test harnesses from your workstation:

```powershell
# Verify Zero-Trust capability scopes & Emergency Kill Switch
python .\scripts\test_killswitch.py

# Verify Cyber-Physical mobile approval & haptic alerts
python .\scripts\test_hitl.py

# Verify Cryptographic signing, TOCTOU prevention, and secretless broker
python .\scripts\test_vault.py

# Verify Durable queue, idempotency deduplication, and DLQ
python .\scripts\test_queue.py

# Verify Model Context Protocol (MCP) over Server-Sent Events
python .\scripts\test_mcp_client.py
```

---

## 🌐 Endpoints & Web Console

* **Visual Approval Dashboard & Kill Switch**: `http://<phone-ip>:8000/approvals` (or `/admin`)
* **Interactive OpenAPI Docs**: `http://<phone-ip>:8000/docs`
* **Admin Operational Status**: `http://<phone-ip>:8000/v1/admin?api_key=argala-dev-key-change-me`
* **Model Context Protocol**: `GET /v1/mcp/sse` & `POST /v1/mcp/messages`
* **Queue Ingestion**: `POST /v1/jobs` & `GET /v1/jobs/{id}`
* **Sovereign Vault**: `POST /v1/vault/sign`, `POST /v1/vault/verify`, `POST /v1/vault/broker`

---

## 📜 License
MIT License. Crafted for sovereign personal computing.
