# Android Termux 24/7 Personal API Gateway & Control Plane

## Executive Summary

This architecture treats an Android device running Termux not as the
entire AI agent, but as a persistent, security-sensitive edge gateway
and personal control plane.

The Android gateway provides:

-   API routing
-   Secure credential brokering
-   Encrypted storage
-   Human-in-the-loop approvals
-   Durable job queuing
-   Event dispatch
-   Health monitoring
-   Audit logging
-   Device identity and access control

The laptop and cloud remain the computational data plane for AI
inference, RAG, agentic workflows, and heavyweight workloads.

> **The laptop thinks. The cloud computes. The Android gateway
> authorizes, protects, queues, and connects.**

------------------------------------------------------------------------

## 1. Core Architecture

``` text
                         ┌─────────────────────┐
                         │      Android        │
                         │       Termux        │
                         │                     │
                         │  Secure Gateway     │
                         │  API Router         │
                         │  Credential Vault   │
                         │  HITL Interface     │
                         │  Event Dispatcher   │
                         │  Health Monitor     │
                         └──────────┬──────────┘
                                    │
                         Encrypted authenticated
                              communication
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
           ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
           │   Laptop    │   │   Cloud VM  │   │ Other APIs  │
           │ AI Runtime  │   │ Backend     │   │ Services    │
           └─────────────┘   └─────────────┘   └─────────────┘
```

The phone functions as a mobile, cryptographically authenticated
infrastructure appliance.

------------------------------------------------------------------------

## 2. Responsibilities of the Termux Node

``` text
Termux
│
├── gateway/
│   ├── API Gateway
│   ├── Authentication
│   ├── Routing
│   └── Rate Limiting
│
├── vault/
│   ├── Encrypted Secrets
│   ├── Token Retrieval
│   ├── Key Rotation
│   └── Credential Policies
│
├── orchestrator/
│   ├── Job Queue
│   ├── Event Processing
│   ├── Retry Manager
│   └── Service Registry
│
├── hitl/
│   ├── Approval Requests
│   ├── User Notifications
│   ├── Approval Expiry
│   └── Action Confirmation
│
├── monitoring/
│   ├── Health Checks
│   ├── Heartbeats
│   ├── Connectivity
│   └── Resource Monitoring
│
└── storage/
    ├── SQLite
    ├── Encrypted Metadata
    ├── Audit Logs
    └── Local Queue
```

Heavy model inference should remain on the laptop or cloud unless a
lightweight local model is specifically needed.

------------------------------------------------------------------------

## 3. Hybrid Communication Model (Durable Pull + Low-Latency Push)

A robust edge design must balance two conflicting requirements:
1. **Disconnection resilience**: The Android device may lose connectivity, change networks, or enter low-power states.
2. **Interactive responsiveness**: When an agent requests human approval, round-trip latency should be sub-second when the device is reachable.

To achieve both, the gateway implements a **hybrid model**:

``` text
┌─────────────────────────────────────────────────────────────┐
│                      HYBRID TRANSPORT                       │
├──────────────────────────────┬──────────────────────────────┤
│ 1. Asynchronous Task Queue   │ 2. Real-Time HITL & Events   │
│    (Durable Pull)            │    (Low-Latency Push / SSE)  │
├──────────────────────────────┼──────────────────────────────┤
│ • SQLite persistent storage  │ • Server-Sent Events (SSE)   │
│ • Lease-based worker polling │ • WebSocket event stream     │
│ • Survives reboots & Doze    │ • Instant push notifications │
│ • Idempotency & dead-letter  │ • Sub-second approval loop   │
└──────────────────────────────┴──────────────────────────────┘
```

### Communication Flow:
* **Background Jobs (Durable Pull)**: Agents and workers submit and retrieve long-running batch jobs via persistent queues. Disconnections do not result in dropped tasks.
* **Human-in-the-Loop & Alerts (Push over SSE with Polling Fallback)**: The edge gateway pushes real-time approval requests over persistent SSE/WebSocket streams. If the connection drops, agents fall back to polling the durable SQLite queue until the gateway reconnects.

------------------------------------------------------------------------

## 4. Network Topology

Recommended topology:

``` text
                    Internet
                       │
                       ▼
                 Secure Mesh VPN
                       │
          ┌────────────┴────────────┐
          │                         │
       Laptop                    Android
          │                         │
          └────── Private Mesh ────┘
```

Preferred technologies:

-   WireGuard
-   Tailscale
-   Headscale
-   Cloudflare Tunnel where appropriate
-   mTLS over private networking
-   Reverse SSH tunnels for limited scenarios

A mesh VPN is generally preferable to exposing the Termux API directly
to the public internet.

------------------------------------------------------------------------

## 5. API Gateway & Model Context Protocol (MCP) Interface

Avoid arbitrary shell execution endpoints (`POST /execute`).

The gateway exposes capabilities through two complementary interfaces:
1. **Standard REST Endpoints**: For programmatic HTTP clients and curl.
2. **Model Context Protocol (MCP) over SSE/HTTP**: The native standard for AI agents (Antigravity IDE, Claude Desktop, Cursor, LangGraph) to discover and execute tools without bespoke glue code.

### MCP Interface Architecture

``` text
AI Agent / IDE (Claude / Antigravity / LangGraph)
                     │
                     │ MCP JSON-RPC 2.0 (over SSE / HTTP)
                     ▼
             ┌───────────────┐
             │  MCP Endpoint │
             │  /mcp/sse     │
             └───────┬───────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
MCP Tools       MCP Resources   MCP Prompts
• sign_action   • telemetry     • security_policy
• broker_call   • pending_hits  • incident_audit
• send_alert    • vault_status
```

### Capability-based pattern (REST & MCP Tools)

``` http
POST /v1/services/gmail/send-email
POST /v1/services/calendar/create-event
POST /v1/services/secrets/get
POST /v1/services/browser/request-approval
POST /v1/services/agent/submit-job
POST /v1/services/notifications/send
POST /mcp/messages (JSON-RPC 2.0 tool execution)
```

Each request should be evaluated based on:

-   Requesting principal (authenticated via API key or mTLS)
-   Requested capability
-   Target resource
-   Scope
-   Risk level
-   Policy requirements
-   Whether human approval is required

Example capability payload:

``` json
{
  "request_id": "req_92af",
  "principal": "laptop-agent",
  "capability": "email.send",
  "resource": "gmail",
  "parameters": {
    "to": "someone@example.com",
    "subject": "Deployment update",
    "body": "..."
  },
  "risk_level": "high",
  "requires_approval": true
}
```

------------------------------------------------------------------------

## 6. Capability-Based Security

The laptop should not possess every long-lived credential.

### Traditional model

``` text
Laptop stores:
- Gmail token
- GitHub token
- Cloud API keys
- Database passwords
- Service credentials
```

### Secretless execution model

``` text
Laptop requests capability
        ↓
Android validates policy
        ↓
Android retrieves credential internally
        ↓
Android executes or brokers operation
        ↓
Laptop receives result, not the secret
```

For example:

``` text
Laptop → Request "Create GitHub issue"
Android → Validate scope
Android → Use GitHub credential internally
Android → Return operation result
```

This minimizes credential exposure.

------------------------------------------------------------------------

## 7. Encrypted Storage Vault

The vault should use multiple layers of protection.

### Recommended layers

1.  Android filesystem encryption
2.  Application-level authenticated encryption
3.  Strong key derivation
4.  Envelope encryption
5.  Separate recovery mechanism

Conceptual design:

``` text
Android Hardware-backed Security
             │
             ▼
       Key Encryption Key
             │
             ▼
       Encrypted Vault
             │
             ▼
     Encrypted SQLite / Files
```

Recommended primitives:

-   AES-256-GCM or another well-reviewed AEAD construction
-   Argon2id for password-based key derivation
-   Android Keystore where integration is practical
-   Separate data-encryption keys and key-encryption keys

### Envelope encryption

``` text
Master Key
   │
   ├── Encrypts Data Encryption Key
   │
   ▼
Data Encryption Key
   │
   ├── Encrypts Gmail token
   ├── Encrypts GitHub token
   ├── Encrypts API keys
   └── Encrypts private configuration
```

------------------------------------------------------------------------

## 8. Never Return Raw Secrets by Default

Avoid endpoints such as:

``` http
GET /vault/github-token
```

Prefer operation brokering:

``` http
POST /vault/execute
{
  "service": "github",
  "operation": "create_issue",
  "parameters": {}
}
```

The gateway retrieves and uses the secret internally.

The agent receives the result of the operation, not the underlying
credential.

------------------------------------------------------------------------

## 9. Human-in-the-Loop System

The Android phone is an ideal human trust boundary because it is
physically close to the user.

Potential approval-triggering actions:

-   Sending email
-   Publishing content
-   Making payments
-   Deleting files
-   Deploying production systems
-   Modifying infrastructure
-   Accessing sensitive information
-   Rotating security credentials

Example flow:

``` text
Agent wants to perform sensitive action
                ↓
Gateway creates approval request
                ↓
Phone notification appears
                ↓
User reviews action
                ↓
Approve / Reject / Inspect
                ↓
Gateway executes only if authorized
```

Approval object:

``` json
{
  "approval_id": "apr_123",
  "action": "send_email",
  "risk": "high",
  "summary": "Send email to client",
  "expires_at": "...",
  "status": "pending"
}
```

------------------------------------------------------------------------

## 10. Cryptographically Bound Approvals

Approval should be bound to the exact action rather than represented by
a simple Boolean.

Create a canonical action hash:

``` text
hash(
  action_type,
  target,
  parameters,
  requester,
  timestamp,
  nonce
)
```

Approval token:

``` json
{
  "request_hash": "...",
  "approved_by": "user",
  "issued_at": "...",
  "expires_at": "...",
  "nonce": "...",
  "signature": "..."
}
```

If the action changes after approval, the hash changes and the approval
becomes invalid.

This helps prevent approval substitution and time-of-check/time-of-use
problems.

------------------------------------------------------------------------

## 11. Risk-Based Approval Policies

Example policy tiers:

  Risk Level   Policy
  ------------ -------------------------------------------
  0            Automatic
  1            Automatic with audit
  2            Approval outside normal scope
  3            Always require human approval
  4            Human approval plus explicit confirmation

Example actions:

  Action                           Suggested Policy
  -------------------------------- -------------------------------
  Read public weather              Automatic
  Read local non-sensitive notes   Automatic
  Read Gmail                       Scoped permission
  Send email                       Human approval
  Delete cloud resources           Human approval + confirmation
  Financial transaction            Explicit human confirmation
  Modify vault policy              Administrative approval
  Rotate master key                Manual-only

------------------------------------------------------------------------

## 12. Notification and Approval Interfaces

Start simple and evolve.

### Stage 1: CLI

``` text
approve req_123
reject req_123
```

### Stage 2: Termux notifications

Use Termux notification capabilities to alert the user.

### Stage 3: Secure local web UI

A local dashboard can show:

-   Pending approvals
-   Service status
-   Recent jobs
-   Audit events
-   Vault state
-   Device connectivity

### Stage 4: Native Android application

Potential features:

-   Approval inbox
-   Vault unlock
-   Service status
-   Audit logs
-   Emergency kill switch
-   Device pairing
-   Session revocation

The native app should come after the backend security model is stable.

------------------------------------------------------------------------

## 13. Event-Driven Architecture

Rather than allowing every backend to directly communicate with every
other service, use the gateway as an event broker.

``` text
                    ┌───────────────┐
                    │ Android       │
                    │ Event Gateway │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
       Gmail             Calendar          GitHub
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                         Agent
```

Example event:

``` json
{
  "event_type": "approval.completed",
  "event_id": "...",
  "source": "android-gateway",
  "timestamp": "...",
  "payload": {}
}
```

Potential transports:

-   SQLite-backed queue initially
-   Redis Streams
-   NATS JetStream
-   MQTT
-   RabbitMQ
-   WebSocket
-   Server-Sent Events

For the first version, SQLite plus HTTPS polling or WebSockets is
sufficient.

------------------------------------------------------------------------

## 14. Offline-First and Store-and-Forward Behavior

The Android gateway should continue to function during temporary network
outages.

Example:

``` text
External webhook
      ↓
Android Gateway
      ↓
Durable SQLite queue
      ↓
Laptop reconnects
      ↓
Laptop receives event
```

This allows the phone to:

-   Receive webhooks
-   Store events
-   Queue tasks
-   Notify the user
-   Deliver tasks when workers reconnect

------------------------------------------------------------------------

## 15. Android Reliability Constraints

Android is not equivalent to a Linux server running systemd.

Potential issues include:

-   Doze mode
-   Background process termination
-   Battery optimization
-   Memory pressure
-   Device reboots
-   Network changes
-   App suspension
-   Battery depletion
-   OEM-specific process killing

Therefore, the architecture must not assume that the phone is
permanently available.

Required reliability mechanisms:

-   Durable queues
-   Idempotency keys
-   Retry policies
-   Lease-based job claiming
-   Heartbeats
-   State reconciliation
-   Reconnection logic
-   Watchdogs
-   Boot recovery
-   Battery and connectivity monitoring

Example lease model:

``` text
Job submitted
   ↓
Durably stored
   ↓
Worker claims job
   ↓
Lease acquired
   ↓
Worker crashes
   ↓
Lease expires
   ↓
Job becomes available again
```

------------------------------------------------------------------------

## 16. Avoiding the Phone as a Single Point of Failure

Separate availability-critical services from security-sensitive
services.

### Services that should continue without the phone

-   Local AI inference
-   Non-sensitive RAG
-   Public API calls
-   Local notes
-   Basic task execution
-   Non-sensitive automation

### Services that may wait for the phone

-   Credential access
-   Email sending
-   Payments
-   Production deployments
-   Sensitive data access
-   Human approvals

``` text
Phone offline
    │
    ├── Non-sensitive tasks → Continue
    │
    └── Sensitive tasks → Queue until gateway returns
```

This makes the phone a security dependency rather than an availability
dependency.

------------------------------------------------------------------------

## 17. Control Plane vs Data Plane

This is the cleanest systems-design abstraction.

### Control Plane

Runs primarily on Android:

-   Authentication
-   Authorization
-   Secrets
-   Policy
-   Human approvals
-   Device identity
-   Audit logs
-   Routing
-   Revocation

### Data Plane

Runs on laptop and cloud:

-   LLM inference
-   RAG
-   LangGraph workflows
-   Code execution
-   Heavy computation
-   GPU jobs
-   Backend workers
-   External service operations

``` text
                 CONTROL PLANE
              ┌─────────────────┐
              │ Android Gateway  │
              │ Vault            │
              │ Policy           │
              │ HITL             │
              │ Identity         │
              └────────┬────────┘
                       │
                Authorized actions
                       │
              ┌────────▼────────┐
              │    DATA PLANE   │
              │ Laptop / Cloud  │
              │ Agents / APIs   │
              │ Workers         │
              └─────────────────┘
```

------------------------------------------------------------------------

## 18. Recommended Technology Stack (Tailored for Termux)

### Gateway Runtime
- **Python**: 3.14 (32-bit ARM userspace)
- **Framework**: FastAPI (`fastapi<0.115` to ensure Pydantic v1 compatibility)
- **Validation**: Pydantic (`pydantic<2` / `1.10.26`)
- **Server**: Uvicorn (`uvicorn<0.31`)
- **Protocol**: Model Context Protocol (MCP) JSON-RPC 2.0 over SSE / HTTP

### Storage & Queue
- **Database**: SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)
- **Queue**: Durable SQLite queue with lease timeouts, retries, and dead-lettering

### Cryptography & Security
- **Hashing & Signing**: HMAC-SHA256, SHA-256 (standard library `hashlib`, `hmac`)
- **AEAD Encryption**: AES-256-GCM / ChaCha20-Poly1305 via `python-cryptography`
- **Key Derivation**: PBKDF2-HMAC-SHA256 (standard library) / Argon2id

### Networking & Transport
- **Mesh VPN**: Tailscale (WireGuard-based private mesh with permanent `100.x.y.z` IP)
- **Local Fallback**: USB ADB port forwarding (`adb forward tcp:8000 tcp:8000`)
- **Tunneling**: Cloudflare Tunnel (`cloudflared`) / SSH reverse tunnel where needed

### Android Hardware & Keep-Alive
- **Process Keep-Alive**: `termux-wake-lock` + Android Unrestricted Battery Optimization
- **Hardware Bridge**: `termux-api` package (vibration, notifications, TTS, battery)

---

## 19. Suggested Repository Structure

``` text
android-gateway/
│
├── app/
│   ├── main.py                   # FastAPI lifespan, router mounting, CORS
│   ├── config.py                 # Pydantic v1 BaseSettings
│   │
│   ├── api/
│   │   ├── router.py             # Root API router
│   │   ├── routes_auth.py        # Authentication & API key validation
│   │   ├── routes_jobs.py        # Job submission, status, and polling
│   │   ├── routes_vault.py       # Secretless service brokering
│   │   ├── routes_approval.py    # HITL ticket creation, resolution & webhooks
│   │   ├── routes_telemetry.py   # Battery, thermals, and network health
│   │   └── routes_mcp.py         # MCP protocol endpoints (SSE & JSON-RPC)
│   │
│   ├── mcp/
│   │   ├── protocol.py           # JSON-RPC 2.0 framing & MCP message validation
│   │   ├── tools.py              # Registered MCP tool definitions
│   │   └── sse.py                # Server-Sent Events stream handler
│   │
│   ├── core/
│   │   ├── policy_engine.py      # Capability & risk evaluator
│   │   ├── identity.py           # Principal identity & token verification
│   │   ├── crypto.py             # Canonical action hashing & HMAC signing
│   │   ├── audit.py              # Structured tamper-evident audit logger
│   │   └── rate_limiter.py       # Token-bucket rate limiting
│   │
│   ├── vault/
│   │   ├── manager.py            # Vault lifecycle (lock, unlock, status)
│   │   ├── keyring.py            # Ephemeral in-memory key storage
│   │   └── envelope.py           # AES-GCM / ChaCha20 envelope encryption
│   │
│   ├── queue/
│   │   ├── models.py             # Job, lease, and dead-letter schemas
│   │   ├── repository.py         # SQLite durable queue queries
│   │   └── worker.py             # Background task processor
│   │
│   ├── hitl/
│   │   ├── approval_manager.py   # Pending approval queue & expiration
│   │   ├── notifier.py           # Termux notifications & haptics
│   │   └── web_ui.py             # Mobile-friendly web approval UI
│   │
│   ├── hardware/
│   │   ├── termux_bridge.py      # Async subprocess wrapper for termux-api
│   │   └── telemetry.py          # Battery, memory, and thermal reader
│   │
│   └── services/
│       ├── github.py             # Brokered GitHub operations
│       ├── gmail.py              # Brokered email operations
│       └── generic_http.py       # Outbound authenticated HTTP broker
│
├── migrations/                   # SQLite schema migrations
├── tests/                        # Automated unit & integration tests
├── scripts/
│   ├── start_server.sh           # Daemon starter with wake-lock
│   ├── sync_to_phone.ps1         # Windows-to-Termux SCP sync over ADB/SSH
│   └── setup_termux.sh           # Dependencies bootstrap script
│
├── requirements.txt              # Pydantic<2, FastAPI<0.115 locked deps
└── README.md
```

------------------------------------------------------------------------

## 20. Service Lifecycle on Termux

Useful components include:

-   Termux:Boot
-   Termux:API
-   termux-services

Possible supervised services:

``` text
gateway
worker
watchdog
backup
health-monitor
```

However, Termux process supervision should be combined with
Android-specific measures:

-   Disable battery optimization for Termux where possible
-   Use wake locks only when justified
-   Implement restart policies
-   Persist all important state
-   Recover services after boot
-   Handle network reconnection

------------------------------------------------------------------------

## 21. Personal Agent Trust Broker

The gateway creates a powerful separation:

``` text
Agent:
  "I want to send this email."

Gateway:
  "You are not automatically authorized."

Gateway:
  "Requesting human approval."

Human:
  "Approve."

Gateway:
  "Execute the exact approved operation."
```

The agent becomes:

> **An autonomous planner, but not an autonomous authority.**

This is one of the strongest design principles for a personal agent
infrastructure.

------------------------------------------------------------------------

## 22. Personal Agent Identity Model

Each backend should have its own cryptographic identity.

``` text
Android Gateway Identity
       │
       ├── Laptop Agent Identity
       ├── Cloud Worker Identity
       ├── Browser Agent Identity
       └── Mobile Client Identity
```

Example capability policy:

``` json
{
  "principal": "laptop-agent",
  "permissions": [
    "vault.read:gmail.readonly",
    "jobs.submit",
    "approval.request"
  ]
}
```

The laptop should not automatically receive access to unrelated secrets
or high-risk operations.

This resembles a miniature zero-trust service mesh for personal
infrastructure.

------------------------------------------------------------------------

## 23. Emergency Kill Switch

The phone can expose emergency controls such as:

-   Disable all agents
-   Revoke laptop identity
-   Revoke cloud workers
-   Lock the vault
-   Rotate session keys
-   Cancel pending high-risk jobs
-   Disable a compromised service

Example:

``` text
Phone → Emergency Lockdown
       ↓
Gateway revokes active tokens
       ↓
Laptop sessions invalidated
       ↓
Cloud workers lose access
       ↓
Pending high-risk jobs cancelled
```

------------------------------------------------------------------------

## 24. Backup and Recovery

The vault must not exist only on the Android device, but backups must
never expose plaintext secrets.

Recommended approach:

``` text
Encrypted Vault Backup
       │
       ├── Offline encrypted backup
       ├── Encrypted cloud backup
       └── Recovery key stored separately
```

A cloud backup should be useless by itself without the required recovery
factor.

------------------------------------------------------------------------

## 25. Recommended Implementation Roadmap

### Phase 1 --- Distributed Transport & Basic Gateway (Current Milestone)
- **Networking**: Tailscale mesh configuration on Android & Windows; verify global connectivity.
- **Runtime**: FastAPI + Pydantic v1 baseline in `~/addy_space`.
- **System**: Termux `wake-lock` and battery optimization configuration.
- **Endpoints**: `/health`, `/telemetry` (battery, CPU, memory), and API-key authenticated ping.
- **Tooling**: Windows-to-Termux synchronization script (`sync_to_phone.ps1`).

### Phase 2 --- Model Context Protocol (MCP) & Real-Time Event Stream
- **MCP SSE Transport**: `/mcp/sse` endpoint for agent connections.
- **Protocol Framing**: JSON-RPC 2.0 message handler for tool discovery and execution.
- **Hybrid Transport**: SSE stream for instant push alerts + SQLite backing.

### Phase 3 --- Durable SQLite Queue & Lease Manager
- **Storage**: SQLite with WAL mode schema for jobs and leases.
- **Queue Engine**: Idempotency keys, lease expiration, worker claim protocol, dead-letter queue.
- **Store-and-Forward**: Offline task ingestion and replay on reconnect.

### Phase 4 --- Cryptographic Signer & Capability Vault
- **Cryptographic Primitives**: Canonical action hashing `hash(action, target, params, requester, timestamp, nonce)` + HMAC-SHA256 signing.
- **Secretless Execution**: Service adapters (e.g. GitHub/HTTP broker) using internal secrets.
- **Envelope Encryption**: Memory-held KEK derived via PBKDF2 for encrypting credential store.

### Phase 5 --- Human-in-the-Loop (HITL) Subsystem
- **Approval Queue**: Pending ticket lifecycle, timeout, and cancellation.
- **Physical Actuation**: Termux notifications with action buttons, vibration, and TTS alerts.
- **Mobile Web Console**: Lightweight, mobile-optimized dark-mode approval dashboard.

### Phase 6 --- Zero Trust & Native Companion
- **Device Identity**: Ed25519 identity tokens and per-agent capability policies.
- **Emergency Kill Switch**: Instant session revocation and vault lockdown.
- **Native Android App**: Companion APK integrating Android Keystore and native biometric prompts.

------------------------------------------------------------------------

## 26. Final Recommended Architecture

``` text
                         ┌──────────────────────────────┐
                         │       PERSONAL CONTROL       │
                         │                              │
                         │ Android + Termux             │
                         │                              │
                         │ ┌──────────────────────────┐ │
                         │ │ API Gateway              │ │
                         │ │ Auth / Policy            │ │
                         │ │ Encrypted Vault          │ │
                         │ │ HITL Approval             │ │
                         │ │ Event Queue              │ │
                         │ │ Audit Log                │ │
                         └──────────────┬───────────────┘
                                        │
                              Private encrypted mesh
                                        │
          ┌─────────────────────────────┼────────────────────────────┐
          │                             │                            │
┌─────────▼─────────┐       ┌───────────▼──────────┐      ┌──────────▼─────────┐
│ Laptop AI Runtime │       │ Cloud Agent Runtime  │      │ External Services  │
│                   │       │                      │      │                    │
│ LangGraph         │       │ Heavy inference      │      │ Gmail              │
│ RAG               │       │ GPU jobs             │      │ GitHub             │
│ Local models      │       │ Scheduled tasks      │      │ Calendar           │
│ Tool execution    │       │ APIs                 │      │ Browser            │
└───────────────────┘       └──────────────────────┘      └────────────────────┘
```

## Guiding Principle

> **The laptop thinks. The cloud computes. The Android gateway
> authorizes, protects, queues, and connects.**

This architecture provides a practical path from a Termux-based personal
utility to a personal zero-trust control plane and edge orchestration
platform.
