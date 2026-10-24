"""
Pluggable chat-LLM layer over any OpenAI-compatible /chat/completions API.

Defaults to Google AI Studio's OpenAI-compatible endpoint (free tier key
from https://aistudio.google.com works). Point LLM_BASE_URL at any other
OpenAI-compatible provider (OpenAI, OpenRouter, local vLLM, ...) to swap.

Env:
    LLM_BASE_URL   default https://generativelanguage.googleapis.com/v1beta/openai/
    LLM_API_KEY    (required)
    LLM_MODEL      default gemini-3-flash-preview
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
        self.model = model or os.getenv("LLM_MODEL", "gemini-3-flash-preview")
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


# ---------------------------------------------------------------------------
# ScriptedLLM — deterministic fallback dialogue (no LLM key needed).
#
# Used ONLY when no LLM_API_KEY is set, or when PAYPILOT_SCRIPTED_LLM=1.
# When a real key is present the real LLM above stays the default path.
# It maps the demo script's utterances to the correct tool-call sequence
# and answers from the tool results themselves, so the full
# search -> compare -> confirm -> checkout -> approve -> capture ->
# receipt flow runs end-to-end with zero external calls. It never invents
# products, prices, order ids, or payment statuses: every fact it states
# comes from a tool result already in the conversation history.
# ---------------------------------------------------------------------------

import re

_PRODUCT_KEYWORDS = {
    "aurora": "p001",
    "pulsebuds": "p002",
    "pulse": "p002",
    "voltcore": "p003",
    "lumendesk": "p004",
    "typeflow": "p005",
    "strideband": "p006",
    "orbitcam": "p007",
    "nimbus": "p008",
    "echostand": "p009",
    "terragrow": "p010",
    "sonicbar": "p011",
    "aeropack": "p012",
}


class ScriptedLLM:
    def __init__(self) -> None:
        self._n = 0

    # ---------- helpers ----------

    def _tool(self, name: str, args: dict) -> dict:
        self._n += 1
        return {
            "id": f"scripted-{self._n}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }

    def _reply(self, content: str) -> dict:
        return {"content": content, "tool_calls": []}

    def _call(self, name: str, args: dict) -> dict:
        return {"content": None, "tool_calls": [self._tool(name, args)]}

    @staticmethod
    def _tool_results(messages: list[dict]) -> list[tuple[str, object]]:
        """(tool_name, parsed_json) for every tool message, in order."""
        results: list[tuple[str, object]] = []
        for m in messages:
            if m.get("role") != "tool":
                continue
            content = m.get("content") or ""
            name = ""
            if content.startswith("[") and " result]" in content:
                name = content[1 : content.index(" result]")]
            data: object = {}
            if "\n" in content:
                try:
                    data = json.loads(content.split("\n", 1)[1])
                except json.JSONDecodeError:
                    data = {}
            results.append((name, data))
        return results

    @staticmethod
    def _last_user(messages: list[dict]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return m.get("content") or ""
        return ""

    def _latest_order_id(self, results: list[tuple[str, object]]) -> str:
        for name, data in reversed(results):
            if name == "create_checkout" and isinstance(data, dict):
                return str(data.get("order_id") or "")
        return ""

    # ---------- pending tool-result handling ----------

    def _handle_pending(self, name: str, data: object) -> dict | None:
        if name == "search_products" and isinstance(data, list):
            if not data:
                return self._reply(
                    "I couldn't find anything matching that. Want to try different keywords?"
                )
            lines = [
                f"- {p.get('name')} — ${p.get('price')} ({p.get('rating')}★, "
                f"{p.get('reviews')} reviews)"
                for p in data[:3]
            ]
            top = data[0]
            return self._reply(
                "Here's what I found:\n" + "\n".join(lines)
                + f"\n\nMy recommendation is the {top.get('name')} at "
                f"${top.get('price')} — best rated of the bunch. "
                "Want me to buy it for you?"
            )
        if name == "get_product" and isinstance(data, dict) and data.get("name"):
            return self._reply(
                f"{data.get('name')} — ${data.get('price')} "
                f"({data.get('rating')}★). {data.get('description') or ''} "
                "Want me to buy it for you?"
            )
        if name == "create_checkout" and isinstance(data, dict) and data.get("order_id"):
            return self._reply(
                "Order created (mocked checkout — PayPal sandbox is unavailable "
                "in Pakistan, so this is a simulated order, not a live PayPal "
                f"transaction):\nTotal: ${data.get('total')} "
                f"{data.get('currency')}\nApprove it here: {data.get('approve_url')}\n"
                "Click the link, approve on the mock page, then tell me "
                "'I approved it' and I'll capture it."
            )
        if name == "check_order" and isinstance(data, dict):
            status = data.get("status")
            if status == "APPROVED":
                return self._call("capture_payment", {"order_id": data.get("order_id")})
            if status == "COMPLETED":
                return self._reply("That order is already completed.")
            return self._reply(
                f"That order is still {status} — it needs your approval first. "
                "Click the approval link, approve it, then tell me 'I approved it'."
            )
        if name == "capture_payment" and isinstance(data, dict):
            receipt = data.get("receipt") or {}
            captures = receipt.get("captures") or []
            cap = captures[0] if captures else {}
            return self._reply(
                "Payment captured — receipt (mocked checkout, no live PayPal "
                "transaction):\n"
                f"Order: {receipt.get('order_id')}\n"
                f"Capture ID: {cap.get('capture_id')}\n"
                f"Amount: {cap.get('amount')} {cap.get('currency')}\n"
                f"Payer: {receipt.get('payer_email')}\n"
                "Status: COMPLETED — you can see it in the order history table."
            )
        if isinstance(data, dict) and data.get("error"):
            return self._reply(f"That didn't work: {data.get('error')}")
        return None

    # ---------- main entry ----------

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        results = self._tool_results(messages)
        user_text = self._last_user(messages)
        low = user_text.lower()

        # The agent injects a "Summarize..." user message when a turn ends on
        # tool calls; answer it from the latest receipt/order.
        if low.startswith("summarize"):
            for name, data in reversed(results):
                if name == "capture_payment" and isinstance(data, dict):
                    return self._handle_pending(name, data) or self._reply(
                        "Done — payment captured."
                    )
            order_id = self._latest_order_id(results)
            return self._reply(
                f"Done — order {order_id} is in progress." if order_id
                else "Done — let me know what you'd like to shop for next."
            )

        # If the newest message is a tool result (no user message after it),
        # react to that result before looking at older user text.
        last_tool_idx = max(
            (i for i, m in enumerate(messages) if m.get("role") == "tool"),
            default=-1,
        )
        last_user_idx = max(
            (i for i, m in enumerate(messages) if m.get("role") == "user"),
            default=-1,
        )
        if last_tool_idx > last_user_idx and results:
            handled = self._handle_pending(*results[-1])
            if handled is not None:
                return handled

        # --- fresh user utterance -> tool call ---
        if "approv" in low or "captur" in low:
            order_id = self._latest_order_id(results)
            if order_id:
                return self._call("check_order", {"order_id": order_id})
            return self._reply("Which order do you mean? I don't have one in progress.")

        if "buy" in low or low.strip() in ("yes", "yes please", "yeah", "sure"):
            product_id = None
            for keyword, pid in _PRODUCT_KEYWORDS.items():
                if keyword in low:
                    product_id = pid
                    break
            if product_id is None:
                for name, data in reversed(results):
                    if name == "search_products" and isinstance(data, list) and data:
                        product_id = str(data[0].get("id"))
                        break
            if product_id:
                return self._call(
                    "create_checkout", {"product_id": product_id, "quantity": 1}
                )
            return self._reply("Which product should I buy? Name it and I'll check you out.")

        if re.search(
            r"\b(find|show|search|looking|need|want|gift|headphones|earbuds|"
            r"charger|monitor|keyboard|tracker|camera|backpack|soundbar|"
            r"stand|garden|laptop)\b",
            low,
        ):
            query = low
            max_price = None
            m = re.search(r"under\s*\$?(\d+(?:\.\d+)?)", low)
            if m:
                max_price = float(m.group(1))
            if "headphone" in low:
                query = "noise cancelling headphones"
            elif "gift" in low or "smart home" in low:
                query = "smart home"
            elif "laptop" in low or "remote" in low:
                query = "laptop accessories"
            else:
                query = re.sub(
                    r"^(find me|show me|search for|i need|i want)\s+", "", low
                ).strip() or low
            args: dict = {"query": query}
            if max_price is not None:
                args["max_price"] = max_price
            return self._call("search_products", args)

        return self._reply(
            "Hi! I'm PayPilot. Tell me what you want to buy — for example, "
            "'Find me noise-cancelling headphones under $200' — and I'll find "
            "it, compare options, and check you out."
        )
