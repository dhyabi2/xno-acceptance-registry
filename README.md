# xno-acceptance-registry

A machine-readable list of sellers an agent can pay in XNO, **each probed live on 2026-11-02T06:07Z**, every `payTo` checksum-validated by code in this repo. Public domain (CC0 data, MIT code).

- `registry.json`: all 39 entries with state, probe result, evidence level and payTo checksum flag
- `feeds/nano-sellers.json` / `.csv`: only entries that answered live today with a valid Nano payTo (26), in x402 `accepts[]` shape, for directories and catalogs
- [SUBCENT-TARGETS.md](SUBCENT-TARGETS.md): sub-cent x402 hosts with real traffic and no XNO (public Bazaar list, 2026-11-02); [PAYERS.md](PAYERS.md): distinct and independently-funded payers of the listed payTo accounts
- `build.py` re-probes everything (one **unpaid** request each; nothing is paid); `feeds.py` derives the feeds; `tests/` check the file

## Today (2026-11-02T06:07Z)
Counts: {"dead": 8, "live_402_nano": 25, "live_portal": 1, "live_status_route": 2, "mail_only": 2, "unclear": 1, "total": 39}

States: `live_402_nano` answered 402 and the 402 carries a Nano payTo; `live_portal` operator page prints the address (operator's statement, no 402 route read); `live_status_route` the seller's declared status route answered as declared, payTo not read by us; `mail_only` contact by mail, not probed; `dead` no answer, 404/5xx, or deployment disabled; `unclear` answered but not as declared.

Evidence levels: `endpoint_read` (we read a Nano payTo from a live response), `operator_statement_plus_portal`, `unverified`. A live 402 shows that the seller *asks* for XNO; it does not show the seller delivers after payment. Listing parties' own paid-verification records are copied in `paid_verification_by_listing_party` where they gave one.
The `nanogpt` payTo is a per-payment deposit address and changes on every quote.

Source of the seed: the Nano seller list published at https://pursekeeper.dev/sellers.json (snapshot in `data/`), plus agents_webdesigner (read directly: `accepts[1]` = nano:mainnet, 50000000000000000000000000000 raw = 0.05 XNO) and antigravityandrew (portal prints its address). ARION, parley's members and ornithclaude are not rows: no payTo of theirs could be verified today (parley-pass is listed with its status route only).

## Live now
| id | state | HTTP | payTo | price quoted by operator |
|---|---|---|---|---|
| nanogpt | live_402_nano | 402 | nano_14r6q7get5jm99jpiski4y53tne6hxwi7c3n65ncabi9jmygp353o5zrqhhg | quoted per request; one small completion cost Ӿ0.00108 |
| llmrt | live_402_nano | 402 | nano_1jt74trsipkkzpsmhf37d5w1ydf531kbfotpnw7rrjg5k6brje43hwucweup | Ӿ8.1 per kit (3 USDT equivalent) |
| pyfile-llm | live_402_nano | 402 | nano_3uojbn47b5xqcbs4yibbasamn8aeyqxgyi1z8peogwtdn6z3kagjanjpz4ss | $0.005 per request, quoted in XNO by the 402 (Ӿ0.01438 on 2026-09-26;  |
| contract-lens | live_status_route | 400 | - | Ӿ0.01 per document pair |
| subnano | live_402_nano | 402 | nano_3zebpjamb8y66y7fgapcbocxfy8d1piqr1smnx71f6cwsazddwxu4c47urgf | per post, set by the author; the probe post is Ӿ0.00001, a typical art |
| feeless402 | live_402_nano | 402 | nano_3aysuejus8iy1hhw6doc7syzg1aaa6hgpec91xcc36mf6hp6thy7u6ymkgfm | Ӿ0.0001 per call |
| nanoto-rpc | live_402_nano | 402 | nano_1rpc19tpfzuotsk346bt674mehj96ju86n5xiop4o68mepqexf5f55xa7ycx | Ӿ0.001 per work_generate call (the 402 quote); one payment buys one ca |
| kepler-nano-check | live_402_nano | 402 | nano_1jyx763fmsr851ieufnztwh7jed8sssixhd4bsgwcj3rd31iwxaxtendnhu3 | Ӿ0.001 per answer |
| busyman-probe | live_402_nano | 402 | nano_1cniy53izwradscmqznu9bxpi6h73dfdcy6abirb7rnuxj7dcjqp5q5wjrga | Ӿ0.001 per probe |
| parley-pass | live_status_route | 200 | nano_1w3xqs35iapy11kwurkgnt9gr9auzqf57pwi7w54u3tzb88piqe3h1b9gqfg | Ӿ2.5 per 7-day member pass, Ӿ7.5 patron (founding price; rises 25% per |
| opscontrol-npm-risk | live_402_nano | 402 | nano_3mr761i87o7o33hmrd67a1emt81j6djgdqeyod95ip5qcidz77b71x4ukqea | Ӿ0.001 per report |
| uknwplayer-json-lens | live_402_nano | 402 | nano_1zwik4hd1pjy73owfah8xuxzokk6zexc5a6rs6byhrxryggkbh38kemm51yt | Ӿ0.01 per call |
| productos-sha256 | unclear | 200 | - | Ӿ0.001 per answer |
| pururin-sequence | live_402_nano | 402 | nano_13gz94zfz7747o4tag8t8y1yw7bmzzroi84ez7wg1fqu5iiju4r37ut7abrk | Ӿ0.001 per call |
| pyfile-courier | live_402_nano | 402 | nano_3uojbn47b5xqcbs4yibbasamn8aeyqxgyi1z8peogwtdn6z3kagjanjpz4ss | Ӿ0.02876 per job on 2026-09-28 (quoted in raw by the 402) |
| copperglass-offer-proof | live_402_nano | 402 | nano_1q7k9k6nwdxbiewh9yetp3tsuc4ry4w9d7j7h5nb9km5bq69j7515ryxe63i | Ӿ0.01 per report (an optional Ӿ10 prepaid route for 1,000 reports is a |
| pal-catalog-audit | live_402_nano | 402 | nano_1gcpoxg6o1heqtmub9srjbpdwoe9bm1n85tks3yznjhb9iywktixczc7ydpr | Ӿ0.01 per audit |
| claimcheck | live_402_nano | 402 | nano_3gtiea9weod3itxy5q69t95tr83d6ybdspxyqe5oihtu4ee457rswo8misot | Ӿ0.001 per verification |
| noxid-nano-echo | live_402_nano | 402 | nano_3154czz87etettuydyts5qg1798sqcqx1rpkropcu3h3t845pnr6y7gmz3ze | Ӿ0.0001 per call |
| pinnacle-url-check | live_402_nano | 402 | nano_1u5zktci5e4jtrcf9poq66pc5wk6g4mnmruh5h3dg1bdac63nj5kck5w453x | Ӿ0.01 per check (plus a per-invoice suffix below 0.00000000002) |
| pal-x402-validate | live_402_nano | 402 | nano_1gcpoxg6o1heqtmub9srjbpdwoe9bm1n85tks3yznjhb9iywktixczc7ydpr | Ӿ0.05 per validation |
| oso-pepe-courier | mail_only | None | - | 0.25 XNO per confirmed send block, or per confirmed open-and-send batc |
| cedarproof-diagnose | live_402_nano | 402 | nano_1rtip87co9td57n18tdq7996dsuuycotttnizprfr7nzobhabwkpyxwktxsh | Ӿ0.05 per classification |
| pyfile-search | live_402_nano | 402 | nano_3uojbn47b5xqcbs4yibbasamn8aeyqxgyi1z8peogwtdn6z3kagjanjpz4ss | Ӿ0.008628 per query on 2026-10-05 (quoted in raw by the 402; the USDC  |
| busleyden-csv-mail | mail_only | None | - | 0.25 XNO per accepted file; nothing before acceptance (the seller's ow |
| nanswap-nodes | live_402_nano | 402 | nano_115hp31z6kh5d66pggb15s4mxchqx1aah9jtqbeuhjdwaoqxoxo7o1yzpodk | $0.00003 per credit, quoted live in raw XNO; one work_generate cost Ӿ0 |
| opscontrol-page-extract | live_402_nano | 402 | nano_3mr761i87o7o33hmrd67a1emt81j6djgdqeyod95ip5qcidz77b71x4ukqea | Ӿ0.001 per page |
| nanotracker-spend-or-swap | live_402_nano | 402 | nano_19zs7s5cwnccx7nqyhukxhuxnjqk14xzicbhue1o9kn6n3bescfc8rbpwmdg | USD 0.001 per request, quoted in XNO at the day's rate in the 402 (Ӿ0. |
| lab0-x402 | live_402_nano | 402 | nano_3dj5gu116i41139tx83kfa4t9f5rcfmifqigmt9wnqoeunz6hjcp4h6uiz9z | Ӿ0.001 per call (1e27 raw; Ӿ0.005 when first asked on 2026-10-26, lowe |
| agents_webdesigner | live_402_nano | 402 | nano_39b311tznm9hub316enn8159ammduxnfonoaei7afzymw66wsouw9q3j9ic1 | 0.05 XNO per audit (accepts[1], as read) |
| antigravityandrew | live_portal | 200 | nano_3t1sxtuxyjgdabj6miwn6st58p8x553i8ybkikoc9ozn7mra7kk71iysfyn1 | $0.25 per 15 queries, order-keyed tagged raw amounts |

## Dead today (kept so nobody re-adds them blindly)
| id | state | HTTP | payTo | price quoted by operator |
|---|---|---|---|---|
| cleartable | dead | 404 | - | Ӿ0.01 per call |
| stringsafeqa | dead | None | - | Ӿ0.01 per audit |
| feed-weight-check | dead | 503 | - | Ӿ0.01 per batch of up to 100 records |
| oreomuncher-attest | dead | 525 | - | Per route, USD list price ($0.002 to $0.005 for most) converted to XNO |
| sur-courier | dead | 402 | - | Ӿ0.25 per confirmed block |
| northstar-linkcheck | dead | None | - | Ӿ0.01 per batch of up to 100 URL strings |
| vend | dead | None | - | Ӿ0.0001 per call (extract, status, check-link, web-search, geoip); Ӿ0. |
| apfs-probe | dead | None | - | Ӿ1 per probe call |

## Add or fix an entry
Open a pull request adding your endpoint to `extras.json` (id, operator, what, endpoint, price, a probe method). CI is not used; run `python3 build.py data/pursekeeper-sellers-2026-11-02.json extras.json registry.json && python3 feeds.py && python3 -m unittest discover -s tests`. Entries are removed only when the operator asks; downtime is shown as `dead`, not hidden.

Run the tests: `python3 -m unittest discover -s tests` (stdlib only, Python 3.9+).

## Also here
- `BOARD.md` (from `board.json` by `board.py`): sellers who say they take XNO, with address, their own published price and what the ledger shows today; for holders asking who accepts XNO.
- `feeds/nano-accepting-agents.json`: flat file, one row per payee (name, url, nano_address, verified_at) for directories that ingest a list.
- `listing/`: which x402 facilitators and catalogs can list nano:mainnet, probed and tracked (`listing/README.md`).
- `cases/parley.md`: a seller that already takes XNO beside USDC, read from its own endpoints.

- Wanted in XNO (a seller said "no demand yet"? count who asked): [WANTED-IN-XNO.md](WANTED-IN-XNO.md), request form `.github/ISSUE_TEMPLATE/request-xno-at-seller.yml`, counter `request_count.py` (distinct GitHub accounts per seller host; nothing seeded).
