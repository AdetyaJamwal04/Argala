# Argala Sovereign Ecosystem 🛡️⚡

The complete developer and agent ecosystem for **Argala** — turning physical Android smartphones into sovereign hardware security appliances, zero-secret API brokers, and cyber-physical Human-in-the-Loop (HITL) gates.

---

## 📦 What's Inside

1. **`argala` Python SDK**: High-level, fully typed client library for all Argala Gateway features (telemetry, physical haptics, voice announcements, durable queues, and encrypted vaults).
2. **`@requires_approval` Decorator**: One-line Python decorator that blocks sensitive code execution until approved via physical phone vibration, voice prompt, and screen tap.
3. **Sovereign AI Local Proxy (`argala proxy`)**: Local HTTP proxy (`http://127.0.0.1:8080`) compatible with OpenAI and Google Gemini APIs. Local developer tools (Cursor, LangChain, CLI tools) run with **zero API keys on the laptop** — requests are brokered securely through the phone's encrypted vault.
4. **Argala CLI (`argala`)**: Unified terminal CLI for node health monitoring, physical actuation, ticket management, local proxy hosting, and emergency killswitch activation.
5. **Agent Integrations (`argala.integrations.genai`)**: Pre-built tools for Google's `google-genai` SDK and Anthropic Model Context Protocol (MCP).

---

## 🚀 Quickstart

### 1. Installation

Install the package in editable development mode from this directory:

```bash
cd eco_system
pip install -e .
```

To install with optional dependencies:
```bash
# With async support (httpx)
pip install -e .[async]

# With Google GenAI SDK
pip install -e .[genai]

# Complete suite
pip install -e .[full]
```

### 2. Environment Configuration

By default, the SDK and CLI look for the Argala node on your WireGuard / Tailscale mesh:

```bash
# Linux / macOS
export ARGALA_ENDPOINT="http://100.68.31.91:8000"
export ARGALA_API_KEY="argala-laptop-agent-key"

# Windows PowerShell
$env:ARGALA_ENDPOINT="http://100.68.31.91:8000"
$env:ARGALA_API_KEY="argala-laptop-agent-key"
```

---

## 💻 CLI Commands

The `argala` CLI gives you full control over the edge node directly from your terminal:

```bash
# Check live hardware telemetry (battery, RAM, thermals)
argala status

# Trigger physical phone alerts directly
argala actuate --speak "Deployment finished successfully" --vibrate 500

# Post an Android notification shade alert
argala actuate --notify-title "CI/CD Alert" --notify-content "Build passed on main branch"

# List pending and historical approval tickets
argala approvals list

# Approve or reject tickets from the terminal
argala approvals approve <ticket_id>
argala approvals reject <ticket_id>

# Launch the Sovereign AI Local Proxy
argala proxy --port 8080

# Emergency Kill Switch (Revoke all agent capabilities)
argala lock --reason "Suspicious activity detected"
argala unlock
```

---

## 🔒 The Sovereign AI Local Proxy (Zero Secrets on Laptop)

Run the local proxy to allow Cursor, Continue.dev, LangChain, or scripts to use LLMs without exposing API keys on your computer:

```bash
argala proxy --port 8080
```

Configure your tool:
```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_API_KEY="argala-sovereign-zero-secret"
```

Now, any prompt you submit is transparently signed and routed to your Android phone over the encrypted mesh. The phone injects the decrypted API key from its hardware vault and returns the completion. **Your laptop never stores or touches the raw key.**

---

## 🛠️ Python SDK Usage

### 1. Cyber-Physical Approval Decorator
```python
from argala import requires_approval

@requires_approval(action="database.drop_schema", risk_level="critical")
def drop_database(cluster_id: str):
    # This code WILL NEVER run unless approved on the physical phone screen!
    print(f"Dropping {cluster_id}...")
```

### 2. Direct Hardware Actuation
```python
from argala import ArgalaClient

client = ArgalaClient()

# Vibrate phone for half a second
client.vibrate(500)

# Speak aloud using Android Text-to-Speech
client.speak("Warning: High memory utilization on server node.")

# Post interactive notification
client.notify("Security Alert", "New SSH login detected from workstation.")
```

### 3. Secretless Vault Broker
```python
from argala import ArgalaClient

client = ArgalaClient()

# Request Gemini completion through the phone without having the key!
resp = client.broker_request(
    service="gemini",
    path="/v1beta/models/gemini-3.8-flash:generateContent",
    body={
        "contents": [{"parts": [{"text": "Hello, world!"}]}]
    }
)
print(resp.response_body)
```

---

## 📚 Living Documentation

In accordance with our Documentation-First workflow, full technical specifications and decision records are maintained in:
- [`docs/plan.md`](docs/plan.md) — Feature scope, non-goals, and step-by-step roadmap.
- [`docs/design.md`](docs/design.md) — System boundaries, components, and security contracts.
- [`docs/decisions.md`](docs/decisions.md) — Chronological architecture decision log (ADR).
- [`docs/flow.md`](docs/flow.md) — Runtime data flow diagrams and edge-case handling.
