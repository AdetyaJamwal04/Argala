# Argala Sovereign Ecosystem: Decision Log

This log records architectural and technical decisions made during the evolution of the Argala Ecosystem, documenting the context, alternatives considered, and rationale.

---

## Decision 001: Ecosystem Directory Architecture (`eco_system/`)
- **Date**: 2026-09-17 (Phase 1: Project Scaffolding)
- **What was decided**: Place all ecosystem client tooling, SDK, local proxy, CLI, and examples inside the dedicated `eco_system/` root folder as an installable Python package, rather than polluting the root or phone gateway directory (`app/`).
- **Alternatives considered**:
  1. Adding SDK files directly under `app/client/`: Rejected because `app/` is the edge phone gateway codebase deployed to Termux. Mixing laptop-side tooling with phone daemon code causes dependency bloat and confusion.
  2. Keeping ad-hoc scripts in `demo_run/`: Rejected because demo scripts are not reusable, typed, or packagable for external projects.
- **Why this won**: Provides clean separation of concerns: `app/` is the edge hardware node runtime, while `eco_system/` is the developer-facing SDK and tooling suite that can be distributed, packaged, or imported anywhere.

---

## Decision 002: Dual Sync/Async Client Design (`ArgalaClient` & `AsyncArgalaClient`)
- **Date**: 2026-09-17 (Phase 1: SDK Design)
- **What was decided**: Provide both synchronous (`ArgalaClient`) and asynchronous (`AsyncArgalaClient`) clients in the core SDK, with standard library `urllib` or lightweight `http.client` fallbacks and optional `httpx` async support.
- **Alternatives considered**:
  1. Async-only with `httpx` / `aiohttp`: Rejected because synchronous CLI scripts, standard DevOps automation (e.g. Fabric, Ansible, simple Python scripts), and simple functions gated by `@requires_approval` would be forced to use `asyncio.run()`, introducing unnecessary boilerplate.
  2. Sync-only: Rejected because modern agentic frameworks (LangChain, AutoGen, FastAPI, Antigravity) are heavily asynchronous.
- **Why this won**: Enables seamless developer experience across both simple linear scripts and high-concurrency async agent loops.

---

## Decision 003: Sovereign AI Local Proxy Protocol Translation
- **Date**: 2026-09-17 (Phase 1: Proxy Design)
- **What was decided**: Build a local HTTP proxy server implementing the standard OpenAI `/v1/chat/completions` and Google `/v1beta/models/...` interface, routing all payloads through the phone's `POST /v1/vault/broker` endpoint.
- **Alternatives considered**:
  1. Requiring users to write custom SDK code for all LLM calls: Rejected because users want their existing tools (Cursor, VS Code extensions, Continue.dev, Claude Code) to work without modifying their source code.
  2. Storing encrypted keys in laptop memory: Rejected because the core sovereign security guarantee is that the laptop NEVER possesses the raw API key.
- **Why this won**: Any off-the-shelf developer tool can set `OPENAI_BASE_URL="http://127.0.0.1:8080/v1"`, immediately gaining physical zero-trust security without changing any code or exposing keys.

---

## Decision 004: Direct Hardware Actuation Endpoint (`POST /v1/hardware/actuate`)
- **Date**: 2026-09-17 (Phase 1: Gateway Design)
- **What was decided**: Add a direct `/v1/hardware/actuate` REST route to the gateway, protected by a dedicated `hardware:actuate` capability scope.
- **Alternatives considered**:
  1. Only allowing actuation as a side effect of approval tickets: Rejected because developers need to signal arbitrary events (e.g. CI build passed/failed, server health alerts, long-running agent notifications) without creating interactive approval state machines.
  2. Triggering actuation via Termux SSH: Rejected because SSH exposes the entire phone shell and bypasses zero-trust capability scoping, logging, and lockdown interlocks.
- **Why this won**: Clean REST semantics with fine-grained security scopes, integrated with the Emergency Lockdown safety interlock.

---

## Decision 005: Four-Document Living Architecture
- **Date**: 2026-09-17 (Phase 1: Documentation Workflow)
- **What was decided**: Strictly adhere to the four living documents in `docs/` (`plan.md`, `design.md`, `decisions.md`, `flow.md`) before writing and while updating implementation code.
- **Alternatives considered**:
  1. Writing code first and generating documentation after: Rejected because it leads to design drift and misses the educational and decision-tracking value of the project.
- **Why this won**: Ensures that every architectural choice is deliberate, documented, and reproducible by future contributors.

---

## Decision 006: Pre-Packaged Google GenAI Toolset (`create_argala_gemini_tools`)
- **Date**: 2026-09-17 (Phase 6: Integrations)
- **What was decided**: Provide native Python callables with type annotations and Google-style docstrings in `eco_system/argala/integrations/genai.py` that plug directly into `google-genai` client `tools=[...]` parameter.
- **Alternatives considered**:
  1. Requiring users to write custom function declaration dictionaries with nested JSON schemas: Rejected due to verbosity and high error rates.
  2. Wrapping the whole model in a custom class: Rejected because developers want to use the official `google-genai` SDK client directly without learning a proprietary wrapper.
- **Why this won**: The official `google-genai` SDK automatically reflects parameter types and docstrings from Python functions, providing instant auto-function-calling with zero boilerplate.

---

## Decision 007: Standard Library HTTP Server for Sovereign AI Proxy
- **Date**: 2026-09-17 (Phase 4: Proxy Implementation)
- **What was decided**: Implement `SovereignProxyHandler` using Python's standard library `http.server.ThreadingHTTPServer` rather than requiring `uvicorn`/`fastapi` as mandatory dependencies.
- **Alternatives considered**:
  1. Forcing `fastapi` and `uvicorn`: Rejected because developers on minimal environments or CI containers should be able to run `argala proxy` without heavy pip installs.
- **Why this won**: Guarantees zero external dependency installation for basic proxy functionality while maintaining multithreaded request handling.

---

## Decision 008: Outbound SSRF Protection in Sovereign Vault Broker
- **Date**: 2026-09-18 (System Audit & Hardening)
- **What was decided**: Enforce strict destination IP validation in `app/vault/manager.py:broker_http_request`. All target URLs must resolve to valid public IPv4/IPv6 addresses. Access to loopback (`127.0.0.0/8`), private networks (RFC 1918), link-local (`169.254.0.0/16`), multicast, and cloud metadata addresses is forbidden.
- **Alternatives considered**:
  1. Relying on network-level firewall (iptables) in Termux: Rejected because Termux lacks root privileges by default on non-rooted devices; software-layer boundary enforcement guarantees protection in all environments.
  2. Domain allow-listing: Considered too rigid for developers brokering arbitrary external REST APIs.
- **Why this won**: Prevents malicious agents or prompt-injected LLMs from using the phone's sovereign vault as an internal network pivot to reach gateway internal endpoints or Termux localhost services.

---

## Decision 009: Pydantic v1/v2 Polyfill Strategy for Heterogeneous Environments
- **Date**: 2026-09-18 (System Audit & Hardening)
- **What was decided**: Implement dual-version import fallbacks (`from pydantic.v1 import BaseSettings` fallback to `from pydantic import BaseSettings`) in `app/config.py` and ensure all SDK models work across Pydantic v1 (used in Termux Python) and Pydantic v2 (used in modern laptop environments).
- **Alternatives considered**:
  1. Forcing Pydantic v2 upgrade on Termux: Rejected because compiling/installing Rust-based `pydantic-core` wheels on ARM32/ARM64 Android Termux frequently fails or introduces unstable toolchain requirements.
  2. Pinning laptop environments to Pydantic v1: Rejected because modern AI agent libraries (Google GenAI, LangChain) require Pydantic v2.
- **Why this won**: Allows the edge gateway on Android to remain on lightweight pre-compiled Pydantic v1 while laptop clients run modern Pydantic v2 without schema incompatibilities.

---

## Decision 010: Replay Cache Nonce Pruning (Bounded SQLite Footprint)
- **Date**: 2026-09-18 (System Audit & Hardening)
- **What was decided**: Periodically prune expired nonces during `verify_action` execution in `app/vault/manager.py`, deleting nonces where `expires_at < now`.
- **Alternatives considered**:
  1. Dedicated background cron task: Adds unnecessary timer complexity and battery drain on Android.
  2. In-memory set: Rejected because edge node restarts or memory pressure kills would wipe the replay cache, opening replay vulnerability windows.
- **Why this won**: Opportunistic pruning keeps SQLite storage bounded on memory-constrained mobile hardware with zero additional process overhead.

---

## Decision 011: Strict CORS Origin Policy & Credential Guard
- **Date**: 2026-09-18 (System Audit & Hardening)
- **What was decided**: Replace CORS wildcard `["*"]` in default gateway configuration with explicit local origins (`127.0.0.1`, `localhost`, local mesh IPs). In addition, configure FastAPI's `CORSMiddleware` in `app/main.py` so that `allow_credentials` is disabled whenever a wildcard origin is present.
- **Alternatives considered**:
  1. Allowing wildcard origins everywhere for convenience: Rejected because it violates browser security standards and exposes authenticated endpoints to CSRF/XSS from untrusted web pages.
- **Why this won**: Prevents browser-based exploitation of the edge node while allowing local development and mesh clients to communicate smoothly.


