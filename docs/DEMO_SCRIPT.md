# PayPilot demo video script — under 3 minutes

**Format:** screen recording with voiceover, uploaded to YouTube (public).
No copyrighted music. Total target: **2:30**.

---

## 0:00–0:20 — The problem (20s)
> "Online checkout is still forms, carts, and tab-switching. What if you could
> just *tell* an AI what you want — and it shops and pays for you, safely?
> Meet **PayPilot**, my agentic commerce copilot for the PayPal AI Hackathon."

Show the landing page: chat UI + "SANDBOX MODE" badge.

## 0:20–1:10 — Live agentic purchase (50s)
1. Type: **"Find me noise-cancelling headphones under $200"**
2. Agent calls `search_products` → shows Aurora X9 ($189.99) vs PulseBuds Pro,
   compares, recommends one. *(Show this is real tool use, briefly.)*
3. Type: **"Yes, buy the Aurora X9"**
4. Agent calls `create_checkout` → **real PayPal sandbox order** appears;
   approval link shown in chat.
5. Click the link → PayPal sandbox login (buyer test account) → **Approve**.
   *(Pre-log the buyer account to keep this under 15s.)*

## 1:10–1:50 — Capture + receipt (40s)
6. Back in chat: **"I approved it"** → agent checks order status
   (`APPROVED`) → `capture_payment` → receipt with capture ID, amount, payer.
7. Pan to the **order history table** (AG Grid): the order flips to
   `COMPLETED` live.

## 1:50–2:30 — Why it matters (40s)
> "PayPilot is agentic commerce with consent baked into the code: the agent
> can't create an order you didn't confirm, and can't capture a payment PayPal
> hasn't approved. PayPal Sandbox handles the money; the AI handles the
> shopping. One chat, zero forms."
>
> "Built with FastAPI, PayPal Orders API v2, and AG Grid — MIT licensed, link
> in the description."

End card: repo URL + hackathon name.

---

## Recording checklist (human)
- [ ] `.env` filled with sandbox + LLM keys; app running locally
- [ ] Sandbox **buyer** account created and login saved in the browser
- [ ] Do one full dry run first (fresh order each take — sandbox orders can't be reused)
- [ ] Record at 1080p, system audio off, voiceover clear
- [ ] Keep under 3:00 — judges aren't required to watch past that
