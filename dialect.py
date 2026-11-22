"""The `dialect` key per seller row of xno-acceptance-registry, computed by client_fit.py (B17).

Spec: specs/agent-tool-registry-dialect.md. Built in this repository (strategist 2026-11-21 09:5xZ, after
PR runs 427-429 left it unbuilt), so it pushes nowhere. On 11-22 an own-repository round copies THREE files
into dhyabi2/xno-acceptance-registry unchanged: this file, ../client_fit.py and ../clients.json, then adds the
three lines in PATCH below to probe.py and build.py.

Pure functions, no network, stdlib only:

    capture(headers, body_text)        -> {"headers": {...}, "body": "..."}   what probe.py keeps of a 402
    row_dialect(probe, clients, second) -> the spec's dialect dict, or None for a non-402 / no capture
    apply(registry, probes, seconds)   -> sets entry["dialect"] and counts["payable_by"] in place
    count_payable(entries)             -> {client: rows whose verdict is "yes"}

Clients with a `pending` key in clients.json (a fix not merged or released) are never counted.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import client_fit as cf  # noqa: E402

BODY_LIMIT = 20000
ACCEPT_KEYS = ("scheme", "network", "asset", "amount_raw", "payTo", "payTo_checksum_valid")

PATCH = """
probe.py, after `txt = raw.decode(...)` and before the header loop:
    if st == 402: out['raw402'] = dialect.capture(h, txt)
build.py, after `reg['counts']['total'] = len(rows)` (probe results are `res`, in seller order):
    dialect.apply(reg, {s['id']: r for s, r in zip(sellers, res)})
both files: `import dialect` beside the other imports.
""".strip()


def load_clients(path=None):
    for p in (path, os.path.join(HERE, "clients.json")):
        if p and os.path.exists(p):
            return cf.load_clients(p)
    raise FileNotFoundError("clients.json")


def capture(headers, body_text, limit=BODY_LIMIT):
    """The part of one unpaid 402 the verdict needs: the two payment-required headers, raw, and the body."""
    keep = {}
    for k, v in (headers or {}).items():
        if k.upper() in cf.HEADER_NAMES:
            keep[k.upper()] = v
    if isinstance(body_text, bytes):
        body_text = body_text.decode("utf-8", "replace")
    return {"headers": keep, "body": (body_text or "")[:limit]}


def _cap(probe):
    if not isinstance(probe, dict) or probe.get("http_status") != 402:
        return None
    return probe.get("raw402")


def row_dialect(probe, clients=None, second=None):
    """The spec's dialect dict for one seller, from probe.py's result. None when it is not a 402."""
    cap = _cap(probe)
    if cap is None:
        return None
    clients = clients if clients is not None else load_clients()
    v = cf.verdicts(cap.get("headers") or {}, cap.get("body"), clients)
    p1 = cf.parse_402(cap.get("headers") or {}, cap.get("body"))
    cap2 = _cap(second)
    p2 = cf.parse_402(cap2.get("headers") or {}, cap2.get("body")) if cap2 is not None else None
    return {
        "where": v["where"],
        "x402Version": v["x402Version"],
        "kind": v["dialect"],
        "accepts": [{k: a.get(k) for k in ACCEPT_KEYS} for a in v["accepts"]],
        "payto_fixed": cf.payto_fixed(p1, p2),
        "payable_by": v["payable_by"],
    }


def count_payable(entries):
    return cf.count_payable([e.get("dialect") or {} for e in entries])


def apply(registry, probes, seconds=None, clients=None):
    """Set `dialect` on every entry (None when it was not probed or not a 402) and counts.payable_by."""
    clients = clients if clients is not None else load_clients()
    seconds = seconds or {}
    for e in registry.get("entries", []):
        e["dialect"] = row_dialect(probes.get(e["id"]), clients, seconds.get(e["id"]))
    counts = count_payable(registry.get("entries", []))
    registry.setdefault("counts", {})["payable_by"] = {c: counts.get(c, 0) for c in sorted(clients)}
    return registry


def probe_from_fixture(fx):
    """A fixture of client_fit_fixtures.json as probe.py would have returned it."""
    body = fx.get("body")
    text = body if isinstance(body, str) else json.dumps(body)
    return {"id": fx.get("id"), "http_status": 402, "raw402": capture(fx.get("headers") or {}, text)}


def main(argv):
    if len(argv) != 2:
        print("Usage: python3 dialect.py FIXTURES.json   (client_fit fixtures: a list of {id, headers, body})")
        return 2
    with open(argv[1]) as f:
        fixtures = json.load(f)
    reg = {"entries": [{"id": fx["id"]} for fx in fixtures]}
    apply(reg, {fx["id"]: probe_from_fixture(fx) for fx in fixtures})
    for e in reg["entries"]:
        d = e["dialect"]
        print("%-26s %-9s %-24s %s" % (e["id"], d["kind"], d["where"],
                                       " ".join("%s=%s" % kv for kv in sorted(d["payable_by"].items()))))
    print("counts.payable_by", json.dumps(reg["counts"]["payable_by"], sort_keys=True), "of", len(fixtures))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
