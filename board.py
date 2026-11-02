#!/usr/bin/env python3
"""Open board: sellers that say they take XNO and have no buyer yet, with address, price and what the ledger says today.
Reads board.json (hand-kept, every row cites where the seller said it) and optionally re-reads each address from a Nano node.
Read-only; sends nothing; contacts nobody.

    python3 board.py [--node URL]... > BOARD.md        # --node re-reads account state; without it the board prints 'not re-read'
"""
import argparse, datetime, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nanoaddr  # noqa: E402


def rpc(node, body):
    req = urllib.request.Request(node, data=json.dumps(body).encode(), headers={"content-type": "application/json", "user-agent": "xno-acceptance-registry-board"})
    return json.load(urllib.request.urlopen(req, timeout=25))


def state(addr, nodes):
    if not nodes:
        return {"read": False}
    for n in nodes:
        try:
            time.sleep(0.4)
            i = rpc(n, {"action": "account_info", "account": addr})
            if i.get("error") == "Account not found":
                return {"read": True, "node": n, "opened": False}
            if "balance" in i:
                return {"read": True, "node": n, "opened": True, "balance_xno": int(i["balance"]) / 10 ** 30, "blocks": int(i["block_count"]),
                        "modified": datetime.datetime.fromtimestamp(int(i["modified_timestamp"]), datetime.timezone.utc).strftime("%Y-%m-%d")}
        except Exception:  # noqa: BLE001
            continue
    return {"read": False}


def render(board, nodes):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    out = ["# Open board: who takes XNO and wants a buyer", "",
           f"Generated {now} by `board.py` from `board.json`. Every row quotes where the seller said it; the account column is read from a public Nano node at generation time. "
           "Nothing on this page funds, promises or arranges a purchase, and nobody listed here was contacted to be listed: each row is from the seller's own public post or a public ledger.", "",
           "**If you hold XNO and are looking for something to buy:** the 25 endpoints in [feeds/nano-sellers.json](feeds/nano-sellers.json) answer a live 402 with a Nano `payTo` today (probed, not claimed). "
           "The rows below are the other side: sellers who say they take XNO but who have had no buyer yet.", "",
           "| Seller | Sells | Price they published | Nano address | Ledger today | Said where |", "|---|---|---|---|---|---|"]
    for s in board["sellers"]:
        assert nanoaddr.is_valid(s["address"]), s["name"]
        st = state(s["address"], nodes)
        if not st["read"]:
            led = "not re-read"
        elif not st["opened"]:
            led = "never opened (no block yet)"
        else:
            led = f"{st['balance_xno']:.6g} XNO, {st['blocks']} blocks, last block {st['modified']}"
        out.append(f"| {s['name']} | {s['sells']} | {s['price']} | `{s['address']}` | {led} | {s['source']} |")
    out += ["", "## Notes", ""] + [f"- {n}" for n in board["notes"]]
    out += ["", "## Check a row yourself (no code of ours)", "",
            "```sh", "curl -s -A 'Mozilla/5.0' -H 'content-type: application/json' -d '{\"action\":\"account_info\",\"account\":\"<ADDRESS>\"}' https://rainstorm.city/api", "```",
            "`Account not found` means no block has ever been published for that address. Any node works; ask two.", "",
            "## Add or correct a row", "",
            "Open a pull request on `board.json` with the seller's own public words (a link) and the address. A seller can ask to be removed and is removed. "
            "Price is copied as the seller wrote it; where none was published the row says so rather than guessing."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.write(render(json.load(open(os.path.join(HERE, "board.json"))), a.node))
