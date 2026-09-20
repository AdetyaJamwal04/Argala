# Argala Sovereign Ecosystem: System Design

## 1. Architectural Philosophy & Mental Model

The Argala Ecosystem operates under a strict principle of **Sovereign Physical Asymmetry**:
- **Workstations and Clouds compute and reason**, but are fundamentally untrusted or high-risk surfaces (vulnerable to secret leaks, prompt injections, and runaway loops).
- **Argala (the Android Phone) holds the cryptographic root of trust and cyber-physical authority**. It holds external secrets in an encrypted vault, monitors hardware state, enforces human approval through physical sound, touch, and screen prompts, and maintains a durable, crash-resilient queue.

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           WORKSTATION / AGENT                          │
  │                                                                        │
  │   [Your Code / CI / Scripts]        [IDE / Cursor / AutoGen]           │
  │              │                                  │                      │
  │       @requires_approval                 OpenAI / Gemini format        │
  │              │                                  │                      │
  │              ▼                                  ▼                      │
  │      ┌───────────────┐                  ┌───────────────┐              │
  │      │  Argala SDK   │                  │Sovereign Proxy│              │
  │      │(client/models)│                  │ (:8080 local) │              │
  │      └───────┬───────┘                  └───────┬───────┘              │
  │              │                                  │                      │
  └──────────────┼──────────────────────────────────┼──────────────────────┘
                 │                                  │
                 │   Encrypted WireGuard Mesh       │
                 │   (HMAC Auth / Token Headers)    │
                 ▼                                  ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           ARGALA EDGE NODE                             │
  │                        (Samsung Galaxy A6+ / Termux)                   │
  │                                                                        │
  │   ┌────────────────────────────────────────────────────────────────┐   │
  │   │  FastAPI Gateway (/v1)                                         │   │
  │   │  ├── /health & /telemetry   (Battery, RAM, Thermals)           │   │
  │   │  ├── /hardware/actuate      (Direct Vibrate, TTS, Notify)      │   │
  │   │  ├── /approvals             (Cyber-Physical HITL Tickets)      │   │
  │   │  ├── /vault                 (Action Signing & Secret Broker)   │   │
  │   │  ├── /jobs                  (SQLite WAL Durable Queue)         │   │
  │   │  └── /mcp/sse               (Model Context Protocol Bridge)    │   │
  │   └────────────────────────────────┬───────────────────────────────┘   │
  │                                    │                                   │
  │             ┌──────────────────────┴──────────────────────┐            │
  │             ▼                                             ▼            │
  │   ┌───────────────────┐                         ┌───────────────────┐  │
  │   │ Cyber-Physical    │                         │ Sovereign Vault   │  │
  │   │ Actuation Bridge  │                         │ & External Broker │  │
  │   │(Vibrate/TTS/Shade)│                         │ (Secret Injection)│  │
  │   └───────────────────┘                         └─────────┬─────────┘  │
  └───────────────────────────────────────────────────────────┼────────────┘
                                                              │ Secretless
                                                              ▼ Outbound
                                                    ┌───────────────────┐
                                                    │ Google / OpenAI   │
                                                    │ Cloud APIs        │
                                                    └───────────────────┘
```

---

## 2. Component Breakdown & Responsibilities

### 2.1 The Official `argala` Python SDK (`eco_system/argala/`)

- **`argala.client.ArgalaClient` / `AsyncArgalaClient`**:
  - **Responsibility**: Provides synchronous and asynchronous HTTP abstractions over the Argala REST API.
  - **Boundaries**: Handles connection pooling, request authentication headers (`X-API-Key`, `X-Principal-ID`), timeout configurations, automatic exponential backoff for transient failures, and strongly typed response deserialization.
  - **Key Contracts**:
    - `get_telemetry() -> NodeTelemetry`: Retrieves battery percentage, charging status, thermals, RAM.
    - `request_approval(action, target, risk_level, prompt, timeout_seconds) -> ApprovalTicket`: Dispatches HITL ticket with physical phone alert.
    - `wait_for_approval(ticket_id, poll_interval) -> ApprovalStatus`: Blocks/polls until human grants or denies access.
    - `actuate(vibrate_ms, speak_text, notification_title, notification_content) -> ActuationResult`: Triggers instant physical alert.
    - `broker_request(service, method, path, body, headers) -> BrokerResponse`: Forwards secretless outbound request through phone vault.
    - `submit_job(capability, payload, idempotency_key) -> JobRecord`: Submits persistent task to phone SQLite queue.

- **`argala.decorators.@requires_approval`**:
  - **Responsibility**: Intercepts high-risk function invocations in any Python application.
  - **Behavior**:
    1. Extracts runtime function arguments.
    2. Dispatches a physical approval ticket to the phone with risk level and custom prompt.
    3. Triggers haptic vibration and voice alert on the phone ("Approval required for action X").
    4. Polls until human accepts on the mobile screen.
    5. If accepted: function executes normally and returns result.
    6. If rejected or timed out: raises `ArgalaApprovalDeniedError` or `ArgalaTimeoutError`, aborting execution before damage can occur.

### 2.2 Sovereign AI Local Proxy (`eco_system/argala/proxy/`)

- **`SovereignProxy`**:
  - **Responsibility**: Acts as a drop-in local LLM server running on the workstation (`http://127.0.0.1:8080`).
  - **Boundaries**:
    - Inbound: Accepts standard OpenAI-formatted `/v1/chat/completions` or Gemini-formatted `/v1beta/models/...` requests from local developer tools (Cursor, VS Code extensions, LangChain, CLI scripts).
    - Outbound: Never inspects or injects raw API keys locally. Wraps the payload and dispatches an authenticated `POST /v1/vault/broker` call to the Argala phone node.
    - Result: The phone decrypts the stored key, executes the outbound request to Google or OpenAI over its internet connection, and returns the response back to the proxy, which returns standard JSON to the workstation tool.

### 2.3 Unified Developer CLI (`eco_system/argala/cli/`)

- **Entrypoint**: `argala` console command (and `python -m argala.cli`).
- **Subcommands**:
  - `argala status`: Pretty-printed table showing connection latency, phone battery, CPU/battery temperature, active queue jobs, and lockdown status.
  - `argala actuate`: CLI bridge to send instant physical alerts (e.g. `argala actuate --speak "Deployment failed" --vibrate 600`).
  - `argala approvals`: Live monitoring stream for pending approval tickets with terminal approval commands.
  - `argala proxy`: Starts the local zero-trust sovereign proxy on a specified port.
  - `argala lock` / `argala unlock`: Sovereign emergency deadbolt control to quarantine compromised agents.

### 2.4 Gateway Upgrades & Hardening (`app/`)

- **Direct Actuation Endpoint (`POST /v1/hardware/actuate`)**:
  - Direct route protected by the `hardware:actuate` capability scope.
  - Executes non-blocking Termux API calls (`termux-vibrate`, `termux-tts-speak`, `termux-notification`).
- **MCP Expansion (`app/mcp/tools.py`)**:
  - Registers `android_request_approval`, `android_actuate`, and `android_vault_broker` into Anthropic's Model Context Protocol tool registry.
  - Aligns tool parameter schemas (`secret_id`, `url`, `method`, `header_name`, `header_prefix`) and uses non-blocking asynchronous broker calls.
  - Enables AI assistants in IDEs (Antigravity, Claude Desktop, Cursor) to interact with physical phone hardware directly.
- **Queue Worker Capabilities (`app/queue/worker.py`)**:
  - Supports `hardware.actuate` and `vault.broker` asynchronous job capabilities.
  - Asynchronously brokers outbound requests using `broker_http_request`.
- **SSRF Hardened Outbound Broker (`app/vault/manager.py`)**:
  - Validates all destination IP addresses prior to HTTP dispatch.
  - Blocks loopback (`127.0.0.0/8`), private subnets (RFC 1918), link-local (`169.254.0.0/16`), and metadata endpoints to prevent internal network pivoting.
- **Durable Replay Nonce Cache Pruning (`app/vault/manager.py`)**:
  - Periodically purges expired verification nonces from the SQLite datastore to bound disk consumption on mobile storage.

---

## 3. Data Flow & Security Boundaries

1. **Authentication**: All workstation-to-phone traffic carries an API key and principal identifier mapped to least-privilege capability scopes. Unset or default keys log explicit warnings on gateway initialization.
2. **Confidentiality**: Zero secrets are persisted on the workstation. All high-privilege credentials live inside the phone's AES-256 / PBKDF2 encrypted vault.
3. **Integrity & Non-Repudiation**: Approvals produce signed tokens with RFC 8785 canonical hashes and expiration nonces preventing replay and TOCTOU tampering. Nonces are verified against an on-device SQLite ledger.
4. **Network Isolation (SSRF Guard)**: Brokered requests cannot target the local phone loopback or internal subnets, confining outbound agent traffic strictly to public internet targets.
5. **CORS Boundary**: Configured with explicit local origins; credentialed cross-origin requests with wildcard origins are strictly prohibited.

