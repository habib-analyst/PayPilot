"""
Pluggable chat-LLM layer over any OpenAI-compatible /chat/completions API.

Defaults to Google AI Studio's OpenAI-compatible endpoint (free tier key
from https://aistudio.google.com works). Point LLM_BASE_URL at any other
OpenAI-compatible provider (OpenAI, OpenRouter, local vLLM, ...) to swap.

Env:
    LLM_BASE_URL   default https://generativelanguage.googleapis.com/v1beta/openai/
    LLM_API_KEY    (required)
    LLM_MODEL      default gemini-2.5-flash
"""

from __future__ import annotations

import json
import os

import httpx

SYSTEM_PROMPT = """You are PayPilot, an agentic commerce copilot. You help the user shop \
and pay securely with PayPal.

Rules:
- You can search a product catalog, show options, and check out with PayPal sandbox.
- NEVER invent products, prices, order IDs, or payment statuses. Use tools for every fact.
- When the user wants to buy something: confirm the exact product and total with them \
BEFORE creating the PayPal order. After creating the order, give them the approval URL \
and explain they must approve it in the PayPal sandbox. Only capture AFTER the buyer \
approved (ask them to confirm they approved).
- Keep answers short and conversational. Prices in USD.
- If the user asks something unrelated to shopping/payments, answer briefly and steer \
back to how you can help them shop.
"""


class LLM:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("LLM_BASE_URL",
                         "https://generativelanguage.googleapis.com/v1beta/openai/")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Get a free key at https://aistudio.google.com "
                "and put it in your .env (see .env.example)."
            )
        self.model = model or os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self._http = httpx.Client(timeout=60.0)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        resp = self._http.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM call failed ({resp.status_code}): {resp.text[:400]}")
        return resp.json()["choices"][0]["message"]


def fmt_tool_result(name: str, result: object) -> str:
    return f"[{name} result]\n{json.dumps(result, indent=2, default=str)}"
