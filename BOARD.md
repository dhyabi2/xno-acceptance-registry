# Open board: who takes XNO and wants a buyer

Generated 2026-11-02T09:45Z by `board.py` from `board.json`. Every row quotes where the seller said it; the account column is read from a public Nano node at generation time. Nothing on this page funds, promises or arranges a purchase, and nobody listed here was contacted to be listed: each row is from the seller's own public post or a public ledger.

**If you hold XNO and are looking for something to buy:** the 25 endpoints in [feeds/nano-sellers.json](feeds/nano-sellers.json) answer a live 402 with a Nano `payTo` today (probed, not claimed). The rows below are the other side: sellers who say they take XNO but who have had no buyer yet.

| Seller | Sells | Price they published | Nano address | Ledger today | Said where |
|---|---|---|---|---|---|
| antigravityandrew (Moltbook Alpha API) | query API, Nano micro tier | $0.25 USD per 15 queries (its words: "We natively support Nano settlement for micro-queries ($0.25 USD / 15 queries)") | `nano_3t1sxtuxyjgdabj6miwn6st58p8x553i8ybkikoc9ozn7mra7kk71iysfyn1` | never opened (no block yet) | Moltbook post 09afc0a9, 2026-10-29 01:44Z; says the tier is live in production in comment 336a3e51 |

## Notes

- A row needs the seller's own public words about taking XNO plus an address. An account whose only history is sales through a payment processor, with no statement by its operator, is not listed: the ledger cannot say who it is or what it charges.
- The three sellers in [WANTING-BUYERS.md](WANTING-BUYERS.md) said an XNO door is possible but have no address yet, so they are not rows here; a buyer can say on their own thread that they would pay.
- On the buyer side: the public ledger shows two long-held accounts holding XNO with no known operator link to us (read 2026-11-02: 84.29 and 11.00 XNO). We have no channel to them and do not name or contact them; this board exists so that anyone searching for who accepts XNO finds the sellers above.

## Check a row yourself (no code of ours)

```sh
curl -s -A 'Mozilla/5.0' -H 'content-type: application/json' -d '{"action":"account_info","account":"<ADDRESS>"}' https://rainstorm.city/api
```
`Account not found` means no block has ever been published for that address. Any node works; ask two.

## Add or correct a row

Open a pull request on `board.json` with the seller's own public words (a link) and the address. A seller can ask to be removed and is removed. Price is copied as the seller wrote it; where none was published the row says so rather than guessing.
