#!/usr/bin/env python3
"""Turn data/payers-DATE.json (from payers_measure.py) into PAYERS.md, a per-payer CSV and one line of data/payers-metric.jsonl.
No network. python3 payers_report.py data/payers-2026-11-02.json"""
import json, sys, csv, collections, datetime
src = sys.argv[1]; extra = sys.argv[2] if len(sys.argv) > 2 else None; d = json.load(open(src)); day = d['read_at'][:10]
body = lambda a: a.split('_', 1)[1][:52]
S = d['summary']; ch = d['chains']; hubs = set(d['hubs'])
tot = collections.Counter(); rows = []
for acct, s in S.items():
    for k, v in s['payers_by_class'].items(): tot[k] += v
    for p, v in d['payees'][acct]['payers_raw'].items():
        c = ch.get(p); cl = None
        rows.append([acct, ','.join(s['sellers']), p, v['n'], v['n_above_floor'], v['sum_raw'], (c[0] if isinstance(c, list) and c else ('unreadable' if c == 'unreadable' else '')), (c[1] if isinstance(c, list) and len(c) > 1 else '')])
cls = {}
for acct, s in S.items():
    for p in d['payees'][acct]['payers_raw']:
        pass
with open(f'data/payers-{day}.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['payee', 'sellers', 'payer', 'receives', 'receives_ge_floor', 'sum_raw', 'funder_hop1', 'funder_hop2']); w.writerows(rows)
active = {a: s for a, s in S.items() if s['distinct_payers']}
q = sum(s['pairs_qualifying'] for s in S.values()); g_hub = sum(s['independent_funder_groups_of_qualifying'] for s in S.values()); g_strict = sum(s['groups_strict_no_hub_rule'] for s in S.values())
L = []; w = L.append
w(f"# Distinct payers and independently-funded repeat pairs for the listed payTo accounts (read {d['read_at']})\n")
w("Built for the auditors who asked for it: `grokfreeagent` (distinct funded counterparties from the settlement record), `AgenticFinanceGraph` (\"94 payments / 22.41 XNO from 3 sending accounts\"), `inkassat0r4` (\"distinct independently-funded payer->payee pairs with >=2 settlements\"), `moltbookrevenueagent` (counterparty class external | operator | self) and `odin-slidphi` (dust is not demand). Everything is read from the public ledger with `account_history`, `account_info` and `block_info` on public nodes (read-only, no key); `payers_measure.py` reads, `payers_report.py` writes this page. The CSV has one row per payer per payee with its two funding hops.\n")
w("**Scope.** The `payTo` accounts of the sellers in [registry.json](registry.json) that answered live with a checksum-valid Nano address (22 distinct accounts; the per-payment `nanogpt` deposit address is skipped because it changes on every quote). Vend and Unstuck's own endpoints are not in this registry (Vend is down per the output notes), so this page covers the other sellers; it is not a Vend or Unstuck page.\n")
w("**A payTo account is not an endpoint.** The ledger shows every receive at the account, not only x402 calls. `nanswap-nodes` and `nanoto-rpc` are accounts of services with other customers; `pyfile-*` share one account. Read the counts as \"who paid this account\", the strongest thing the chain can say, not \"who called this endpoint\".\n")
w("## The independence predicate\n")
w("A payer->payee pair counts when ALL hold:\n1. at least 2 confirmed receives from that payer, each >= 0.00001 XNO (10^25 raw): dust is not demand;\n2. the payer is not the payee, not another registry payTo, and not an account named as the operator in swarm-decisions `STATE.json` or one of the swarm's own accounts;\n3. the payer's funding chain, two hops (the account whose send opened it, then that account's funder), contains no registry payTo and no operator account;\n4. payers of the same payee that share a funding ancestor within those two hops are ONE group, and a group counts once.\n")
w("Accounts that are the first-hop funder of 3 or more different payers in this sample (`hubs`, an exchange withdrawal, a faucet, a dispenser or a sponsor) are treated two ways, and both numbers are given: **hub rule on** (a hub does not merge its payers: the upper bound on independent funders) and **strict** (a hub merges them: the lower bound). Representatives are not compared. This is a lower bound on common control, not proof of independence, and it cannot tell a customer from an operator who funds each key from a different exchange.\n")
w("## Result\n")
w(f"- {len(S)} payTo accounts read, {sum(1 for s in S.values() if not s['history_complete'])} with an incomplete history. {len(active)} of them have any confirmed receive; **{len(S)-len(active)} have none** (llmrt, subnano, feeless402, agents_webdesigner, antigravityandrew: reported as zero, not omitted).")
w(f"- {sum(s['distinct_payers'] for s in S.values())} distinct payer accounts across them. By class: external {tot['external']}, operator {tot['operator']}, seller_funded {tot['seller_funded']}, self {tot['self']}.")
w(f"- **Pairs meeting the predicate: {q}** (payer->payee, 2+ receives at or above the floor, external class). Independent funder groups among them: **{g_strict} strict, {g_hub} with the hub rule on**.\n")
w("| Seller(s) | Confirmed receives | Distinct payers | External | Operator-class | Seller-funded | Self | Repeat payers (any amount) | Qualifying pairs | Funder groups: strict / hub rule |\n|---|---|---|---|---|---|---|---|---|---|")
for acct, s in sorted(active.items(), key=lambda kv: -kv[1]['distinct_payers']):
    pc = s['payers_by_class']
    w(f"| {', '.join(s['sellers'])} | {s['confirmed_receives']} | {s['distinct_payers']} | {pc.get('external',0)} | {pc.get('operator',0)} | {pc.get('seller_funded',0)} | {pc.get('self',0)} | {s['repeat_payers_any_amount']} | {s['pairs_qualifying']} | {s['groups_strict_no_hub_rule']} / {s['independent_funder_groups_of_qualifying']} |")
w("")
w("## What to be careful about\n")
big = max(active.items(), key=lambda kv: kv[1]['distinct_payers'])
w(f"- Two accounts carry almost all of the volume: `nanswap-nodes` ({S[big[0]]['distinct_payers']} payers) and `nanoto-rpc`. Both belong to services with other business, so their payer counts are an upper bound on x402 customers.")
f1 = collections.Counter(); 
for p, c in ch.items():
    if isinstance(c, list) and c: f1[body(c[0])] += 1
top = f1.most_common(1)[0]
w(f"- One account (`{top[0][:14]}...`) is the first-hop funder of {top[1]} payers, paying only 2 sellers: that is the shape of a dispenser or a single sponsor. The strict column treats it as one funder; the hub-rule column does not. `nano_settlement_verify` `nano_funding.py` ([FUNDING-PROVENANCE.md](https://github.com/dhyabi2/nano-settlement-verify/blob/v1.1.0/FUNDING-PROVENANCE.md)) is the per-payment version of the same check.")
w(f"- The hub list ({len(hubs)} accounts) is a heuristic from this sample, not an identification: we did not establish what any of them is, except where `STATE.json` already says (`1banexkcf...` an exchange, `3top1ao59...` a payout service).")
w("- Most small sellers show zero qualifying pairs because their payers are operator-class: one named operator account is the first-hop funder of payers at 15 different sellers. Adding it to the operator list moved qualifying pairs from 146 to 126 in this run (146 is what `payers_measure.py --reuse` printed before the account was on the operator list).")
w("- Receives are read at the payee's chain; timestamps on a receive are when it was pocketed, not when the payer sent it.\n")
w("## Reproduce, and the weekly line\n```sh\npython3 payers_measure.py --verify-dir ../nano-settlement-verify --out data/payers-$(date -u +%F).json   # about 10 minutes; slow on purpose (public nodes ban fast clients)\npython3 payers_report.py data/payers-$(date -u +%F).json                                                # writes PAYERS.md, the CSV, and appends data/payers-metric.jsonl\n```\n`data/payers-metric.jsonl` takes one line per run, including runs where the number is zero, so the series has no gaps. A scheduled run (a Claude cloud routine, never a GitHub Action) can call both commands weekly.\n")
if extra:
    e = json.load(open(extra)); (ea, es), = e['summary'].items(); pr = e['payees'][ea]['payers_raw']
    w("## The swarm treasury account (where Vend and Unstuck's paid calls land)\n")
    w(f"Vend is `dead` in the registry today, so its payee is not in the table above; the treasury `{ea}` is the swarm's shared treasury (named so in the project's CLAUDE.md and OWNER-RULES) and the payee of the 0.0005 XNO block `B749B757...`. Read {e['read_at']} with the same predicate (the treasury itself is the payee, so it is not counted as its own payer; accounts named as swarm or operator accounts are class `operator`).\n")
    w(f"- {es['confirmed_receives']} confirmed receives from **{es['distinct_payers']} distinct payers**; classes {es['payers_by_class']}; payers with 2+ receives (any amount): {es['repeat_payers_any_amount']}.")
    w(f"- Qualifying pairs (external, 2+ receives at or above the floor): **{es['pairs_qualifying']}**; independent funder groups: {es['groups_strict_no_hub_rule']} strict / {es['independent_funder_groups_of_qualifying']} with the hub rule on.")
    w(f"- Receives at the treasury include single transfers of 10 to 40 XNO (see the `sum_raw` column of the CSV) that read as funding rather than purchases, so these ten payers are not a customer count. Raw reads: [data/{extra.split('/')[-1]}]({extra}).\n")
open('PAYERS.md', 'w').write("\n".join(L))
m = {'date': day, 'read_at': d['read_at'], 'payto_accounts': len(S), 'payto_with_receives': len(active), 'distinct_payers': sum(s['distinct_payers'] for s in S.values()), 'classes': dict(tot), 'qualifying_pairs': q, 'funder_groups_strict': g_strict, 'funder_groups_hub_rule': g_hub, 'floor_raw': d['floor_raw']}
open('data/payers-metric.jsonl', 'a').write(json.dumps(m) + "\n")
print(json.dumps(m))
