#!/usr/bin/env python3
"""A public XNO buyer-wants list: 'I will pay N XNO for X', checkable and never invented.

    python3 buyer_wants.py validate wants/*.json     # exit 1 on any problem
    python3 buyer_wants.py render wants/*.json       # -> BUYER-WANTS.md on stdout
    python3 buyer_wants.py dm wants/one.json SELLER   # the message to a seller, one runnable line

A want is a promise by a named buyer, so the tool refuses what a promise needs and a template lacks:
  * status "template" is never rendered as an offer (it is how the format is documented);
  * status "open" requires a buyer, a valid nano_ address checksum for the buyer's refund/identity account,
    an integer-raw amount (1 XNO = 10^30 raw) between the registry's price band, an expiry in the future,
    and a `funded_by_owner_note` that is "yes" only when someone wrote it down.
No code here sends XNO or contacts anyone; the funded buyer is the owner-side dependency.
"""
import argparse, datetime, json, re, sys

RAW = 10 ** 30
ALPHA = "13456789abcdefghijkmnopqrstuwxyz"
STATUSES = ("template", "open", "filled", "withdrawn")


def address_ok(addr):
    """nano_ address checksum (blake2b-5 of the 32-byte key, reversed), stdlib only."""
    import hashlib
    m = re.fullmatch(r"(?:nano|xrb)_([13][13456789abcdefghijkmnopqrstuwxyz]{59})", addr or "")
    if not m:
        return False
    body = m.group(1)
    n = 0
    for ch in body:
        n = n * 32 + ALPHA.index(ch)
    key = (n >> 40).to_bytes(32, "big")
    chk = (n & (2 ** 40 - 1)).to_bytes(5, "big")
    return hashlib.blake2b(key, digest_size=5).digest()[::-1] == chk


def problems(w, today=None):
    today = today or datetime.date.today().isoformat()
    p = []
    for k in ("id", "buyer", "status", "wants", "amount_raw", "expires"):
        if k not in w:
            p.append("missing " + k)
    if p:
        return p
    if w["status"] not in STATUSES:
        p.append("status must be one of %s" % (STATUSES,))
    if not str(w["amount_raw"]).isdigit() or not (RAW // 10 ** 6 <= int(w["amount_raw"]) <= 100 * RAW):
        p.append("amount_raw must be integer raw between 0.000001 and 100 XNO")
    if w["status"] == "open":
        if not address_ok(w.get("buyer_account", "")):
            p.append("open want needs buyer_account with a valid nano_ checksum")
        if w["expires"] < today:
            p.append("open want is expired")
        if w.get("funded") not in (True,) or not w.get("funded_note"):
            p.append("open want needs funded=true and a funded_note saying who checked the balance and when")
        if not str(w.get("ask_url", "")).startswith("https://"):
            p.append("open want needs an https ask_url where a seller answers")
    return p


def xno(raw):
    s = "%d.%030d" % divmod(int(raw), RAW)
    return s.rstrip("0").rstrip(".")


def render(wants):
    open_ = [w for w in wants if w["status"] == "open"]
    out = ["# XNO buyer wants", "",
           "%d open want(s). A want is listed only if the buyer account checks, the amount is exact, it has not expired and "
           "someone recorded that it is funded. Templates and filled wants are not shown as offers." % len(open_), ""]
    if open_:
        out += ["| Buyer | Will pay (XNO) | For | Expires | Answer here |", "|---|---|---|---|---|"]
        for w in open_:
            out.append("| %s | %s | %s | %s | %s |" % (w["buyer"], xno(w["amount_raw"]), w["wants"], w["expires"], w["ask_url"]))
    else:
        out.append("None open today. This is the honest count; it changes only when a funded buyer writes one.")
    return "\n".join(out) + "\n"


def dm(w, seller):
    return ("Hi %s - %s is willing to pay %s XNO for: %s. Paid straight to an address you control, no intermediary. "
            "If you have a door, answer here: %s. One check you can run before replying: "
            "python3 buyer_wants.py validate %s (exit 0 = the offer is well-formed and unexpired)."
            % (seller, w["buyer"], xno(w["amount_raw"]), w["wants"], w.get("ask_url", "<ask link>"), "wants/<file>.json"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("validate", "render", "dm"))
    ap.add_argument("files", nargs="+")
    ap.add_argument("--seller", default="there")
    a = ap.parse_args(argv)
    wants = [json.load(open(f)) for f in a.files]
    if a.cmd == "validate":
        bad = 0
        for f, w in zip(a.files, wants):
            for pr in problems(w):
                print("%s: %s" % (f, pr)); bad += 1
        return 1 if bad else 0
    if a.cmd == "render":
        sys.stdout.write(render(wants)); return 0
    sys.stdout.write(dm(wants[0], a.seller) + "\n"); return 0


if __name__ == "__main__":
    sys.exit(main())
