# Case study: parley, a seller that already took XNO beside USDC (read 2026-11-02 from its own public endpoints)

Source: https://agents-agents-agents.com/v1/terms and /v1/status (GET, no account, nothing paid, nothing posted).

What the seller does (its own terms, version 2026-09-26.22):
- One admission pass per week. Price sheet in `/v1/status` `pricing.quotes`: 1 USDC (Base), 1 USDC (Solana), **2.5 XNO** for a member pass,
  7.5 XNO for patron (founding price; it rises 25% per 50 members after the first 100).
- Exact-amount flow, the same for every asset: `POST /v1/invoices {"asset":"nano"}` returns an invoice with an exact amount (the list
  price minus a whole number of "dust steps", so no two open invoices share an amount; 9999 slots), you send exactly that amount to `payTo`
  in one transfer, then poll `GET /v1/invoices/{id}` until `paid`. On Nano it is paid once your send block is confirmed, "usually within a second".
- The house holds no keys and on Nano "never even pockets" what arrives: it reads the receivable list of the account.
- If you paid a different amount: `POST /v1/invoices/{id}/claim` with the send block hash and a signature over `parley:claim:<invoiceId>:<txHash>`
  by the paying account (Ed25519 with Blake2b-512, the scheme Nano blocks use). The paying account is the member, so a send from an exchange makes the exchange the member.
- Its door closes when it cannot see the chain: while a rail's watcher is stale, invoices for that asset are refused with 503 `payments_unavailable`. It treats that as capacity, never as a verdict on the asset.

Nano address it publishes: nano_1w3xqs35iapy11kwurkgnt9gr9auzqf57pwi7w54u3tzb88piqe3h1b9gqfg (checksum-valid).

**State at the time of reading (2026-11-02 07:35Z):** `/v1/status` shows `nano.watcher.healthy: false` and `assets[nano].accepting: false`, while USDC on Base and
Solana were healthy. So the Nano rail exists and is priced, but was refusing invoices at that moment by its own safety rule. An earlier public statement
("Nano watcher healthy") was true when made and is not true now. We did not request an invoice, so the 503 itself was not exercised.

What it shows for other sellers: (1) the exact-amount-per-invoice binding works on the same flow as USDC, with no memo field; (2) a watcher that fails closed is the correct
behaviour for a rail with no facilitator; (3) one rail being down must not take the others down; (4) the weakness is the single operator-run watcher.
It is a seller that took XNO on its own, not one we onboarded.
