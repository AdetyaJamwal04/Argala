"""
Test MCP Client over SSE and HTTP.
Connects to the Argala MCP server, handles the handshake, lists tools, and invokes tools.
Uses pure Python standard library (no pip dependencies required on Windows).
"""

import json
import sys
import threading
import time
import urllib.request

SERVER_HOST = "100.68.31.91:8000"
SSE_URL = f"http://{SERVER_HOST}/v1/mcp/sse"
MESSAGE_BASE_URL = f"http://{SERVER_HOST}"

session_id = None
endpoint_path = None
running = True


def post_json_rpc(endpoint: str, payload: dict) -> dict:
    url = f"{MESSAGE_BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sse_listener():
    global session_id, endpoint_path, running
    print(f"[*] Connecting to MCP SSE stream at {SSE_URL}...")
    req = urllib.request.Request(SSE_URL, headers={"Accept": "text/event-stream"})
    
    with urllib.request.urlopen(req, timeout=60) as stream:
        while running:
            line = stream.readline().decode("utf-8")
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                if event_type == "endpoint":
                    endpoint_path = data_str
                    # Extract sessionId from endpoint URL
                    if "sessionId=" in endpoint_path:
                        session_id = endpoint_path.split("sessionId=")[1]
                    print(f"[+] Connected! Session ID: {session_id}")
                    print(f"[+] Message endpoint: {endpoint_path}")
                elif event_type == "message":
                    data = json.loads(data_str)
                    print(f"\n[<-- RECV JSON-RPC Frame]:\n{json.dumps(data, indent=2)}")


def main():
    global running
    listener_thread = threading.Thread(target=sse_listener, daemon=True)
    listener_thread.start()

    # Wait for session initialization
    for _ in range(50):
        if session_id and endpoint_path:
            break
        time.sleep(0.1)

    if not session_id:
        print("[-] Failed to establish MCP SSE session")
        sys.exit(1)

    time.sleep(0.5)

    # 1. Send MCP Initialize Handshake
    print("\n[1] Sending 'initialize' handshake...")
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "WindowsTestAgent", "version": "1.0"},
        },
    }
    post_json_rpc(endpoint_path, init_payload)
    time.sleep(0.5)

    # 2. Query available tools
    print("\n[2] Requesting 'tools/list'...")
    tools_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    post_json_rpc(endpoint_path, tools_payload)
    time.sleep(0.5)

    # 3. Call tool: android_get_telemetry
    print("\n[3] Executing 'tools/call' -> android_get_telemetry...")
    call_telemetry_payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "android_get_telemetry",
            "arguments": {},
        },
    }
    post_json_rpc(endpoint_path, call_telemetry_payload)
    time.sleep(0.5)

    # 4. Call tool: android_ping with echo
    print("\n[4] Executing 'tools/call' -> android_ping...")
    call_ping_payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "android_ping",
            "arguments": {"echo": "Hello from Windows Laptop Agent across WireGuard!"},
        },
    }
    post_json_rpc(endpoint_path, call_ping_payload)
    time.sleep(1.0)

    print("\n[+] MCP Test Protocol complete!")
    running = False


if __name__ == "__main__":
    main()
