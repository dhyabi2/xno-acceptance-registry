#!/usr/bin/env python3
"""Render WANTING-BUYERS.md from sellers-wanting-buyers.json and registry.json. Offline, deterministic."""
import json
w = json.load(open("sellers-wanting-buyers.json"))
reg = json.load(open("registry.json"))
live = sum(1 for e in reg["entries"] if e["state_today"] == "live_402_nano")
out = ["# Sellers waiting for an XNO buyer", "",
       f"{len(w['sellers'])} sellers have said, in public, that the missing piece is a buyer who wants to pay in XNO. "
       f"Separately, {live} sellers answer a live 402 with a Nano payTo today (registry.json, probed {reg['generated_at']}).", "",
       "| Seller | Sells | Pays today | XNO door | What a buyer needs |", "|---|---|---|---|---|"]
for s in w["sellers"]:
    out.append(f"| [{s['agent']}]({s['source']}) | {s['sells']} | {s['pays_today']} | {'yes' if s['xno_door'] else 'not yet'} | {s['buyer_needs']} |")
out += ["", "Nothing here funds or promises a purchase. If you are an agent or human who would really pay a seller above in XNO, "
        "say so on the seller's thread; the seller has said it will act on a real request.", "",
        "To pay a seller that already has a door, see the [feed](feeds/nano-sellers.json).", ""]
open("WANTING-BUYERS.md", "w").write("\n".join(out))
print(len(w["sellers"]))
