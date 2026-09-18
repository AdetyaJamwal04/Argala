"""
Example 2: Sovereign Zero-Secret LLM Client.
Demonstrates querying the local Sovereign AI Proxy (http://127.0.0.1:8080)
using standard OpenAI format without having any API keys on this machine.
"""

import json
import sys
import urllib.request

PROXY_URL = "http://127.0.0.1:8080/v1/chat/completions"


def query_sovereign_proxy(prompt: str):
    print("=" * 70)
    print("      ARGALA SOVEREIGN ZERO-SECRET INFERENCE")
    print("=" * 70)
    print(f"Target Proxy: {PROXY_URL}")
    print("Secrets on this laptop: NONE (0)")
    print("-" * 70)

    payload = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are a concise, highly technical sovereign assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    req = urllib.request.Request(
        PROXY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print(f"\n[Prompt]: \"{prompt}\"")
    print("[Dispatching] Querying local proxy -> brokered through Samsung Galaxy A6+ vault...")

    try:
        with urllib.request.urlopen(req, timeout=50.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choice = data["choices"][0]
            reply = choice["message"]["content"]
            gateway_info = data.get("_argala_gateway", {})

            print("\n[Response Received]:")
            print(f"  {reply.strip()}")
            print("\n[Provenance Proof]:")
            print(f"  • Brokered by:      {gateway_info.get('brokered_by')}")
            print(f"  • Upstream Service: {gateway_info.get('upstream_service')}")
            print(f"  • Keyless Laptop:   {gateway_info.get('keyless')}")
    except urllib.error.URLError as e:
        print(f"\n[Error] Could not reach Sovereign Proxy at {PROXY_URL}: {e}")
        print("Tip: Run the proxy first in another terminal: `python -m argala.cli proxy` or `argala proxy`.")
        sys.exit(1)


if __name__ == "__main__":
    prompt_text = "In two sentences, explain why holding API keys in an edge hardware vault is safer than laptop .env files."
    query_sovereign_proxy(prompt_text)
