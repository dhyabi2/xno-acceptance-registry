#!/usr/bin/env python3
"""Probe facilitators (GET /supported) and catalogs with one unauthenticated GET each; record whether
nano:mainnet / nano appears. Pays nothing. stdlib only. Excludes x402-foundation-run services."""
import datetime, json, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

FACILITATORS = [
 ("PayAI", "https://facilitator.payai.network/supported"),
 ("Coinbase CDP", "https://api.cdp.coinbase.com/platform/v2/x402/supported"),
 ("x402.rs", "https://facilitator.x402.rs/supported"),
 ("Dexter", "https://x402.dexter.cash/supported"),
 ("Mogami", "https://facilitator.mogami.tech/supported"),
 ("OpenX402", "https://facilitator.openx402.ai/supported"),
 ("Ultravioleta DAO", "https://facilitator.ultravioletadao.xyz/supported"),
 ("Daydreams", "https://facilitator.daydreams.systems/supported"),
 ("Polygon", "https://x402.polygon.technology/supported"),
 ("thirdweb", "https://api.thirdweb.com/v1/payments/x402/supported"),
 ("Corbits", "https://facilitator.corbits.dev/supported"),
 ("Heurist", "https://x402.gateway.heurist.ai/supported"),
]
CATALOGS = [
 ("Coinbase x402 Bazaar (CDP discovery, first 1000 of ~70k; full count: scan_bazaar.py)", "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=1000"),
 ("x402scan", "https://www.x402scan.com/"),
 ("pursekeeper.dev", "https://pursekeeper.dev/sellers.json"),
 ("x402 Bazaar (x402.org docs)", "https://docs.cdp.coinbase.com/x402/bazaar"),
 ("agentic.market", "https://agentic.market/"),
 ("402index.io", "https://402index.io/"),
]
# excluded on purpose (owner): x402-foundation repos and the foundation-run x402.org facilitator

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "xno-listing-tracker/0.1"})
    try:
        r = urllib.request.urlopen(req, timeout=20); return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200000).decode("utf-8", "replace")
    except Exception as e:
        return None, type(e).__name__

def row(kind, item):
    name, url = item
    st, body = get(url)
    out = {"kind": kind, "name": name, "url": url, "http": st}
    if st is None:
        out["result"] = "unreachable (%s)" % body; return out
    nets = []
    try:
        j = json.loads(body)
        for k in j.get("kinds", []) if isinstance(j, dict) else []:
            nets.append(k.get("network"))
        out["networks"] = sorted({n for n in nets if n})
        out["items"] = len(j.get("items", [])) if isinstance(j, dict) and "items" in j else None
    except Exception:
        pass
    low = body.lower()
    low = re.sub(r"nano[ -]banana", "", low)  # an image model, not the currency
    out["mentions_nano"] = bool(re.search(r"\bnano\b|nano:mainnet|nano-mainnet|\bxno\b", low))
    if kind == "facilitator":
        if st == 200 and out.get("networks") is not None:
            out["result"] = "lists nano:mainnet" if any("nano" in n.lower() for n in out["networks"]) else "supports %d networks, no nano" % len(out["networks"])
        elif st in (401, 403):
            out["result"] = "needs credentials; /supported not readable"
        else:
            out["result"] = "no /supported answer (HTTP %s)" % st
    else:
        out["result"] = "mentions nano/xno" if out["mentions_nano"] else "no nano found in the page/feed"
    return out

if __name__ == "__main__":
    jobs = [("facilitator", f) for f in FACILITATORS] + [("catalog", c) for c in CATALOGS]
    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(lambda j: row(*j), jobs))
    doc = {"probed_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%MZ"), "rows": rows}
    json.dump(doc, open(sys.argv[1] if len(sys.argv) > 1 else "listing-status.json", "w"), indent=1)
    for r in rows: print(r["kind"], r["name"], r["http"], r["result"])
