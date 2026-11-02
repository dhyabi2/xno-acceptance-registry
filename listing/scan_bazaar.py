#!/usr/bin/env python3
"""Page through the public Coinbase x402 Bazaar discovery list and count resources per network; report any nano network.
Read-only, stdlib only."""
import json, sys, time, urllib.request
BASE = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
def main(max_pages=100):
    nets, seen, total, off = {}, 0, None, 0
    nano = []
    for _ in range(max_pages):
        for attempt in range(3):
            try:
                req = urllib.request.Request("%s?limit=1000&offset=%d" % (BASE, off), headers={"User-Agent": "xno-listing-tracker/0.1"})
                d = json.load(urllib.request.urlopen(req, timeout=60)); break
            except Exception:
                time.sleep(2); d = None
        if d is None: break
        total = d["pagination"]["total"]
        for i in d["items"]:
            seen += 1
            for a in i.get("accepts", []):
                n = str(a.get("network")); nets[n] = nets.get(n, 0) + 1
                if "nano" in n.lower() or "nano_" in json.dumps(a).lower():
                    nano.append({"resource": i["resource"], "network": n, "payTo": a.get("payTo"), "network_is_nano": "nano" in n.lower()})
        off += 1000
        if off >= total: break
    return {"total_reported": total, "scanned": seen, "networks": dict(sorted(nets.items(), key=lambda kv: -kv[1])), "nano_resources": nano}
if __name__ == "__main__":
    r = main(); json.dump(r, open(sys.argv[1], "w"), indent=1)
    print(r["total_reported"], r["scanned"], len(r["networks"]), "networks;", len(r["nano_resources"]), "nano resources")
