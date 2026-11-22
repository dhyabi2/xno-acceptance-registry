"""Which installable Nano buyer client can pay a seller's 402, read from the 402 alone.

B17 / B18 (CAMPAIGN.md), spec `specs/agent-tool-registry-dialect.md`, expert GUIDE 2026-11-21T05Z.

Pure functions, no network. Input is one unpaid 402 as the seller sent it (its headers and its body);
output is one dialect and one verdict per client in `clients.json`:

    dialect_of(parsed)        -> "exact" | "send-hash" | "invoice" | "UNKNOWN"
    client_fit(accept, client, where) -> "yes" | "no:<first field that fails>"
    verdicts(headers, body, clients)  -> {"dialect": ..., "where": ..., "x402Version": ...,
                                          "accepts": [...], "payable_by": {client: verdict}}

The verdict order is fixed, so `no:<field>` always names the FIRST thing that fails:
where, version, resource (whole quote, only for a client row with `versions`), then per accept: scheme, network,
where, asset, amount_key, payTo, amount_ambiguous, cap, extra.

Optional client keys (strategist 2026-11-21 16:5xZ, for x402-dotnet-client; a row without them is
checked exactly as before): `versions` (the x402Version values it parses), `needs_resource` (the quote
must carry a `resource` key), `asset` (required asset, case-insensitive), `amount_key` (the accept key
the amount must arrive under). `cap_raw` null means the cap is the host's own allowance: only a
positive integer amount is checked.

    "UNKNOWN"   - the 402 carried no parsable terms (an undecodable header, a body that is not JSON).
    "no:scheme" - the terms are readable and speak another dialect (send-hash: pay first, then present
                  the block hash in X-Nano-Payment). Neither client sends that.
    "no:invoice"- a private invoice flow (POST an invoice, pay an exact amount with a random suffix).

`extra` is needed by no listed client today. @x402nano/exact 1.1.0's client/index.js:67 reads
`paymentRequirements?.extra.workOptional`, a TypeError when a quote has no `extra` (lane 3 05:4xZ), but
kilkelly 1.1.0 depends on @x402nano/exact ^0.1.1 = 0.1.1, whose client reads only payTo and amount
(PR agent run 434: package.json, package-lock.json:92-95, npm deps). `no:extra` stays for a client
row with needs_extra true.

Usage: python3 claude/tools/client_fit.py FIXTURES.json   (a list of {"id", "headers", "body"})
"""
import base64
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER_NAMES = ("PAYMENT-REQUIRED", "X-PAYMENT-REQUIRED")
ALPHABET = "13456789abcdefghijkmnopqrstuwxyz"


def load_clients(path=None, include_pending=False):
    """Clients that install today. A client with a `pending` key (a fix on a branch, not merged or
    released) is left out unless include_pending is True, so a count never credits unmerged code."""
    with open(path or os.path.join(HERE, "clients.json")) as f:
        data = json.load(f)
    return {k: v for k, v in data.items()
            if not k.startswith("_") and (include_pending or "pending" not in v)}


def nano_checksum_ok(address):
    """True when a nano_/xrb_ address's 8-char checksum is blake2b-40 of its key (reversed)."""
    if not isinstance(address, str):
        return False
    for prefix in ("nano_", "xrb_"):
        if address.startswith(prefix):
            rest = address[len(prefix):]
            break
    else:
        return False
    if len(rest) != 60 or any(c not in ALPHABET for c in rest):
        return False
    bits = "".join(format(ALPHABET.index(c), "05b") for c in rest)
    key_bits, check_bits = bits[4:260], bits[260:]
    if bits[:4] != "0000":
        return False
    key = int(key_bits, 2).to_bytes(32, "big")
    check = int(check_bits, 2).to_bytes(5, "big")
    return hashlib.blake2b(key, digest_size=5).digest()[::-1] == check


def _header(headers, name):
    for k, v in (headers or {}).items():
        if k.lower() == name.lower():
            return v
    return None


def _json(text):
    if isinstance(text, (dict, list)):
        return text
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except (TypeError, ValueError, RecursionError):  # RecursionError: deeply nested body
        return None


def _norm_accept(a):
    amount, mar = a.get("amount"), a.get("maxAmountRequired")
    if amount is not None and mar is not None and str(amount) != str(mar):
        amount_raw = None
        ambiguous = True
    else:
        amount_raw = str(amount if amount is not None else mar) if (amount is not None or mar is not None) else None
        ambiguous = False
    pay_to = a.get("payTo")
    return {
        "scheme": a.get("scheme"),
        "network": a.get("network"),
        "asset": a.get("asset"),
        "amount_raw": amount_raw,
        "amount_ambiguous": ambiguous,
        "payTo": pay_to,
        "payTo_checksum_valid": nano_checksum_ok(pay_to),
        "has_extra": isinstance(a.get("extra"), dict),
        "keys": sorted(k for k in a if isinstance(k, str)),
    }


def parse_402(headers, body):
    """Where the terms are, their version, and the normalised accepts list. Never raises."""
    out = {"where": None, "x402Version": None, "accepts": [], "parsed": False, "body_json": None,
           "has_resource": False}
    for name in HEADER_NAMES:
        raw = _header(headers, name)
        if raw is None:
            continue
        out["where"] = "header:" + name
        try:
            # a saved capture can hold a number or a list as a header value: undecodable, not a crash
            # (PR agent run 438, conformance.py review)
            doc = json.loads(base64.b64decode(raw.strip(), validate=True).decode("utf-8")) \
                if isinstance(raw, str) else None
        except (ValueError, UnicodeDecodeError, TypeError, RecursionError):
            doc = None
        if isinstance(doc, dict) and isinstance(doc.get("accepts"), list):
            out["x402Version"] = doc.get("x402Version")
            out["accepts"] = [_norm_accept(a) for a in doc["accepts"] if isinstance(a, dict)]
            out["parsed"] = True
            out["has_resource"] = "resource" in doc
        out["body_json"] = _json(body)
        return out
    doc = _json(body)
    out["body_json"] = doc
    if body is not None and body != "":
        out["where"] = "body"
    if isinstance(doc, dict) and isinstance(doc.get("accepts"), list):
        out["x402Version"] = doc.get("x402Version")
        out["accepts"] = [_norm_accept(a) for a in doc["accepts"] if isinstance(a, dict)]
        out["parsed"] = True
        out["has_resource"] = "resource" in doc
    return out


def _text(doc):
    return json.dumps(doc).lower() if doc is not None else ""


def dialect_of(parsed):
    if any(a.get("scheme") == "exact" for a in parsed["accepts"]):
        return "exact"
    t = _text(parsed.get("body_json"))
    if not t:
        return "UNKNOWN"
    if "invoice" in t:
        return "invoice"
    if "x-nano-payment" in t or "nano-send-hash" in t or "send hash" in t or "send_hash" in t:
        return "send-hash"
    if parsed["accepts"]:
        return "other"
    return "UNKNOWN"


def network_ok(accept, client):
    """The client's own network rule. A row with `network_rule` "nano-prefix" keeps any accept whose
    network starts with "nano" or whose asset is xno or nano, case-insensitive (nano-pay:
    Feeless402/feeless402@fab7f69 nano_pay/x402.py:250-257 pick_nano_offer; PR agent run 439,
    GUIDE 19Z). Any other row needs the exact `network` string."""
    if client.get("network_rule") == "nano-prefix":
        net, asset = accept.get("network"), accept.get("asset")
        net = str(net).lower() if net is not None else ""
        asset = str(asset).lower() if asset is not None else ""
        return net.startswith("nano") or asset in ("xno", "nano")
    return accept.get("network") == client["network"]


def client_fit(accept, client, where):
    if accept.get("scheme") != client["scheme"]:
        return "no:scheme"
    if not network_ok(accept, client):
        return "no:network"
    if where not in client["where"]:
        return "no:where"
    if client.get("asset") is not None and \
            str(accept.get("asset") or "").lower() != str(client["asset"]).lower():
        return "no:asset"
    if client.get("amount_key") is not None and client["amount_key"] not in (accept.get("keys") or []):
        return "no:amount_key"
    if not accept.get("payTo_checksum_valid"):
        return "no:payTo"
    if accept.get("amount_ambiguous"):
        return "no:amount_ambiguous"
    amt = accept.get("amount_raw")
    # ASCII digits only: str.isdigit() accepts '²', which int() then rejects with ValueError, and
    # a 0 raw quote is no send at all (PR agent run 432, the same fix as buyer_plan in run 431)
    cap = client.get("cap_raw")
    if amt is None or not re.fullmatch(r"[0-9]+", str(amt)) or int(amt) == 0 \
            or (cap is not None and int(amt) > int(cap)):
        return "no:cap"
    if client.get("needs_extra") and not accept.get("has_extra"):
        return "no:extra"
    return "yes"


def verdicts(headers, body, clients=None):
    clients = clients if clients is not None else load_clients()
    p = parse_402(headers, body)
    d = dialect_of(p)
    payable = {}
    for name, c in clients.items():
        if not p["parsed"] or not p["accepts"]:
            payable[name] = {"send-hash": "no:scheme", "invoice": "no:invoice"}.get(d, "UNKNOWN")
            continue
        if c.get("versions") is not None and p["where"] not in c["where"]:
            payable[name] = "no:where"  # it never reads that place, so nothing else there matters
            continue
        if c.get("versions") is not None and p["x402Version"] not in c["versions"]:
            payable[name] = "no:version"
            continue
        if c.get("needs_resource") and not p["has_resource"]:
            payable[name] = "no:resource"
            continue
        fits = [client_fit(a, c, p["where"]) for a in p["accepts"]]
        payable[name] = "yes" if "yes" in fits else fits[0]
    return {"dialect": d, "where": p["where"], "x402Version": p["x402Version"],
            "accepts": p["accepts"], "payable_by": payable}


def count_payable(rows):
    """{client: number of rows whose verdict is yes} - the spec's counts.payable_by."""
    out = {}
    for r in rows:
        for c, v in (r.get("payable_by") or {}).items():
            out[c] = out.get(c, 0) + (1 if v == "yes" else 0)
    return out


def payto_fixed(probe_a, probe_b):
    """False when two probes of one seller name different payTo sets; None with one probe."""
    if probe_a is None or probe_b is None:
        return None
    a = sorted(x.get("payTo") or "" for x in probe_a.get("accepts", []))
    b = sorted(x.get("payTo") or "" for x in probe_b.get("accepts", []))
    return a == b


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1])
        return 2
    with open(argv[1]) as f:
        fixtures = json.load(f)
    clients = load_clients()
    rows = []
    for fx in fixtures:
        v = verdicts(fx.get("headers") or {}, fx.get("body"), clients)
        v["id"] = fx.get("id")
        rows.append(v)
        print("%-28s %-9s %-24s %s" % (v["id"], v["dialect"], v["where"],
                                        " ".join("%s=%s" % kv for kv in sorted(v["payable_by"].items()))))
    print("payable_by", json.dumps(count_payable(rows), sort_keys=True), "of", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
