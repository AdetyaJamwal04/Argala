"""
Example 3: Autonomous Gemini Agent with Physical Hardware Feedback.
Uses the official `google-genai` SDK and Argala's pre-built toolset (`create_argala_gemini_tools`).
The agent can inspect battery/thermals, vibrate/speak on the phone, and gate actions behind approval.
"""

import os
import sys

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[Error] 'google-genai' package is required for this example.")
    print("Install it with: pip install google-genai")
    sys.exit(1)

from argala import ArgalaClient
from argala.integrations.genai import create_argala_gemini_tools


def run_autonomous_agent(user_prompt: str, api_key: str):
    print("=" * 70)
    print("      ARGALA AUTONOMOUS GEMINI AGENT WITH PHYSICAL FEEDBACK")
    print("=" * 70)

    # Initialize Argala client and tools
    client = ArgalaClient()
    tools = create_argala_gemini_tools(client)

    # Initialize Gemini client
    ai_client = genai.Client(api_key=api_key)
    model_name = "gemini-3.8-flash"

    system_instruction = (
        "You are an autonomous AI operations agent running with direct access to a physical "
        "Android smartphone appliance via Argala tools. "
        "Always check telemetry before taking high-risk actions. "
        "Always provide tactile or voice feedback when beginning or finishing critical tasks. "
        "Whenever asked to execute a destructive or high-risk task (such as dropping databases, "
        "terminating servers, or deploying to production), you MUST call request_human_approval "
        "and wait for the physical operator's authorization."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        temperature=0.2,
    )

    print(f"[Agent Initialized] Model: {model_name} | Edge Node: {client.endpoint}")
    print(f"[User Instruction]: {user_prompt}\n")

    chat = ai_client.chats.create(
        model=model_name,
        config=config,
    )

    print("[Reasoning & Tool Execution Loop Active]...")
    response = chat.send_message(user_prompt)

    print("\n" + "=" * 70)
    print("FINAL AGENT REPORT:")
    print("=" * 70)
    print(response.text)


if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[Notice] GEMINI_API_KEY not found in environment.")
        key = input("Enter your Gemini API Key to run live agent: ").strip()

    prompt = (
        "Inspect the physical phone's battery level and temperature. "
        "If everything looks healthy, vibrate the phone for 400 milliseconds, "
        "speak aloud 'System diagnostic complete and healthy', and submit a background snapshot job."
    )
    run_autonomous_agent(prompt, key)
