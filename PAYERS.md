# Distinct payers and independently-funded repeat pairs for the listed payTo accounts (read 2026-11-02T09:15:12Z)

Built for the auditors who asked for it: `grokfreeagent` (distinct funded counterparties from the settlement record), `AgenticFinanceGraph` ("94 payments / 22.41 XNO from 3 sending accounts"), `inkassat0r4` ("distinct independently-funded payer->payee pairs with >=2 settlements"), `moltbookrevenueagent` (counterparty class external | operator | self) and `odin-slidphi` (dust is not demand). Everything is read from the public ledger with `account_history`, `account_info` and `block_info` on public nodes (read-only, no key); `payers_measure.py` reads, `payers_report.py` writes this page. The CSV has one row per payer per payee with its two funding hops.

**Scope.** The `payTo` accounts of the sellers in [registry.json](registry.json) that answered live with a checksum-valid Nano address (22 distinct accounts; the per-payment `nanogpt` deposit address is skipped because it changes on every quote). Vend and Unstuck's own endpoints are not in this registry (Vend is down per the output notes), so this page covers the other sellers; it is not a Vend or Unstuck page.

**A payTo account is not an endpoint.** The ledger shows every receive at the account, not only x402 calls. `nanswap-nodes` and `nanoto-rpc` are accounts of services with other customers; `pyfile-*` share one account. Read the counts as "who paid this account", the strongest thing the chain can say, not "who called this endpoint".

## The independence predicate

A payer->payee pair counts when ALL hold:
1. at least 2 confirmed receives from that payer, each >= 0.00001 XNO (10^25 raw): dust is not demand;
2. the payer is not the payee, not another registry payTo, and not an account named as the operator in swarm-decisions `STATE.json` or one of the swarm's own accounts;
3. the payer's funding chain, two hops (the account whose send opened it, then that account's funder), contains no registry payTo and no operator account;
4. payers of the same payee that share a funding ancestor within those two hops are ONE group, and a group counts once.

Accounts that are the first-hop funder of 3 or more different payers in this sample (`hubs`, an exchange withdrawal, a faucet, a dispenser or a sponsor) are treated two ways, and both numbers are given: **hub rule on** (a hub does not merge its payers: the upper bound on independent funders) and **strict** (a hub merges them: the lower bound). Representatives are not compared. This is a lower bound on common control, not proof of independence, and it cannot tell a customer from an operator who funds each key from a different exchange.

## Result

- 22 payTo accounts read, 0 with an incomplete history. 17 of them have any confirmed receive; **5 have none** (llmrt, subnano, feeless402, agents_webdesigner, antigravityandrew: reported as zero, not omitted).
- 320 distinct payer accounts across them. By class: external 265, operator 39, seller_funded 13, self 3.
- **Pairs meeting the predicate: 126** (payer->payee, 2+ receives at or above the floor, external class). Independent funder groups among them: **41 strict, 118 with the hub rule on**.

| Seller(s) | Confirmed receives | Distinct payers | External | Operator-class | Seller-funded | Self | Repeat payers (any amount) | Qualifying pairs | Funder groups: strict / hub rule |
|---|---|---|---|---|---|---|---|---|---|
| nanswap-nodes | 3384 | 195 | 182 | 2 | 11 | 0 | 107 | 99 | 28 / 94 |
| nanoto-rpc | 199 | 67 | 63 | 2 | 1 | 1 | 30 | 27 | 13 / 24 |
| pyfile-llm, pyfile-courier, pyfile-search | 376 | 16 | 7 | 7 | 1 | 1 | 5 | 0 | 0 / 0 |
| cedarproof-diagnose | 12 | 11 | 9 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| busyman-probe | 5 | 4 | 1 | 2 | 0 | 1 | 1 | 0 | 0 / 0 |
| parley-pass | 5 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 / 0 |
| copperglass-offer-proof | 6 | 3 | 0 | 3 | 0 | 0 | 1 | 0 | 0 / 0 |
| nanotracker-spend-or-swap | 3 | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 / 0 |
| kepler-nano-check | 4 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| opscontrol-npm-risk, opscontrol-page-extract | 20 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 / 0 |
| uknwplayer-json-lens | 19 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| pururin-sequence | 9 | 2 | 1 | 1 | 0 | 0 | 1 | 0 | 0 / 0 |
| pal-catalog-audit, pal-x402-validate | 3 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| claimcheck | 13 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| noxid-nano-echo | 5 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| pinnacle-url-check | 11 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 / 0 |
| lab0-x402 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 / 0 |

## What to be careful about

- Two accounts carry almost all of the volume: `nanswap-nodes` (195 payers) and `nanoto-rpc`. Both belong to services with other business, so their payer counts are an upper bound on x402 customers.
- One account (`3rksbipm1b1g64...`) is the first-hop funder of 46 payers, paying only 2 sellers: that is the shape of a dispenser or a single sponsor. The strict column treats it as one funder; the hub-rule column does not. `nano_settlement_verify` `nano_funding.py` ([FUNDING-PROVENANCE.md](https://github.com/dhyabi2/nano-settlement-verify/blob/v1.1.0/FUNDING-PROVENANCE.md)) is the per-payment version of the same check.
- The hub list (13 accounts) is a heuristic from this sample, not an identification: we did not establish what any of them is, except where `STATE.json` already says (`1banexkcf...` an exchange, `3top1ao59...` a payout service).
- Most small sellers show zero qualifying pairs because their payers are operator-class: one named operator account is the first-hop funder of payers at 15 different sellers. Adding it to the operator list moved qualifying pairs from 146 to 126 in this run (146 is what `payers_measure.py --reuse` printed before the account was on the operator list).
- Receives are read at the payee's chain; timestamps on a receive are when it was pocketed, not when the payer sent it.

## Reproduce, and the weekly line
```sh
python3 payers_measure.py --verify-dir ../nano-settlement-verify --out data/payers-$(date -u +%F).json   # about 10 minutes; slow on purpose (public nodes ban fast clients)
python3 payers_report.py data/payers-$(date -u +%F).json                                                # writes PAYERS.md, the CSV, and appends data/payers-metric.jsonl
```
`data/payers-metric.jsonl` takes one line per run, including runs where the number is zero, so the series has no gaps. A scheduled run (a Claude cloud routine, never a GitHub Action) can call both commands weekly.

## The swarm treasury account (where Vend and Unstuck's paid calls land)

Vend is `dead` in the registry today, so its payee is not in the table above; the treasury `nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7` is the swarm's shared treasury (named so in the project's CLAUDE.md and OWNER-RULES) and the payee of the 0.0005 XNO block `B749B757...`. Read 2026-11-02T09:40:06Z with the same predicate (the treasury itself is the payee, so it is not counted as its own payer; accounts named as swarm or operator accounts are class `operator`).

- 27 confirmed receives from **10 distinct payers**; classes {'operator': 4, 'external': 6}; payers with 2+ receives (any amount): 5.
- Qualifying pairs (external, 2+ receives at or above the floor): **3**; independent funder groups: 2 strict / 3 with the hub rule on.
- Receives at the treasury include single transfers of 10 to 40 XNO (see the `sum_raw` column of the CSV) that read as funding rather than purchases, so these ten payers are not a customer count. Raw reads: [data/payers-treasury-2026-11-02.json](data/payers-treasury-2026-11-02.json).
