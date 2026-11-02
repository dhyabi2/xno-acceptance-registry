# Which x402 facilitators and catalogs can list nano:mainnet

Probed 2026-11-02T07:34Z by `probe_listing.py` (one unauthenticated GET each, nothing paid) and `scan_bazaar.py`. Excluded on purpose: the x402-foundation repos and the foundation-run x402.org facilitator.

## Facilitators (GET /supported)

| facilitator | HTTP | result |
|---|---|---|
| PayAI | 200 | supports 34 networks, no nano |
| Coinbase CDP | 401 | needs credentials; /supported not readable |
| x402.rs | 200 | supports 19 networks, no nano |
| Dexter | 200 | supports 28 networks, no nano |
| Mogami | 200 | supports 2 networks, no nano |
| OpenX402 | 200 | supports 4 networks, no nano |
| Ultravioleta DAO | 200 | supports 88 networks, no nano |
| Daydreams | 200 | supports 10 networks, no nano |
| Polygon | 200 | supports 2 networks, no nano |
| thirdweb | 401 | needs credentials; /supported not readable |
| Corbits | - | unreachable (URLError) |
| Heurist | - | unreachable (URLError) |

No facilitator that publishes /supported lists a Nano network. Two need credentials (unknown, not 'no'); two did not answer.
A Nano seller does not need a facilitator: it can verify the block itself (https://github.com/dhyabi2/dual-rail, https://github.com/dhyabi2/nano-settlement-verify).

## Catalogs

| catalog | HTTP | result |
|---|---|---|
| Coinbase x402 Bazaar (CDP discovery, first 1000 of ~70k; full count: scan_bazaar.py) | 200 | no nano found in the page/feed |
| x402scan | 200 | no nano found in the page/feed (home page only; if it is rendered by script, this says little) |
| pursekeeper.dev | 200 | mentions nano/xno |
| x402 Bazaar (x402.org docs) | 200 | no nano found in the page/feed |
| agentic.market | 200 | no nano found in the page/feed (home page only; if it is rendered by script, this says little) |
| 402index.io | 200 | no nano found in the page/feed (home page only; if it is rendered by script, this says little) |

## Coinbase x402 Bazaar, full scan

69935 of 69878 discovery resources read; 51 distinct networks. **17 resources declare `nano:mainnet`** from 1 payTo address(es) on 2 host(s): pyfile-agent.taile3ff35.ts.net, pyfile-agent.taile3ff35.ts.net:10000.
So the Bazaar can list nano:mainnet entries today: it also lists xrpl, stellar, algorand, stacks, hyperliquid and others. What we have not established is the route by which that seller got in (which facilitator or crawler), or whether the listing is searchable by network. That is the question to ask.

## Asks (drafts, not sent)
See `claude/drafts/facilitator-catalog-asks-2026-11-02.md` in dhyabi2/swarm-decisions. Answers are recorded below when they arrive.

| who | asked | answer |
|---|---|---|
| Coinbase CDP Bazaar | not yet | - |
| PayAI | not yet | - |
| x402.rs | not yet | - |
| Dexter | not yet | - |
| Ultravioleta DAO | not yet | - |
| x402scan | not yet | - |

Rebuild: `python3 probe_listing.py listing-status.json && python3 scan_bazaar.py bazaar-scan.json && python3 build_table.py`.
