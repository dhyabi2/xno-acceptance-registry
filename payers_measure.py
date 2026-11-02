#!/usr/bin/env python3
"""Distinct payers and independently-funded repeat payer->payee pairs for the registry's payTo accounts.

Read-only: account_history, account_info, block_info on public Nano nodes. No key, no send.

    python3 payers_measure.py --verify-dir ../nano-settlement-verify --out data/payers-YYYY-MM-DD.json

Independence predicate (written down so a reader can disagree with a clause, not with a number):
  A payer->payee pair COUNTS when
   1. the payee made at least 2 confirmed receives from that payer, each >= FLOOR_RAW (dust is not demand);
   2. the payer is not the payee, not another registry payTo, and is not an operator account
      (OPERATOR_ACCOUNTS: the swarm's own treasury/starter accounts);
   3. the payer's funding chain (the account whose send opened it, then that account's funder: 2 hops)
      contains neither the payee, another registry payTo, nor an operator account;
   4. no other counted payer of the same payee shares a funding ancestor within those 2 hops
      (such payers form one group; a group is one independent funder). Accounts that fund 3 or more
      different payers in this whole sample are listed as `hubs` (exchange withdrawals look like this) and do not
      merge groups; the number without that rule is reported too (`groups_strict`).
  Representatives are NOT compared (not evaluated here). A lower bound on common control, not proof of
  independence: an operator who funds each key from a different exchange withdrawal reads as several funders.
"""
import argparse, json, sys, time
from datetime import datetime, timezone

FLOOR_RAW = 10 ** 25  # 0.00001 XNO
OPERATOR_ACCOUNTS = {
    "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7",
    "nano_1434j1n4sin4cefs5njibag4tsmo596fmg3s6bdogtod3ndmdfez5yuebrh9",
    "nano_3saqoz5qfgmohfz3dg5ywwmxj7dwdp3g6xfbspt11g7gyrxgbupi1w9u4g4r",
    # named "the operator" in swarm-decisions STATE.json xno_holders.rule (a funding source whose XNO does not count as outside demand)
    "nano_1xug1q5t7nxoj3ywwzokiea9jz8fq8qfgzp8pbyfr3co3e5xgj755uofu8u",
}
NODES = ["https://node.somenano.com/proxy", "https://nanoslo.0x.no/proxy", "https://rainstorm.city/api"]  # rpc.nano.to rate-limits (429 ban) a loop like this; add it back only with a pause
PAUSE_S = 0.4


def body(a):
    return a.split("_", 1)[1][:52] if isinstance(a, str) and "_" in a else a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-dir", required=True)
    ap.add_argument("--registry", default="registry.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--payee", help="measure this one account instead of the registry (with --label)")
    ap.add_argument("--label", default="payee")
    ap.add_argument("--reuse", help="recompute classes and groups from a previous --out file; no network")
    a = ap.parse_args()
    sys.path.insert(0, a.verify_dir)
    import nano_settlement_verify as nsv

    def rpc(payload):
        last = None
        for n in NODES:
            for attempt in range(2):
                try:
                    time.sleep(PAUSE_S)
                    r = nsv.post_json(n, payload)
                    if isinstance(r, dict) and "error" in r and "not found" not in str(r["error"]).lower() \
                            and "not open" not in str(r["error"]).lower():
                        last = r
                        time.sleep(1)
                        continue
                    return r
                except Exception as e:  # noqa
                    last = {"error": str(e)}
                    time.sleep(1)
        return last

    reg = json.load(open(a.registry))
    payees = {}
    for e in reg["entries"]:
        if e.get("state_today") not in ("live_402_nano", "live_portal", "live_status_route"):
            continue
        note = (e.get("payto_note") or "").lower()
        for p in e.get("payto") or []:
            if not p.get("checksum_valid"):
                continue
            if "per-payment" in note or "deposit address" in note:
                continue
            payees.setdefault(p["address"], []).append(e["id"])
    if a.payee:
        payees = {a.payee: [a.label]}
    registry_keys = {body(x) for x in payees}
    op_keys = {body(x) for x in OPERATOR_ACCOUNTS}

    if a.reuse:
        result = json.load(open(a.reuse)); chains = result["chains"]
    else:
        result = {"read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "floor_raw": str(FLOOR_RAW),
                  "nodes": NODES, "payees": {}}
        for acct, ids in payees.items():
            recv, head, pages, complete = [], None, 0, True
            while True:
                pl = {"action": "account_history", "account": acct, "count": "500"}
                if head:
                    pl["head"] = head
                r = rpc(pl)
                if not isinstance(r, dict) or "history" not in r:
                    if isinstance(r, dict) and "not found" in str(r.get("error", "")).lower():
                        break
                    complete = False
                    break
                h = r["history"]
                if not isinstance(h, list):
                    break
                for b in h:
                    if b.get("type") == "receive":
                        recv.append(b)
                pages += 1
                nxt = r.get("previous")
                if not nxt or not h or pages >= a.max_pages:
                    if nxt:
                        complete = False
                    break
                head = nxt
            by = {}
            unconfirmed = 0
            for b in recv:
                if b.get("confirmed") not in ("true", True, None):
                    unconfirmed += 1
                    continue
                amt = int(b["amount"])
                by.setdefault(b["account"], []).append((int(b.get("local_timestamp") or 0), amt))
            result["payees"][acct] = {"sellers": ids, "receives": len(recv), "unconfirmed": unconfirmed,
                                      "complete": complete, "payers_raw": {
                p: {"n": len(v), "n_above_floor": sum(1 for _, x in v if x >= FLOOR_RAW),
                    "sum_raw": str(sum(x for _, x in v)), "first": min(t for t, _ in v), "last": max(t for t, _ in v)}
                for p, v in by.items()}}
            print(acct[:20], ids, "receives", len(recv), "payers", len(by), "complete", complete, file=sys.stderr)

        # funding chains for every distinct payer (2 hops). An RPC error is never read as "unopened":
        # only the node's own "Account not found" is; anything else is retried across nodes and, failing that, recorded as unreadable.
        funder_cache = {}

        def funder(acct):
            """(funder or None, status) status in ok|unopened|unreadable"""
            if acct in funder_cache:
                return funder_cache[acct]
            out = ("unreadable", None)
            info = rpc({"action": "account_info", "account": acct})
            if isinstance(info, dict) and "open_block" in info:
                ob = rpc({"action": "block_info", "json_block": "true", "hash": info["open_block"]})
                c = ob.get("contents") if isinstance(ob, dict) else None
                src = (c or {}).get("link") or (c or {}).get("source") if isinstance(c, dict) else None
                if src:
                    sb = rpc({"action": "block_info", "json_block": "true", "hash": src})
                    f = sb.get("block_account") if isinstance(sb, dict) else None
                    if f:
                        out = ("ok", f)
            elif isinstance(info, dict) and "not found" in str(info.get("error", "")).lower():
                out = ("unopened", None)
            funder_cache[acct] = out
            return out

        chains = {}
        allp = {p for d in result["payees"].values() for p in d["payers_raw"]}
        for i, p in enumerate(sorted(allp)):
            st, f1 = funder(p)
            if st != "ok":
                chains[p] = None if st == "unopened" else "unreadable"
            else:
                ch = [f1]
                st2, f2 = funder(f1)
                if st2 == "ok" and body(f2) not in (body(p), body(f1)):
                    ch.append(f2)
                chains[p] = ch
            if i % 20 == 0:
                print("chains", i, len(allp), file=sys.stderr)
        result["chains"] = chains
    # hubs: a funder appearing as first-hop funder of >=3 distinct payers across the sample
    cnt = {}
    for p, c in chains.items():
        if isinstance(c, list) and c:
            cnt.setdefault(body(c[0]), set()).add(p)
    hubs = {f for f, s in cnt.items() if len(s) >= 3}
    result["hubs"] = sorted(hubs)

    summary = {}
    for acct, d in result["payees"].items():
        rows = []
        for p, v in d["payers_raw"].items():
            k = body(p)
            ch = chains.get(p)
            c_keys = [body(x) for x in (ch if isinstance(ch, list) else [])]
            if k == body(acct):
                cls = "self"
            elif k in registry_keys:
                cls = "registry_seller"
            elif k in op_keys or any(x in op_keys for x in c_keys):
                cls = "operator"
            elif body(acct) in c_keys or any(x in registry_keys for x in c_keys):
                cls = "seller_funded"
            elif ch == "unreadable" or ch is None:
                cls = "unreadable" if ch == "unreadable" else "unopened"
            else:
                cls = "external"
            rows.append((p, v, cls, c_keys))
        ext = [r for r in rows if r[2] == "external"]
        qual = [r for r in ext if r[1]["n_above_floor"] >= 2]

        def groups(items, use_hubs):
            parent = {r[0]: r[0] for r in items}

            def root(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            owner = {}
            for r in items:
                for anc in [body(r[0])] + r[3]:
                    if use_hubs and anc in hubs:
                        break
                    if anc in owner:
                        parent[root(r[0])] = root(owner[anc])
                    else:
                        owner[anc] = r[0]
            return len({root(r[0]) for r in items})
        cls_count = {}
        for r in rows:
            cls_count[r[2]] = cls_count.get(r[2], 0) + 1
        summary[acct] = {
            "sellers": d["sellers"], "history_complete": d["complete"],
            "confirmed_receives": d["receives"] - d["unconfirmed"],
            "distinct_payers": len(rows),
            "payers_by_class": cls_count,
            "repeat_payers_any_amount": sum(1 for r in rows if r[1]["n"] >= 2),
            "pairs_qualifying": len(qual),
            "independent_funder_groups_of_qualifying": groups(qual, True) if qual else 0,
            "groups_strict_no_hub_rule": groups(qual, False) if qual else 0,
            "distinct_external_payers": len(ext),
            "independent_funder_groups_of_external": groups(ext, True) if ext else 0,
            "qualifying_payers": [r[0] for r in qual],
        }
    result["summary"] = summary
    json.dump(result, open(a.out, "w"), indent=1)
    print(json.dumps({k: {x: y for x, y in v.items() if x != 'qualifying_payers'} for k, v in summary.items()}, indent=0)[:6000])


if __name__ == "__main__":
    main()
