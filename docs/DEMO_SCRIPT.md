# PayPilot demo video script — under 3 minutes

**Format:** screen recording with voiceover, uploaded to YouTube (public).
No copyrighted music. Total target: **2:30**.

---

## 0:00–0:20 — The problem (20s)
> "Online checkout is still forms, carts, and tab-switching. What if you could
> just *tell* an AI what you want — and it shops and pays for you, safely?
> Meet **PayPilot**, my agentic commerce copilot for the PayPal AI Hackathon."

Show the landing page: chat UI + "MOCKED CHECKOUT" badge (mocked checkout is
disclosed on screen — see below).

## 0:20–1:10 — Live agentic purchase (50s)
1. Type: **"Find me noise-cancelling headphones under $200"**
2. Agent calls `search_products` → shows Aurora X9 ($189.99) vs PulseBuds Pro,
   compares, recommends one. *(Show this is real tool use, briefly.)*
3. Type: **"Yes, buy the Aurora X9"**
4. Agent calls `create_checkout` → **mock PayPal order** appears (labeled
   MOCK); approval link shown in chat.
5. Click the link → local mock-approval page → **Approve (mock)**.
   *(No PayPal login: sandbox signup is unavailable in Pakistan, so checkout
   is simulated and labeled MOCK throughout — the page says so.)*

## 1:10–1:50 — Capture + receipt (40s)
6. Back in chat: **"I approved it"** → agent checks order status
   (`APPROVED`) → `capture_payment` → receipt with mock capture ID, amount,
   mock payer.
7. Pan to the **order history table** (AG Grid): the order flips to
   `COMPLETED` live.

## 1:50–2:30 — Why it matters (40s)
> "PayPilot is agentic commerce with consent baked into the code: the agent
> can't create an order you didn't confirm, and can't capture a payment that
> hasn't been approved. One chat, zero forms."
>
> "One honest note: the checkout in this demo is mocked — PayPal sandbox
> signup isn't available in Pakistan — so every order is labeled MOCK and no
> real PayPal transaction happens. The agent loop, the tools, and the receipts
> are the real code paths; only the PayPal call is simulated."
>
> "Built with FastAPI, PayPal Orders API v2, and AG Grid — MIT licensed, link
> in the description."

End card: repo URL + hackathon name.

---

## Recording checklist (human)
- [ ] Mock mode on: `PAYPILOT_MOCK_PAYPAL=1`, app running locally
      (no PayPal keys needed; the scripted run needs no LLM key either,
      the real-LLM run needs only `LLM_API_KEY`)
- [ ] Do one full dry run first (fresh order each take — mock orders can't be reused)
- [ ] Record at 1080p, system audio off, voiceover clear
- [ ] Keep under 3:00 — judges aren't required to watch past that
