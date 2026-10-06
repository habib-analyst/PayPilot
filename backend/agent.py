"""
PayPilot agent — a ReAct-style agentic commerce loop.

Flow the agent can execute:
  user message -> search_products -> shortlist -> confirm with user
  -> create_checkout (PayPal sandbox order) -> approval URL to user
  -> user approves in PayPal sandbox -> capture_payment -> receipt

Safety rules enforced in code (not just in the prompt):
- create_checkout requires an explicit user confirmation naming the product id.
- capture_payment only runs after the PayPal order status is APPROVED.
- Every tool result is real: catalog lookups and PayPal API responses only.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from . import catalog
from .llm import LLM, SYSTEM_PROMPT, fmt_tool_result
from .paypal_client import PayPalClient, PayPalError

MAX_STEPS = 8

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the demo store catalog. Returns up to 6 matching products with id, name, price, rating, description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the user is looking for, e.g. 'noise cancelling headphones'"},
                    "max_price": {"type": "number", "description": "Maximum price in USD (optional)"},
                    "category": {"type": "string", "description": "One of: audio, computing, wearables, cameras, accessories, home, travel (optional)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get full details of one product by id.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checkout",
            "description": (
                "Create a PayPal SANDBOX order for a product and get the buyer approval URL. "
                "Call ONLY after the user explicitly confirmed the exact product (they must name it or say 'yes, buy it'). "
                "The buyer must approve the order at the returned URL before anything is charged."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "default": 1},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_payment",
            "description": (
                "Capture a PayPal order AFTER the buyer approved it. "
                "Call ONLY when the user confirms they approved the order in PayPal, or after check_order shows APPROVED."
            ),
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_order",
            "description": "Check the current status of a PayPal order (CREATED, APPROVED, COMPLETED...).",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
]


class OrderStore:
    """In-memory order history (demo). Swap for a DB in production."""

    def __init__(self) -> None:
        self.orders: list[dict] = []

    def add(self, entry: dict) -> dict:
        entry = {"id": uuid.uuid4().hex[:8], "time": datetime.now(timezone.utc).isoformat(), **entry}
        self.orders.append(entry)
        return entry

    def all(self) -> list[dict]:
        return list(reversed(self.orders))


class Agent:
    def __init__(self) -> None:
        self.llm = LLM()
        self.paypal = PayPalClient()
        self.store = OrderStore()
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # ---------- tool implementations ----------

    def _run_tool(self, name: str, args: dict) -> object:
        if name == "search_products":
            return catalog.search(args.get("query", ""), args.get("max_price"), args.get("category"))
        if name == "get_product":
            p = catalog.get(args.get("product_id", ""))
            return p or {"error": "unknown product id"}
        if name == "create_checkout":
            p = catalog.get(args.get("product_id", ""))
            if not p:
                return {"error": "unknown product id"}
            qty = max(1, int(args.get("quantity", 1)))
            try:
                order = self.paypal.create_order(
                    [{"name": p["name"], "unit_price": p["price"], "quantity": qty, "sku": p["id"]}]
                )
            except PayPalError as e:
                return {"error": str(e)}
            self.store.add({
                "product": p["name"], "total": order["total"], "currency": order["currency"],
                "paypal_order_id": order["order_id"], "status": "AWAITING_APPROVAL",
            })
            return {
                "order_id": order["order_id"],
                "total": order["total"],
                "currency": order["currency"],
                "approve_url": order["approve_url"],
                "next": "Share the approve_url with the user. They must approve in the PayPal sandbox, then confirm back.",
            }
        if name == "check_order":
            try:
                body = self.paypal.get_order(args.get("order_id", ""))
            except PayPalError as e:
                return {"error": str(e)}
            return {"order_id": body.get("id"), "status": body.get("status")}
        if name == "capture_payment":
            order_id = args.get("order_id", "")
            try:
                status_body = self.paypal.get_order(order_id)
            except PayPalError as e:
                return {"error": str(e)}
            if status_body.get("status") != "APPROVED":
                return {
                    "error": f"Order is {status_body.get('status')}, not APPROVED. "
                             "The buyer must approve it at the approval URL first."
                }
            try:
                receipt = self.paypal.capture_order(order_id)
            except PayPalError as e:
                return {"error": str(e)}
            for o in self.store.orders:
                if o.get("paypal_order_id") == order_id:
                    o["status"] = "COMPLETED"
            return {"receipt": receipt}
        return {"error": f"unknown tool {name}"}

    # ---------- conversation ----------

    def chat(self, user_text: str) -> dict:
        self.history.append({"role": "user", "content": user_text})
        assistant_text = ""
        events: list[dict] = []

        for _ in range(MAX_STEPS):
            msg = self.llm.chat(self.history, tools=TOOLS)
            tool_calls = msg.get("tool_calls") or []
            assistant_text = msg.get("content") or ""

            if not tool_calls:
                break

            # keep a clean assistant message (without tool_calls) for history
            self.history.append({"role": "assistant", "content": assistant_text or "(calling tools…)"})
            for tc in tool_calls:
                fname = tc["function"]["name"]
                try:
                    fargs = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    fargs = {}
                result = self._run_tool(fname, fargs)
                events.append({"tool": fname, "args": fargs, "result": result})
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", fname),
                    "content": fmt_tool_result(fname, result),
                })
        else:
            assistant_text = assistant_text or "I hit my step limit — could you rephrase that?"

        if not assistant_text:
            # model only called tools on the last step; ask for the final summary
            self.history.append({"role": "user", "content": "Summarize what you just did for me in a short reply."})
            msg = self.llm.chat(self.history)
            assistant_text = msg.get("content") or ""

        self.history.append({"role": "assistant", "content": assistant_text})
        # keep history bounded
        self.history = [self.history[0]] + self.history[-20:]
        return {"reply": assistant_text, "events": events}

    def order_history(self) -> list[dict]:
        return self.store.all()

    def reset(self) -> None:
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
