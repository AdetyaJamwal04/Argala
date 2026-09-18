"""
Sovereign AI Local Proxy Server.
Runs locally on the developer workstation (e.g. http://127.0.0.1:8080).
Provides standard OpenAI and Gemini compatible endpoints, routing all inference
requests through the phone's Sovereign Vault. The laptop never holds or sees raw API keys.
"""

import json
import logging
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from argala.client import ArgalaClient, ArgalaError

logger = logging.getLogger("argala.proxy")


class SovereignProxyHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler translating standard LLM calls into secretless
    Argala phone vault broker requests.
    """

    client: ArgalaClient = None
    default_model: str = "gemini-3.8-flash"

    def do_GET(self):
        """Health check and routing info."""
        if self.path in ("/", "/health"):
            self._send_json(200, {
                "status": "online",
                "service": "Argala Sovereign AI Proxy",
                "edge_node": self.client.endpoint,
                "default_model": self.default_model,
                "supported_routes": [
                    "/v1/chat/completions (OpenAI Compatible)",
                    "/v1beta/models/{model}:generateContent (Gemini Native)",
                ],
            })
        else:
            self._send_json(404, {"error": f"Route '{self.path}' not found."})

    def do_POST(self):
        """Dispatches LLM generation through the sovereign vault broker."""
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        
        try:
            req_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON body: {str(e)}"})
            return

        # Check for cyber-physical gating header
        require_physical_approval = self.headers.get("X-Argala-Require-Approval", "false").lower() == "true"
        if require_physical_approval:
            prompt_preview = str(req_data)[:120]
            ticket = self.client.request_approval(
                action="llm.inference_proxy",
                target=self.path,
                risk_level="high",
                prompt=f"Proxy inference requested: {prompt_preview}...",
                timeout_seconds=60,
            )
            try:
                self.client.wait_for_approval(ticket.id, timeout=65.0)
            except Exception as e:
                self._send_json(403, {"error": f"Physical approval gate rejected or timed out: {str(e)}"})
                return

        # 1. Native Gemini Path: /v1beta/models/{model}:generateContent
        if "/models/" in self.path and ":generateContent" in self.path:
            self._handle_gemini_native(self.path, req_data)

        # 2. OpenAI Compatible Path: /v1/chat/completions
        elif self.path.endswith("/chat/completions"):
            self._handle_openai_compat(req_data)

        else:
            self._send_json(404, {
                "error": f"Unsupported proxy path '{self.path}'. Use /v1/chat/completions or /v1beta/models/..."
            })

    def _handle_gemini_native(self, path: str, req_data: Dict[str, Any]):
        """Proxies native Gemini payload directly through the phone vault broker."""
        target_url = f"https://generativelanguage.googleapis.com{path}"
        try:
            broker_resp = self.client.broker_request(
                url=target_url,
                method="POST",
                secret_id="gemini_api_key",
                header_name="x-goog-api-key",
                header_prefix="",
                body=req_data,
                timeout=60.0,
            )
            self._send_json(broker_resp.status_code, broker_resp.body)
        except ArgalaError as e:
            self._send_json(503, {"error": f"Argala Vault Broker failure: {str(e)}"})
        except Exception as e:
            self._send_json(500, {"error": f"Internal proxy error: {str(e)}"})

    def _handle_openai_compat(self, req_data: Dict[str, Any]):
        """
        Translates OpenAI chat completion format to Gemini format,
        brokers through the phone, and translates the response back to OpenAI format.
        """
        model = req_data.get("model", self.default_model)
        # Normalize model name for Gemini
        if "gemini" not in model:
            gemini_model = self.default_model
        else:
            gemini_model = model

        messages = req_data.get("messages", [])
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "model" if role == "assistant" else "user"
                gemini_contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })

        gemini_payload: Dict[str, Any] = {"contents": gemini_contents}
        if system_instruction:
            gemini_payload["systemInstruction"] = system_instruction

        # Map temperature
        gen_config = {}
        if "temperature" in req_data:
            gen_config["temperature"] = req_data["temperature"]
        if "max_tokens" in req_data:
            gen_config["maxOutputTokens"] = req_data["max_tokens"]
        if gen_config:
            gemini_payload["generationConfig"] = gen_config

        target_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"

        try:
            broker_resp = self.client.broker_request(
                url=target_url,
                method="POST",
                secret_id="gemini_api_key",
                header_name="x-goog-api-key",
                header_prefix="",
                body=gemini_payload,
                timeout=60.0,
            )

            if broker_resp.status_code != 200:
                self._send_json(broker_resp.status_code, broker_resp.body)
                return

            gemini_resp = broker_resp.body
            # Extract generated text
            generated_text = ""
            candidates = gemini_resp.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    generated_text = parts[0].get("text", "")

            # Construct OpenAI response object
            openai_resp = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": generated_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "_argala_gateway": {
                    "brokered_by": "Samsung Galaxy A6+ Sovereign Vault",
                    "upstream_service": "gemini",
                    "keyless": True,
                },
            }
            self._send_json(200, openai_resp)

        except ArgalaError as e:
            self._send_json(503, {"error": f"Argala Vault Broker failure: {str(e)}"})
        except Exception as e:
            self._send_json(500, {"error": f"Internal proxy error: {str(e)}"})

    def _send_json(self, status_code: int, data: Any):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any):
        # Clean logging
        logger.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)


def run_proxy(
    host: str = "127.0.0.1",
    port: int = 8080,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    default_model: str = "gemini-3.8-flash",
):
    """Launches the Sovereign AI Local Proxy."""
    client = ArgalaClient(endpoint=endpoint, api_key=api_key)
    
    # Test connection
    try:
        ping_res = client.ping()
        print(f"[OK] Connected to Argala Node: {ping_res.get('gateway_name')} (Latency: {ping_res.get('_client_latency_ms')}ms)")
    except Exception as e:
        print(f"[Warning] Could not ping Argala node: {e}")

    SovereignProxyHandler.client = client
    SovereignProxyHandler.default_model = default_model

    server = ThreadingHTTPServer((host, port), SovereignProxyHandler)
    print("=" * 70)
    print(f"      ARGALA SOVEREIGN AI LOCAL PROXY RUNNING ON http://{host}:{port}")
    print(f"      Zero Secrets on Laptop -> Inferences Brokered via Phone Vault")
    print("=" * 70)
    print(f"  • OpenAI Base URL:    http://{host}:{port}/v1")
    print(f"  • Gemini Endpoint:    http://{host}:{port}/v1beta/models/{default_model}:generateContent")
    print(f"  • Edge Vault Target:  {client.endpoint}")
    print("\nConfigure Cursor / LangChain / CLI:")
    print(f"  export OPENAI_BASE_URL=\"http://{host}:{port}/v1\"")
    print("  export OPENAI_API_KEY=\"argala-sovereign-zero-secret\"")
    print("-" * 70)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Sovereign Proxy...")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_proxy()
