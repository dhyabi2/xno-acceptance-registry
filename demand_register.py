#!/usr/bin/env python3
"""demand_register.py - the Nano demand register: who outside this project asked to pay in XNO at which seller.

A seller that says "we will add a Nano rail when there is demand" (Flux / APEX did) deserves a number to look at, and
the number must not be ours. Rules, enforced by `validate`:
  * a request needs: requester, host, a verbatim quote, and the public conversation file it came from;
  * the quote must appear in that file (checked against a local clone with --local DIR, else fetched from raw GitHub);
  * the project's own accounts do not count, and one requester counts once per host;
  * nothing is seeded: with no requests the page says 0.

    python3 demand_register.py validate [--local DIR]   # exit 1 on any problem
    python3 demand_register.py render                   # DEMAND-REGISTER.md to stdout
    python3 demand_register.py gate HOST                # exit 0 only when HOST has >= threshold distinct requesters
"""
import argparse, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWN = {"unstuck", "dhyabi2", "nanoswarm", "rai", "vend", "estuary", "grove"}


def load(path=None):
    with open(path or os.path.join(HERE, "demand", "register.json"), encoding="utf-8") as f:
        return json.load(f)


def conversation_text(reg, name, local=None):
    if local:
        p = os.path.join(local, name)
        if not os.path.exists(p):
            p = os.path.join(local, name.lower())
        with open(p, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(reg["conversations_base"] + name, headers={"User-Agent": "demand-register/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def quote_in(text, quote):
    """Verbatim, after JSON decoding (the files store text as JSON strings)."""
    try:
        d = json.loads(text)
        hay = json.dumps(d, ensure_ascii=False)
        hay = "\n".join(e.get("text", "") for e in d.get("exchange", [])) + "\n" + hay
    except ValueError:
        hay = text
    return quote in hay


def validate(reg, local=None, fetch=conversation_text):
    problems = []
    for i, r in enumerate(reg.get("requests", [])):
        for k in ("requester", "host", "quote", "conversation"):
            if not r.get(k):
                problems.append("request %d: missing %s" % (i, k))
        if r.get("requester", "").lower() in OWN:
            problems.append("request %d: %s is one of our own accounts" % (i, r["requester"]))
    items = [("request %d" % i, r) for i, r in enumerate(reg.get("requests", []))]
    items += [("gate %s" % g.get("host"), g) for g in reg.get("gates", [])]
    cache = {}
    for label, r in items:
        if not r.get("conversation") or not r.get("quote"):
            continue
        try:
            t = cache.setdefault(r["conversation"], fetch(reg, r["conversation"], local))
        except Exception as e:  # noqa
            problems.append("%s: cannot read %s (%s)" % (label, r["conversation"], str(e)[:60]))
            continue
        for qk in ("quote", "stated_proof_quote"):
            if r.get(qk) and not quote_in(t, r[qk]):
                problems.append("%s: %s not found verbatim in %s" % (label, qk, r["conversation"]))
    return problems


def counts(reg):
    per = {}
    for r in reg.get("requests", []):
        if r.get("requester", "").lower() in OWN:
            continue
        per.setdefault(r["host"].lower(), set()).add(r["requester"].lower())
    return {h: len(s) for h, s in per.items()}


def render(reg):
    c = counts(reg)
    th = reg.get("threshold", 3)
    out = ["# Nano demand register", "",
           "Outside parties who said, in their own words, that they want to pay or be paid in XNO at a named seller. Counted once per seller, "
           "own accounts excluded, every quote checked verbatim against the public conversation. Nothing is seeded. "
           "Count today: **%d** distinct requesters across **%d** sellers." % (sum(c.values()), len(c)), ""]
    if reg.get("requests"):
        out += ["| Seller host | Requester | Quote | Source |", "|---|---|---|---|"]
        for r in reg["requests"]:
            out.append("| %s | %s | %s | [conversation](https://github.com/dhyabi2/agent-conversations/blob/main/conversations/%s) |"
                       % (r["host"], r["requester"], r["quote"].replace("|", "/"), r["conversation"]))
        out.append("")
    else:
        out += ["(no requests yet)", ""]
    out += ["## Sellers waiting for demand", ""]
    for g in reg.get("gates", []):
        n = c.get(g["host"].lower(), 0)
        out += ["### %s (`%s`)" % (g["seller"], g["host"]), "",
                "- Said: \"%s\"" % g["quote"],
                "- Their stated proof: \"%s\"" % g["stated_proof"],
                "- Requests logged for this host: **%d of %d**. Ask again when: %s." % (n, th, g["ask_again_when"]),
                "- Source: [%s](https://github.com/dhyabi2/agent-conversations/blob/main/conversations/%s)" % (g["conversation"], g["conversation"]),
                "- %s" % g["note"], ""]
    out += ["Add a request: open an issue on this repository with the seller URL and your own words (see WANTED-IN-XNO.md); "
            "an entry here needs your quote to exist in a public conversation, so say it where it can be linked.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["validate", "render", "gate"])
    ap.add_argument("host", nargs="?")
    ap.add_argument("--local")
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    reg = load(a.file)
    if a.cmd == "validate":
        p = validate(reg, a.local)
        for x in p:
            print("PROBLEM", x)
        print("# demand-register %s (%d requests, %d gates)" % ("ok" if not p else "INVALID", len(reg.get("requests", [])), len(reg.get("gates", []))))
        return 1 if p else 0
    if a.cmd == "render":
        sys.stdout.write(render(reg))
        return 0
    n = counts(reg).get((a.host or "").lower(), 0)
    th = reg.get("threshold", 3)
    print("# gate %s: %d of %d distinct requesters -> %s" % (a.host, n, th, "ASK" if n >= th else "WAIT"))
    return 0 if n >= th else 1


if __name__ == "__main__":
    sys.exit(main())
