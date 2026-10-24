"""
PayPilot — agentic commerce copilot for the PayPal AI Hackathon 2026.

Run:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
Then open http://localhost:8000
"""

from __future__ import annotations

import html as htmlmod
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="PayPilot", version="0.1.0")

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        from .agent import Agent
        _agent = Agent()  # raises RuntimeError if LLM_API_KEY / PayPal creds missing
    return _agent


class ChatIn(BaseModel):
    message: str


@app.get("/api/health")
def health():
    mock = os.getenv("PAYPILOT_MOCK_PAYPAL") == "1"
    # The LLM is always available: real LLM with a key, scripted fallback
    # without one. Health therefore tracks PayPal readiness only.
    llm_mode = (
        "scripted"
        if os.getenv("PAYPILOT_SCRIPTED_LLM") == "1" or not os.getenv("LLM_API_KEY")
        else "real"
    )
    ok = mock or bool(os.getenv("PAYPAL_CLIENT_ID"))
    return {
        "ok": ok,
        "service": "paypilot",
        "mode": "mock-paypal" if mock else "paypal-sandbox",
        "llm": llm_mode,
    }


@app.post("/api/chat")
def chat(body: ChatIn):
    try:
        agent = get_agent()
    except (RuntimeError, Exception) as e:  # noqa: BLE001 - surface config errors clearly
        raise HTTPException(status_code=500, detail=str(e))
    try:
        return agent.chat(body.message)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Agent error: {e}")


@app.post("/api/reset")
def reset():
    get_agent().reset()
    return {"ok": True}


@app.get("/api/orders")
def orders():
    return {"orders": get_agent().order_history()}


# --- mocked checkout approval (mock mode only) ---
# Stands in for the PayPal buyer login: the demo video's "approve" click.
# No PayPal call is made and the page discloses that it is a mock.

def _mock_agent():
    if os.getenv("PAYPILOT_MOCK_PAYPAL") != "1":
        raise HTTPException(
            status_code=400,
            detail="Mock approval is only available with PAYPILOT_MOCK_PAYPAL=1",
        )
    agent = get_agent()
    if not getattr(agent, "mock_mode", False):
        raise HTTPException(status_code=400, detail="Agent is not in mock mode")
    return agent


@app.get("/mock-approve")
def mock_approve_page(order_id: str):
    agent = _mock_agent()
    try:
        body = agent.paypal.get_order(order_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(e))
    row = next(
        (o for o in agent.store.orders if o.get("paypal_order_id") == order_id), {}
    )
    product = htmlmod.escape(str(row.get("product", "Unknown product")))
    total = htmlmod.escape(str(row.get("total", body.get("purchase_units", [{}])[0].get("amount", {}).get("value", ""))))
    status = htmlmod.escape(str(body.get("status", "")))
    oid = htmlmod.escape(order_id)
    return HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Mock approval — PayPilot</title>
        <style>body{{font-family:system-ui;background:#0f1420;color:#e8ecf4;padding:40px}}
        .box{{background:#171e2e;border:1px solid #263049;border-radius:14px;padding:24px;max-width:520px}}
        .mock{{color:#f5b942;font-weight:700}} button{{padding:12px 24px;border-radius:10px;border:none;
        background:#4da3ff;color:#06121f;font-weight:700;cursor:pointer;font-size:1rem}}</style></head>
        <body><div class="box"><h2>PayPilot — mock approval</h2>
        <p class="mock">MOCKED CHECKOUT — this is NOT a PayPal transaction. PayPal sandbox
        is unavailable in Pakistan, so this page simulates the buyer approval step.</p>
        <p>Order: {oid}<br>Product: {product}<br>Total: ${total} USD<br>Status: {status}</p>
        <form method="post" action="/mock-approve">
        <input type="hidden" name="order_id" value="{oid}">
        <button type="submit">Approve (mock)</button></form></div></body></html>"""
    )


@app.post("/mock-approve")
def mock_approve_submit(order_id: str = Form(...)):
    agent = _mock_agent()
    try:
        agent.paypal.approve_order(order_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    oid = htmlmod.escape(order_id)
    return HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Mock approved — PayPilot</title>
        <style>body{{font-family:system-ui;background:#0f1420;color:#e8ecf4;padding:40px}}
        .box{{background:#171e2e;border:1px solid #263049;border-radius:14px;padding:24px;max-width:520px}}
        </style></head><body><div class="box"><h2>Mock order approved</h2>
        <p>Order {oid} is now APPROVED (mock — no PayPal transaction).</p>
        <p>Return to the PayPilot chat and type <b>"I approved it"</b> and the agent
        will capture it and show the receipt.</p></div></body></html>"""
    )


@app.post("/api/mock-approve/{order_id}")
def mock_approve_api(order_id: str):
    agent = _mock_agent()
    try:
        result = agent.paypal.approve_order(order_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, **result}


# --- frontend ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
