import base64
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)
import dialect  # noqa: E402
import client_fit as cf  # noqa: E402

FIXTURES = os.path.join(PARENT, "client_fit_fixtures.json")
CLIENTS = dialect.load_clients()
GOOD = "nano_3mr761i87o7o33hmrd67a1emt81j6djgdqeyod95ip5qcidz77b71x4ukqea"
OTHER = "nano_3z335ug5oz6sxfgcfz3kdqdrgn5otx7ht3epuc3kuimka6hc59xqem1jrzqy"
W = "x402-mcp-wrapper+x402nano-exact-1.1.0"  # B19: reads only an MCP tool result
BP = "buyer_plan"  # ours, the 7th row
REP = "x402-gateway-0.18.2-rep"
# buyer_plan is `pending` here (not published): never in CLIENTS or counts.payable_by; WITH_BP adds it
WITH_BP = dict(CLIENTS)
WITH_BP[BP] = cf.load_clients(os.path.join(PARENT, "clients.json"), include_pending=True)[BP]


def b64(doc):
    return base64.b64encode(json.dumps(doc).encode()).decode()


def accept(amount="1" + "0" * 27, network="nano:mainnet", pay_to=GOOD, extra=True):
    a = {"scheme": "exact", "network": network, "asset": "XNO", "amount": amount, "payTo": pay_to}
    if extra:
        a["extra"] = {}
    return a


def probe(headers=None, body="", status=402):
    text = body if isinstance(body, str) else json.dumps(body)
    return {"http_status": status, "raw402": dialect.capture(headers or {}, text)}


def fixtures():
    with open(FIXTURES) as f:
        return json.load(f)


class Spec(unittest.TestCase):
    """specs/agent-tool-registry-dialect.md tests 1-6, through probe.py's result shape."""

    def test_1_header_only(self):
        d = dialect.row_dialect(probe({"Payment-Required": b64({"x402Version": 2, "accepts": [accept()]})}), WITH_BP)
        self.assertEqual(d["where"], "header:PAYMENT-REQUIRED")
        self.assertEqual(d["x402Version"], 2)
        self.assertEqual(d["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "yes", "x402-dotnet-client": "no:resource",
                                          W: "no:where", BP: "yes"})
        self.assertEqual(d["accepts"][0]["payTo_checksum_valid"], True)
        self.assertEqual(set(d["accepts"][0]), set(dialect.ACCEPT_KEYS))

    def test_2_nanswap_hyphen(self):
        d = dialect.row_dialect(probe(body={"accepts": [accept(network="nano-mainnet")]}), WITH_BP)
        self.assertEqual(d["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "no:network", "x402-dotnet-client": "no:where",
                                          W: "no:where", BP: "yes"})

    def test_3_pyfile_courier_cap(self):
        d = dialect.row_dialect(probe(body={"accepts": [accept(amount="28760000000000000000000000000")]}), WITH_BP)
        self.assertEqual(d["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "no:cap", "x402-dotnet-client": "no:where",
                                          W: "no:where", BP: "yes"})

    def test_4_bad_header_unknown_and_row_builds(self):
        reg = {"entries": [{"id": "x"}]}
        dialect.apply(reg, {"x": probe({"X-Payment-Required": "%%% not base64"})}, clients=WITH_BP)
        d = reg["entries"][0]["dialect"]
        self.assertEqual((d["where"], d["accepts"]), ("header:X-PAYMENT-REQUIRED", []))
        self.assertEqual(d["payable_by"], {"nano-pay": "UNKNOWN", "kilkelly-mcp": "UNKNOWN", "x402-dotnet-client": "UNKNOWN",
                                          W: "UNKNOWN", BP: "UNKNOWN"})

    def test_5_payto_moves(self):
        a = probe(body={"accepts": [accept()]})
        b = probe(body={"accepts": [accept(pay_to=OTHER)]})
        self.assertIs(dialect.row_dialect(a, CLIENTS, b)["payto_fixed"], False)
        self.assertIs(dialect.row_dialect(a, CLIENTS, a)["payto_fixed"], True)
        self.assertIsNone(dialect.row_dialect(a, CLIENTS)["payto_fixed"])

    def test_6_counts_equal_yes_rows(self):
        fx = fixtures()
        reg = {"counts": {"total": len(fx)}, "entries": [{"id": x["id"]} for x in fx]}
        dialect.apply(reg, {x["id"]: dialect.probe_from_fixture(x) for x in fx}, clients=CLIENTS)
        for c in CLIENTS:
            yes = sum(1 for e in reg["entries"] if e["dialect"]["payable_by"][c] == "yes")
            self.assertEqual(reg["counts"]["payable_by"][c], yes)
        self.assertEqual(reg["counts"]["total"], len(fx))


class Registry(unittest.TestCase):
    def test_non_402_and_unprobed_are_null(self):
        reg = {"entries": [{"id": "ok200"}, {"id": "dead"}, {"id": "mail"}]}
        probes = {"ok200": probe(body={"accepts": [accept()]}, status=200),
                  "dead": {"http_status": None, "error": "URLError"}}
        dialect.apply(reg, probes, clients=CLIENTS)
        self.assertEqual([e["dialect"] for e in reg["entries"]], [None, None, None])
        self.assertEqual(reg["counts"]["payable_by"], {"kilkelly-mcp": 0, "nano-pay": 0, "x402-dotnet-client": 0, W: 0})

    def test_pending_client_never_counted(self):
        self.assertNotIn("kilkelly-mcp+extra", CLIENTS)
        reg = {"entries": [{"id": "a"}]}
        dialect.apply(reg, {"a": probe(body={"accepts": [accept()]})})
        self.assertNotIn("kilkelly-mcp+extra", reg["counts"]["payable_by"])

    def test_capture_keeps_only_payment_headers_and_caps_body(self):
        c = dialect.capture({"payment-required": "abc", "Set-Cookie": "s=1", "X-Payment-Required": "d"}, "x" * 30000)
        self.assertEqual(c["headers"], {"PAYMENT-REQUIRED": "abc", "X-PAYMENT-REQUIRED": "d"})
        self.assertEqual(len(c["body"]), dialect.BODY_LIMIT)

    def test_output_is_json(self):
        fx = fixtures()
        reg = {"entries": [{"id": x["id"]} for x in fx]}
        dialect.apply(reg, {x["id"]: dialect.probe_from_fixture(x) for x in fx}, clients=CLIENTS)
        json.loads(json.dumps(reg))


class Parity(unittest.TestCase):
    """The port says exactly what client_fit.py says, fixture by fixture."""

    def test_every_fixture_matches_client_fit(self):
        for x in fixtures():
            with self.subTest(x["id"]):
                d = dialect.row_dialect(dialect.probe_from_fixture(x), CLIENTS)
                exp = x["expect"]
                self.assertEqual(d["kind"], exp["dialect"])
                self.assertEqual(d["payable_by"]["nano-pay"], exp["nano-pay"])
                self.assertEqual(d["payable_by"]["kilkelly-mcp"], exp["kilkelly-mcp"])
                self.assertEqual(d["payable_by"], cf.verdicts(x["headers"], x["body"], CLIENTS)["payable_by"])

    def test_extra_fix_pays_3_of_8(self):
        fx = fixtures()
        allc = cf.load_clients(os.path.join(PARENT, "clients.json"), include_pending=True)
        reg = {"entries": [{"id": x["id"]} for x in fx]}
        dialect.apply(reg, {x["id"]: dialect.probe_from_fixture(x) for x in fx}, clients=allc)
        counts = reg["counts"]["payable_by"]
        # 9th and 10th: MCP results (B19), UNKNOWN for every HTTP-era client; 11th: the bound
        # x402-gateway order, paid only by ours (buyer_plan), so the HTTP-era counts stay as for 8
        self.assertEqual(len(fx), 11)
        self.assertEqual((counts["nano-pay"], counts["kilkelly-mcp"], counts["kilkelly-mcp+extra"]), (5, 3, 3))
        self.assertEqual((counts["x402-dotnet-client"], counts[W], counts[BP]), (1, 0, 10))
        # PR agent run 434: kilkelly installs @x402nano/exact 0.1.1 (no `extra` read), so it gains nothing
        gained = sorted(e["id"] for e in reg["entries"]
                        if e["dialect"]["payable_by"]["kilkelly-mcp+extra"] == "yes"
                        and e["dialect"]["payable_by"]["kilkelly-mcp"] != "yes")
        self.assertEqual(gained, [])

    def test_installable_counts_per_client(self):
        fx = fixtures()
        reg = {"entries": [{"id": x["id"]} for x in fx]}
        dialect.apply(reg, {x["id"]: dialect.probe_from_fixture(x) for x in fx}, clients=CLIENTS)
        # buyer_plan (ours, not published) is `pending`, so the public count never credits it
        self.assertNotIn(BP, CLIENTS)
        self.assertEqual(reg["counts"]["payable_by"], {"kilkelly-mcp": 3, "nano-pay": 5,
                                                       "x402-dotnet-client": 1, W: 0})


class RepBinding(unittest.TestCase):
    """The 11th fixture, x402-gateway 0.18.2 (xno-binding/v1/rep), through probe.py's result shape:
    yes for buyer_plan only, and each other client stopped for the same reason client_fit gives."""

    WANT = {"nano-pay": "no:binding", "kilkelly-mcp": "no:network", "x402-dotnet-client": "no:network",
            W: "no:where", BP: "yes"}

    def fx(self):
        return [x for x in fixtures() if x["id"] == REP][0]

    def test_kind_and_verdicts(self):
        d = dialect.row_dialect(dialect.probe_from_fixture(self.fx()), WITH_BP)
        self.assertEqual((d["kind"], d["where"], d["x402Version"]), ("rep-binding", "header:PAYMENT-REQUIRED", 2))
        self.assertEqual(d["payable_by"], self.WANT)
        allc = cf.load_clients(os.path.join(PARENT, "clients.json"), include_pending=True)
        d = dialect.row_dialect(dialect.probe_from_fixture(self.fx()), allc)
        self.assertEqual([k for k, v in d["payable_by"].items() if v == "yes"], [BP])
        self.assertEqual(d["payable_by"]["kilkelly-mcp+extra"], "no:network")

    def test_binding_check_is_what_stops_the_http_clients(self):
        # FAILS if client_fit's binding check is removed: on nano:mainnet every HTTP client would then pass
        # the network and be judged on cap or yes, not no:binding
        x = self.fx()
        doc = json.loads(base64.b64decode(x["headers"]["PAYMENT-REQUIRED"]))
        doc["accepts"][-1]["network"] = "nano:mainnet"
        doc["accepts"][-1]["amount"] = "1" + "0" * 27  # under every cap, so only the binding can refuse it
        d = dialect.row_dialect(probe({"PAYMENT-REQUIRED": b64(doc)}), WITH_BP)
        for k in ("nano-pay", "kilkelly-mcp", "x402-dotnet-client"):
            self.assertEqual(d["payable_by"][k], "no:binding", k)
        self.assertEqual(d["payable_by"][BP], "yes")  # the one row that lists the binding
        # the same accept without the binding pair is paid
        del doc["accepts"][-1]["extra"]["binding"]
        d = dialect.row_dialect(probe({"PAYMENT-REQUIRED": b64(doc)}), CLIENTS)
        self.assertEqual(d["kind"], "exact")
        self.assertEqual(d["payable_by"]["nano-pay"], "yes")


if __name__ == "__main__":
    unittest.main()
