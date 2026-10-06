# PayPilot — your agentic commerce copilot

**PayPal AI Hackathon 2026 entry.** Tell PayPilot what you want to buy in plain
language; the AI agent searches the store, compares options, and checks you out
with **PayPal** — all inside one chat. Built for the hackathon's
**Best Use of Agentic Commerce** theme.

Demo video (under 3 min): *to be recorded — see `docs/DEMO_SCRIPT.md`.*

## What it does

1. **Conversational shopping** — "find me noise-cancelling headphones under $200"
2. **Agentic tool use** — the LLM really calls tools: `search_products`,
   `get_product`, `create_checkout`, `check_order`, `capture_payment`
3. **Real PayPal Sandbox checkout** — Orders API v2: create order → buyer
   approves at PayPal → agent captures → receipt. No real money moves.
4. **Safety rails in code** — checkout needs explicit user confirmation;
   capture is blocked until PayPal reports the order `APPROVED`.
5. **Order history dashboard** — AG Grid table of every order and its status.

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# Edit .env and paste:
#   PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET  (free sandbox app)
#   LLM_API_KEY                           (free Google AI Studio key)

# 2a. Run locally
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2b. Or with Docker
docker compose up --build
```

Open **http://localhost:8000** and start chatting.

### Get the free keys (5 minutes)

**PayPal sandbox**
1. Sign in at https://developer.paypal.com (free PayPal developer account)
2. Dashboard → *Apps & Credentials* → *Sandbox* → *Create App*
3. Copy **Client ID** and **Secret** into `.env`
4. *Testing Tools* → *Sandbox Accounts* → create a **buyer** account
   (you'll log in as this buyer to approve orders in the demo)

**LLM key (free)**
1. https://aistudio.google.com → *Get API key* (free tier)
2. Paste into `.env` as `LLM_API_KEY`
   (defaults already point at Google's OpenAI-compatible endpoint)

## Try it

- "Find me noise-cancelling headphones under $200"
- "I need a gift for someone who likes smart home gadgets"
- "Show me laptop accessories for remote work"

Then: confirm the product → the agent creates a PayPal order → click the
approval link, log in with your **sandbox buyer** account, approve → tell the
agent "I approved it" → it captures and shows the receipt.

## Tech

- **Backend:** FastAPI + a ReAct-style agent loop (tool-calling over an
  OpenAI-compatible chat API; swap `LLM_BASE_URL`/`LLM_MODEL` for any provider)
- **PayPal:** REST Orders API v2 on the **sandbox** (OAuth client-credentials,
  create/get/capture order)
- **Frontend:** vanilla JS chat + [AG Grid](https://www.ag-grid.com/)
  Community for the order-history table
- **Packaging:** Dockerfile + docker-compose, one-command run

## Prize categories targeted

- Best Use of Agentic Commerce ($5,000)
- Best Use of PayPal + AI ($5,000)
- Best Use of AG Grid ($5,000 / $2,000 / $1,000)
- Most Creative / Most Impactful / 1st–3rd Place

## License

MIT — see `LICENSE`.
