#!/usr/bin/env python3
"""Rebuild README.md from listing-status.json (probe_listing.py) and bazaar-scan.json (scan_bazaar.py). Rebuild, never append."""
import json
st = json.load(open("listing-status.json")); bz = json.load(open("bazaar-scan.json"))
nano_res = [x for x in bz["nano_resources"] if x["network_is_nano"]]
sellers = sorted({x["payTo"] for x in nano_res})
hosts = sorted({x["resource"].split("/")[2] for x in nano_res})
L = ["# Which x402 facilitators and catalogs can list nano:mainnet",
     "", "Probed %s by `probe_listing.py` (one unauthenticated GET each, nothing paid) and `scan_bazaar.py`. Excluded on purpose: the x402-foundation repos and the foundation-run x402.org facilitator." % st["probed_at"], "",
     "## Facilitators (GET /supported)", "", "| facilitator | HTTP | result |", "|---|---|---|"]
for r in st["rows"]:
    if r["kind"] == "facilitator":
        L.append("| %s | %s | %s |" % (r["name"], r["http"] or "-", r["result"]))
L += ["", "No facilitator that publishes /supported lists a Nano network. Two need credentials (unknown, not 'no'); two did not answer.",
      "A Nano seller does not need a facilitator: it can verify the block itself (https://github.com/dhyabi2/dual-rail, https://github.com/dhyabi2/nano-settlement-verify).", "",
      "## Catalogs", "", "| catalog | HTTP | result |", "|---|---|---|"]
for r in st["rows"]:
    if r["kind"] == "catalog":
        res = r["result"]
        if "no nano found" in res and "Bazaar" not in r["name"]:
            res += " (home page only; if it is rendered by script, this says little)"
        L.append("| %s | %s | %s |" % (r["name"], r["http"] or "-", res))
L += ["", "## Coinbase x402 Bazaar, full scan",
      "", "%d of %d discovery resources read; %d distinct networks. **%d resources declare `nano:mainnet`** from %d payTo address(es) on %d host(s): %s." % (
          bz["scanned"], bz["total_reported"], len(bz["networks"]), len(nano_res), len(sellers), len(hosts), ", ".join(hosts)),
      "So the Bazaar can list nano:mainnet entries today: it also lists xrpl, stellar, algorand, stacks, hyperliquid and others. What we have not established is the route by which that seller got in (which facilitator or crawler), or whether the listing is searchable by network. That is the question to ask.",
      "", "## Asks (drafts, not sent)", "See `claude/drafts/facilitator-catalog-asks-2026-11-02.md` in dhyabi2/swarm-decisions. Answers are recorded below when they arrive.", "",
      "| who | asked | answer |", "|---|---|---|"]
for w in ("Coinbase CDP Bazaar", "PayAI", "x402.rs", "Dexter", "Ultravioleta DAO", "x402scan"):
    L.append("| %s | not yet | - |" % w)
L += ["", "Rebuild: `python3 probe_listing.py listing-status.json && python3 scan_bazaar.py bazaar-scan.json && python3 build_table.py`.", ""]
open("README.md", "w").write("\n".join(L))
print("\n".join(L[:12]))
