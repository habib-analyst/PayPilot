"""
PayPilot — agentic commerce copilot for the PayPal AI Hackathon 2026.

Run:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
Then open http://localhost:8000
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    ok = bool(os.getenv("LLM_API_KEY")) and bool(os.getenv("PAYPAL_CLIENT_ID"))
    return {"ok": ok, "service": "paypilot", "mode": "paypal-sandbox"}


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


# --- frontend ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
