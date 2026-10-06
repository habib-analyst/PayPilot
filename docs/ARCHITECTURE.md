# PayPilot architecture

```
browser (chat UI + AG Grid order table)
   │  POST /api/chat  ·  GET /api/orders
   ▼
FastAPI (backend/main.py)
   │
   ▼
Agent (backend/agent.py) — ReAct loop, max 8 steps
   ├── LLM (backend/llm.py) — OpenAI-compatible /chat/completions
   │      default: Google AI Studio (gemini-2.5-flash, free tier)
   ├── catalog.py — demo store (12 products, search/rank)
   ├── paypal_client.py — sandbox Orders API v2
   │      POST /v1/oauth2/token → access token
   │      POST /v2/checkout/orders → create (returns approval URL)
   │      GET  /v2/checkout/orders/{id} → status
   │      POST /v2/checkout/orders/{id}/capture → receipt
   └── OrderStore — in-memory order history → AG Grid table
```

## Tool contract (what the agent can do)

| Tool | Effect |
|---|---|
| `search_products(query, max_price?, category?)` | Ranked catalog search, top 6 |
| `get_product(product_id)` | Full product detail |
| `create_checkout(product_id, quantity?)` | PayPal sandbox order + buyer approval URL |
| `check_order(order_id)` | Live PayPal order status |
| `capture_payment(order_id)` | Capture **only if** status == APPROVED |

## Safety design (judges: read this)

Agentic commerce fails in the news when agents spend money without consent.
PayPilot enforces consent **in code**, not just in the prompt:

1. `create_checkout` is only called after the user names/confirms the product
   (prompt rule + the UI asks for confirmation).
2. `capture_payment` hard-blocks unless PayPal's own API reports the order
   as `APPROVED` — the agent cannot charge an unapproved order even if
   tricked by a prompt.
3. All money movement is sandbox-only; the client refuses to point at
   production (`api-m.sandbox.paypal.com` is hardcoded).

## Why this wins

- **Agentic commerce, for real:** not a chatbot FAQ — the agent executes a
  multi-step purchase with live payment rails.
- **PayPal is load-bearing:** remove PayPal and the app does nothing; remove
  AI and it does nothing. Both are meaningful, per the rules.
- **Sponsor overlap:** AG Grid Community powers the order table (eligible for
  Best Use of AG Grid on top of the PayPal categories).
