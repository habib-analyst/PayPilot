"""
PayPal Sandbox REST client — Orders API v2.

Uses only the free PayPal sandbox (https://api-m.sandbox.paypal.com).
No real money moves: all orders are created/captured against sandbox
buyer/seller test accounts.

Required env vars (see .env.example):
    PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
Optional:
    PAYPAL_MODE            (default "sandbox"; only "sandbox" is supported here)
    PAYPAL_BRAND_NAME      (shown on the PayPal approval page)
    PAYPAL_RETURN_URL      (where PayPal sends the buyer after approval)
    PAYPAL_CANCEL_URL      (where PayPal sends the buyer on cancel)
"""

from __future__ import annotations

import base64
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


class PayPalError(RuntimeError):
    pass


class PayPalClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        brand_name: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET", "")
        if not self.client_id or not self.client_secret:
            raise PayPalError(
                "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not set. "
                "Create a free sandbox app at https://developer.paypal.com "
                "and copy them into your .env (see .env.example)."
            )
        self.mode = "SANDBOX"
        self.brand_name = brand_name or os.getenv("PAYPAL_BRAND_NAME", "PayPilot Demo Store")
        self.return_url = return_url or os.getenv("PAYPAL_RETURN_URL", "https://example.com/return")
        self.cancel_url = cancel_url or os.getenv("PAYPAL_CANCEL_URL", "https://example.com/cancel")
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.Client(base_url=SANDBOX_BASE, timeout=30.0)

    # ---------- auth ----------

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = self._http.post(
            "/v1/oauth2/token",
            headers={"Authorization": f"Basic {basic}"},
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code != 200:
            raise PayPalError(f"PayPal OAuth failed ({resp.status_code}): {resp.text[:300]}")
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 30000))
        return self._token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }

    # ---------- orders ----------

    def create_order(
        self,
        items: list[dict[str, Any]],
        currency: str = "USD",
        intent: str = "CAPTURE",
    ) -> dict[str, Any]:
        """Create a PayPal order. Returns order id + approval URL for the buyer."""
        total = sum(float(i["unit_price"]) * int(i.get("quantity", 1)) for i in items)
        payload = {
            "intent": intent,
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{total:.2f}",
                        "breakdown": {
                            "item_total": {"currency_code": currency, "value": f"{total:.2f}"}
                        },
                    },
                    "items": [
                        {
                            "name": i["name"][:127],
                            "unit_amount": {
                                "currency_code": currency,
                                "value": f"{float(i['unit_price']):.2f}",
                            },
                            "quantity": str(int(i.get("quantity", 1))),
                            "sku": i.get("sku", "")[:127],
                        }
                        for i in items
                    ],
                }
            ],
            "application_context": {
                "brand_name": self.brand_name[:127],
                "landing_page": "LOGIN",
                "user_action": "PAY_NOW",
                "return_url": self.return_url,
                "cancel_url": self.cancel_url,
            },
        }
        resp = self._http.post("/v2/checkout/orders", headers=self._headers(), json=payload)
        if resp.status_code not in (200, 201):
            raise PayPalError(f"create_order failed ({resp.status_code}): {resp.text[:500]}")
        body = resp.json()
        approve_url = next(
            (l["href"] for l in body.get("links", []) if l.get("rel") == "approve"), ""
        )
        return {
            "order_id": body["id"],
            "status": body.get("status"),
            "approve_url": approve_url,
            "total": f"{total:.2f}",
            "currency": currency,
        }

    def get_order(self, order_id: str) -> dict[str, Any]:
        resp = self._http.get(f"/v2/checkout/orders/{order_id}", headers=self._headers())
        if resp.status_code != 200:
            raise PayPalError(f"get_order failed ({resp.status_code}): {resp.text[:500]}")
        return resp.json()

    def capture_order(self, order_id: str) -> dict[str, Any]:
        """Capture an APPROVED order. Returns capture details / receipt data."""
        resp = self._http.post(
            f"/v2/checkout/orders/{order_id}/capture", headers=self._headers(), json={}
        )
        if resp.status_code not in (200, 201):
            raise PayPalError(f"capture_order failed ({resp.status_code}): {resp.text[:500]}")
        body = resp.json()
        captures: list[dict[str, Any]] = []
        for pu in body.get("purchase_units", []):
            for cap in pu.get("payments", {}).get("captures", []):
                captures.append(
                    {
                        "capture_id": cap.get("id"),
                        "status": cap.get("status"),
                        "amount": cap.get("amount", {}).get("value"),
                        "currency": cap.get("amount", {}).get("currency_code"),
                        "create_time": cap.get("create_time"),
                    }
                )
        return {
            "order_id": body.get("id"),
            "status": body.get("status"),
            "payer_email": (body.get("payer") or {}).get("email_address"),
            "captures": captures,
        }


class MockPayPalClient:
    """Local stand-in for PayPalClient with the same public interface.

    Used ONLY when PAYPILOT_MOCK_PAYPAL=1. PayPal sandbox signup is
    unavailable in Pakistan, so no live PayPal run is possible from there.
    No network call is made and no money moves: orders live in memory
    and move CREATED -> APPROVED -> COMPLETED exactly like sandbox
    orders. Every payload is sandbox-shaped but clearly fake (order ids
    start with MOCK-, the payer is mock-buyer@example.test), and the
    frontend labels every mock order MOCK. A mock run must never be
    presented as a live PayPal run.
    """

    mode = "MOCK"

    def __init__(self, public_url: str | None = None) -> None:
        self.public_url = (
            public_url or os.getenv("PAYPILOT_PUBLIC_URL", "http://localhost:8000")
        ).rstrip("/")
        self._orders: dict[str, dict[str, Any]] = {}

    def create_order(
        self,
        items: list[dict[str, Any]],
        currency: str = "USD",
        intent: str = "CAPTURE",
    ) -> dict[str, Any]:
        """Create a mock order. Returns order id + local approval URL."""
        total = sum(float(i["unit_price"]) * int(i.get("quantity", 1)) for i in items)
        order_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        self._orders[order_id] = {
            "id": order_id,
            "status": "CREATED",
            "items": items,
            "total": f"{total:.2f}",
            "currency": currency,
            "intent": intent,
            "payer_email": None,
            "capture_id": None,
        }
        return {
            "order_id": order_id,
            "status": "CREATED",
            "approve_url": f"{self.public_url}/mock-approve?order_id={order_id}",
            "total": f"{total:.2f}",
            "currency": currency,
        }

    def get_order(self, order_id: str) -> dict[str, Any]:
        order = self._orders.get(order_id)
        if order is None:
            raise PayPalError(f"unknown mock order {order_id}")
        body: dict[str, Any] = {
            "id": order["id"],
            "status": order["status"],
            "intent": order["intent"],
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": order["currency"],
                        "value": order["total"],
                    }
                }
            ],
        }
        if order["payer_email"]:
            body["payer"] = {"email_address": order["payer_email"]}
        return body

    def approve_order(self, order_id: str) -> dict[str, Any]:
        """Local mock-approval step: stands in for the PayPal buyer login."""
        order = self._orders.get(order_id)
        if order is None:
            raise PayPalError(f"unknown mock order {order_id}")
        if order["status"] != "CREATED":
            raise PayPalError(
                f"mock order is {order['status']}, not CREATED; cannot approve"
            )
        order["status"] = "APPROVED"
        order["payer_email"] = "mock-buyer@example.test"
        return {"order_id": order_id, "status": "APPROVED"}

    def capture_order(self, order_id: str) -> dict[str, Any]:
        """Capture an APPROVED mock order. Returns mock receipt data."""
        order = self._orders.get(order_id)
        if order is None:
            raise PayPalError(f"unknown mock order {order_id}")
        if order["status"] != "APPROVED":
            raise PayPalError(
                f"mock order is {order['status']}, not APPROVED. "
                "The buyer must approve it at the approval URL first."
            )
        order["status"] = "COMPLETED"
        order["capture_id"] = f"MOCKCAP-{uuid.uuid4().hex[:12].upper()}"
        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "payer_email": order["payer_email"],
            "captures": [
                {
                    "capture_id": order["capture_id"],
                    "status": "COMPLETED",
                    "amount": order["total"],
                    "currency": order["currency"],
                    "create_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
