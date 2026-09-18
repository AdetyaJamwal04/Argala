# Argala Ecosystem: Unit of Work Plan

## 1. What is Being Built and Why

### Context
Argala is a sovereign edge gateway, cryptographic credential vault, and cyber-physical Human-in-the-Loop (HITL) gatekeeper running on an Android device (Termux) connected via WireGuard mesh networking. 

We successfully proved the core architecture through an isolated demonstration in `demo_run/` (verifying secretless Gemini 3.8 Flash inference, physical phone vibration/speech actuation, and screen approval gating).

### What We Are Building
We are building a production-ready, reusable software ecosystem around Argala located in `eco_system/`. This transforms Argala from an isolated experiment into a daily driver platform for developers, autonomous AI agents, and DevOps pipelines.

The ecosystem consists of:
1. **The Official `argala` Python SDK (`eco_system/argala/`)**: A clean, fully typed library providing high-level programmatic access to Argala's REST, Vault, Queue, Actuation, and HITL APIs.
2. **Cyber-Physical Function Decorators (`@requires_approval`)**: A single-line Python decorator that gates any high-risk Python function behind physical phone vibration, voice announcement, and screen tap approval.
3. **The Sovereign AI Local Proxy (`argala proxy`)**: A local HTTP proxy on the developer's laptop (`127.0.0.1:8080`) that is API-compatible with OpenAI and Google Gemini. Developer tools (Cursor, VS Code extensions, scripts, LangChain) send inference requests to `localhost:8080`, and the proxy routes them through the phone's Sovereign Vault. **The laptop never holds or sees raw API keys.**
4. **Unified Developer & Ops CLI (`argala`)**: A command-line utility for monitoring node status, approving/rejecting HITL tickets, sending instant physical actuation cues (vibrate/speak/notify), starting the proxy, and controlling the sovereign kill switch.
5. **Pre-Built Agent Integrations**: Turnkey function declarations for Google's `google-genai` SDK and MCP clients.
6. **Gateway Actuation & MCP Upgrades**: Extending the phone's Termux control plane with a direct `/v1/hardware/actuate` endpoint and registering missing MCP tools (`android_request_approval`, `android_actuate`).

---

## 2. Scope & Explicit Non-Goals

### In-Scope
- Creating an installable package in `eco_system/` with `pyproject.toml` exposing the `argala` package and `argala` CLI.
- Developing `eco_system/argala/client.py`: Async & Sync client with retry, timing-safe auth, and response parsing.
- Developing `eco_system/argala/decorators.py`: `@requires_approval` decorator with configurable timeouts, risk levels, and polling handlers.
- Developing `eco_system/argala/proxy/server.py`: Local zero-trust AI proxy compatible with standard LLM endpoints.
- Developing `eco_system/argala/cli/main.py`: Full CLI (`status`, `actuate`, `approvals`, `proxy`, `lock`, `unlock`).
- Developing `eco_system/argala/integrations/genai.py`: Gemini-ready toolsets for agentic workflows.
- Developing runnable real-world examples in `eco_system/examples/`:
  - `01_gated_deployment.py` (DevOps pipeline gated by physical phone tap).
  - `02_sovereign_llm_client.py` (LLM inference via local proxy with zero local keys).
  - `03_autonomous_agent.py` (Gemini agent acting on phone sensors and actuators).
- Upgrading `app/` gateway routes (`routes_actuation.py`) and MCP tools (`app/mcp/tools.py`) to expose actuation directly.
- Maintaining the four living documents in `eco_system/docs/`: `plan.md`, `design.md`, `decisions.md`, `flow.md`.

### Explicit Non-Goals
- Modifying core database schemas in SQLite or altering the existing cryptographic hashing format (RFC 8785 canonical JSON must remain untouched).
- Building native Android APKs or Java/Kotlin apps (Termux Python + Termux:API remains the target runtime).
- Implementing multi-tenant cloud authentication (Argala is designed for sovereign personal computing with private WireGuard mesh access).
- Adding support for paid external cloud orchestrators (Kubernetes, AWS Lambda).

---

## 3. Step-by-Step Approach

### Phase 1: Foundation & Living Documentation Setup
1. Create `eco_system/docs/plan.md` (this file).
2. Create `eco_system/docs/design.md` detailing architecture, boundaries, and components.
3. Create `eco_system/docs/decisions.md` recording initial stack and design decisions.
4. Create `eco_system/docs/flow.md` tracing the end-to-end request flows.

### Phase 2: Gateway Control Plane Upgrades (`app/`)
1. Create `app/api/routes_actuation.py` implementing `POST /v1/hardware/actuate` with `hardware:actuate` scope verification.
2. Mount the actuation router in `app/api/router.py`.
3. Update `app/core/identity.py` to grant `"hardware:actuate"` and `"vault:broker"` scopes to `laptop-agent`.
4. Update `app/mcp/tools.py` to expose `android_request_approval` and `android_actuate` to MCP clients.
5. Update `app/queue/worker.py` to support `hardware.actuate` and `vault.broker` asynchronous job capabilities.

### Phase 3: Core SDK Implementation (`eco_system/argala/`)
1. Create `eco_system/pyproject.toml` defining package metadata, dependencies, and CLI entrypoint.
2. Create `eco_system/argala/models.py` with Pydantic models for tickets, telemetry, actuation, jobs, and vault payloads.
3. Create `eco_system/argala/client.py` implementing `ArgalaClient` (sync) and `AsyncArgalaClient`.
4. Create `eco_system/argala/decorators.py` implementing `@requires_approval`.
5. Create `eco_system/argala/__init__.py` exporting clean public APIs.

### Phase 4: Sovereign AI Local Proxy (`eco_system/argala/proxy/`)
1. Implement `eco_system/argala/proxy/server.py` using Python's standard `http.server` or lightweight ASGI/FastAPI.
2. Support `/v1/chat/completions` (OpenAI format) and `/v1beta/models/...` (Gemini format).
3. Translate inbound requests into `POST /v1/vault/broker` requests sent to the Android gateway.
4. Return responses in standard formats so clients work unmodified.

### Phase 5: Unified Developer CLI (`eco_system/argala/cli/`)
1. Implement `eco_system/argala/cli/main.py` using `argparse`.
2. Implement subcommands:
   - `status`: Show node health, battery, thermals, lock state.
   - `actuate`: Send haptic, speech, or notification alerts.
   - `approvals`: List pending tickets or watch & approve tickets interactively.
   - `proxy`: Start the Sovereign AI proxy.
   - `lock` / `unlock`: Remote emergency lockdown toggle.
   - `jobs`: Enqueue or check background tasks.

### Phase 6: Agent Integrations & Practical Examples
1. Implement `eco_system/argala/integrations/genai.py` providing Gemini tools.
2. Create practical, runnable examples in `eco_system/examples/`.
3. Create comprehensive `eco_system/README.md`.

### Phase 7: Verification & Documentation Refresh
1. Verify SDK against live edge node (`100.68.31.91:8000`).
2. Verify Sovereign Proxy by issuing curl / Python requests without API keys.
3. Update `design.md`, `decisions.md`, and `flow.md` with operational realities and learnings.

### Phase 8: System Audit, Hardening & Remediation
1. **Audit Gateway Codebase**: Comprehensive review of cryptographic signing, vault brokerage, queue worker, and MCP tools.
2. **SSRF Guard Implementation**: Hardened `app/vault/manager.py` with strict public IP validation to prevent loopback/metadata exploits.
3. **MCP Tool & Queue Worker Repair**: Synchronized schemas for `android_vault_broker` and `android_request_approval`, and converted worker calls to async.
4. **Pydantic Polyfill**: Implemented v1/v2 compatibility in `app/config.py` for seamless execution across Termux and desktop.
5. **CORS & Auth Defense**: Hardened default CORS configuration and added startup warning for default API keys.
6. **Integration Verification**: Verified live on Android Termux node (`100.68.31.91:8000`) via PowerShell and automated unit test suite (`tests/test_audit_remediation.py`).


---

## 4. Open Questions & Assumptions

### Assumptions
1. **Network Connectivity**: The Android edge node is reachable over private Tailscale IP (`100.68.31.91:8000`) or localhost if testing on-device.
2. **Python Environment**: The ecosystem works cleanly on Python 3.10+ (both standard Windows/macOS/Linux desktops and 32-bit/64-bit Termux Python 3.11+).
3. **Zero Secrets on Workstation**: The Sovereign Proxy assumes the phone's vault already holds or can be provisioned with the necessary API keys (`gemini_api_key`), so the developer machine remains keyless.
4. **Standard Library Fallbacks**: CLI and proxy tools should have minimal heavy dependencies so they can run in lightweight environments without needing massive wheels.
