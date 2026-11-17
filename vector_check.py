"""Compare the 402 bytes an observer received against a frozen test vector.

    python3 vector_check.py --vector vectors/nano-exact-v1.json --observed FILE
                            [--structure-only] [--parser-client NAME --parser-version V]

FILE holds the bytes as received: either the raw 402 JSON body or the base64 value of an
x402 v2 PAYMENT-REQUIRED header (a leading "PAYMENT-REQUIRED:" label is tolerated).
Whitespace around the bytes is dropped before hashing; nothing else is normalised.

Prints one JSON object on stdout. Exit 0: every structural field matches (and, without
--structure-only, the body is byte-identical to the vector's). Exit 1: a mismatch or a
challenge the checker cannot read as a Nano offer. Exit 2: an input error (unreadable
observed file, corrupt or unfrozen vector). Nothing is fetched and nothing is paid.
Stdlib only.
"""

import argparse, base64, binascii, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nanoaddr

NANO_NETWORK = "nano:mainnet"
FIELDS = ("x402Version", "scheme", "network", "asset", "amount_raw", "payTo", "maxTimeoutSeconds")
MAY_DIFFER = ("amount_raw", "payTo")  # a real seller quotes its own amount and address


class CheckError(Exception):
    def __init__(self, code, exit_code, message=""):
        super().__init__(message or code)
        self.code, self.exit_code = code, exit_code


def load_vector(path):
    try:
        with open(path, "rb") as f:
            vec = json.loads(f.read().decode("utf-8"))
        body = vec["response"]["body"]
        stored = vec["response"]["body_sha256"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError("vector_unreadable", 2, str(exc))
    if vec.get("status") != "frozen":
        raise CheckError("vector_not_frozen", 2, "vector status is %r, not 'frozen'" % vec.get("status"))
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != stored:
        raise CheckError("vector_corrupt", 2, "response.body does not hash to response.body_sha256")
    return vec


def decode_observed(raw):
    """Return (body_bytes, parsed_json, form). Raises CheckError not_json."""
    data = raw.strip()
    try:
        return data, json.loads(data.decode("utf-8")), "body"
    except (UnicodeDecodeError, ValueError):
        pass
    text = data
    if text[:17].lower() == b"payment-required:":
        text = text[17:].strip()
    try:
        decoded = base64.b64decode(text, validate=True)
        return decoded.strip(), json.loads(decoded.decode("utf-8")), "header_b64"
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise CheckError("not_json", 2, "observed bytes are neither JSON nor base64 of JSON")


def _cmp(observed, expected):
    if observed is None:
        return "missing"
    return "match" if observed == expected else "differs"


def check(vec, raw, structure_only=False, client=None, client_version=None):
    """Return (report_dict, exit_code). Raises CheckError only for input errors (exit 2)."""
    body_bytes, doc, form = decode_observed(raw)
    want = vec["expected_fields"]
    vec_body = vec["response"]["body"].encode("utf-8")
    report = {
        "vector_id": vec["vector_id"],
        "observed_sha256": hashlib.sha256(body_bytes).hexdigest(),
        "observed_form": form,
        "byte_identical": body_bytes == vec_body,
        "structural": None,
        "payTo_checksum_valid": None,
        "parser_profile": {"client": client, "client_version": client_version},
        "challenge": None,
        "outcome": "observed",
    }
    accepts = doc.get("accepts") if isinstance(doc, dict) else None
    if not isinstance(accepts, list) or not accepts:
        report["error"] = "no_accepts"
        return report, 1
    entry = next((a for a in accepts if isinstance(a, dict) and a.get("network") == NANO_NETWORK), None)
    if entry is None:
        report["error"] = "no_nano_entry"
        return report, 1
    amount = entry.get("amount", entry.get("maxAmountRequired"))
    got = {
        "x402Version": doc.get("x402Version"),
        "scheme": entry.get("scheme"),
        "network": entry.get("network"),
        "asset": entry.get("asset"),
        "amount_raw": amount,
        "payTo": entry.get("payTo"),
        "maxTimeoutSeconds": entry.get("maxTimeoutSeconds"),
    }
    structural = {k: _cmp(got[k], want[k]) for k in FIELDS}
    report["structural"] = structural
    report["challenge"] = {
        "sha256": report["observed_sha256"],
        "x402_version": got["x402Version"],
        "scheme": got["scheme"],
        "network": got["network"],
        "asset": got["asset"],
        "pay_to": got["payTo"],
        "amount_raw": got["amount_raw"],
        "max_timeout_seconds": got["maxTimeoutSeconds"],
        "extensions": list(doc.get("extensions") or []) if isinstance(doc.get("extensions"), list) else [],
    }
    pay_to = got["payTo"]
    report["payTo_checksum_valid"] = nanoaddr.is_valid(pay_to) if isinstance(pay_to, str) else False
    if not report["payTo_checksum_valid"]:
        report["error"] = "payto_checksum"
        return report, 1
    if structure_only:
        ok = all(v == "match" or (k in MAY_DIFFER and v == "differs") for k, v in structural.items())
    else:
        ok = report["byte_identical"] and all(v == "match" for v in structural.values())
    if not ok:
        report["error"] = "mismatch"
    return report, (0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--vector", required=True)
    ap.add_argument("--observed", required=True, help="file with the bytes received ('-' for stdin)")
    ap.add_argument("--structure-only", action="store_true",
                    help="exit 0 when only amount_raw and payTo differ (a real seller's 402)")
    ap.add_argument("--parser-client")
    ap.add_argument("--parser-version")
    a = ap.parse_args(argv)
    try:
        vec = load_vector(a.vector)
        try:
            if a.observed == "-":
                raw = sys.stdin.buffer.read()
            else:
                with open(a.observed, "rb") as f:
                    raw = f.read()
        except OSError as exc:
            raise CheckError("observed_unreadable", 2, str(exc))
        report, code = check(vec, raw, a.structure_only, a.parser_client, a.parser_version)
    except CheckError as exc:
        report, code = {"error": exc.code, "message": str(exc), "outcome": "observed"}, exc.exit_code
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
