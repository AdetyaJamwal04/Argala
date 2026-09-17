# Argala & Google GenAI — Practical Demonstration

This demo environment showcases the sovereign interaction between a developer workstation AI Agent (powered by `google-genai` on Python 3.12) and the **Argala Sovereign Control Plane** running 24/7 on a Samsung Galaxy A6+ edge node over Tailscale WireGuard (`http://100.68.31.91:8000`).

---

## Prerequisites
* Active virtual environment:
  ```powershell
  # Windows PowerShell
  cd c:\Projects\android_dev_env\demo_run
  .\.venv\Scripts\activate.ps1
  ```

---

## Quickstart: Run the Demo Suite

### 1. Interactive Menu Mode
Run the demonstration CLI:
```powershell
python run_demo.py
```
You can select any scenario interactively:
1. **Wire-Level Ping & Hardware Telemetry** (Reads live battery, RAM, thermal, and uptime from the phone)
2. **Durable Queue & Idempotent Deduplication** (Demonstrates HTTP 202 vs 200 effectively-once execution)
3. **Cyber-Physical HITL Gate** (Vibrates the phone, speaks via TTS, posts Android notification, and waits for human approval at `http://100.68.31.91:8000/approvals`)
4. **Cryptographic Vault & TOCTOU Defense** (Proves mathematical rejection of parameter tampering)
5. **Gemini AI Agent with Sovereign Tools** (Reasoning loop)
6. **Complete End-to-End Suite**

### 2. Direct Scenario Execution
```powershell
# Scenario 1: Telemetry & Ping
python run_demo.py --telemetry

# Scenario 2: Durable Queue
python run_demo.py --queue

# Scenario 3 & 4: HITL Gate & Vault Defense
python run_demo.py --hitl

# Scenario 5: Gemini Agent
python run_demo.py --agent

# Run All Scenarios
python run_demo.py --all
```

---

## Live Practical Requiring Gemini API Key

We have created a dedicated script: **`demo_gemini_execution.py`** that demonstrates real-world Gemini execution:

```powershell
python demo_gemini_execution.py
```

### What It Executes:
1. **Sovereign Secretless Gemini Inference**:
   * Encrypts and provisions your `GEMINI_API_KEY` directly into Argala's SQLite vault on the phone (`POST /v1/vault/secrets`).
   * The laptop issues a prompt to Argala's Secretless Broker (`POST /v1/vault/broker`).
   * The phone decrypts the key in RAM on-device, contacts Google's Gemini Cloud API, and returns the response.
   * **Result:** The laptop executes Gemini AI models without ever storing or exposing the API key locally.
2. **Live Autonomous Gemini 2.0 Agent with Physical Deadbolt**:
   * Initializes Google's official `google-genai` SDK with `gemini-2.0-flash`.
   * Gemini reasons over a goal, inspects phone battery and thermals via live tools.
   * Detecting a critical maintenance action, Gemini dispatches a physical approval ticket.
   * **The Samsung Galaxy A6+ vibrates and speaks the prompt aloud via Android TTS.**
   * Once you tap `APPROVE` on `http://100.68.31.91:8000/approvals`, Gemini validates the cryptographic token and commits the task to the durable queue!

