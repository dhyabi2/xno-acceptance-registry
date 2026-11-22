import base64
import copy
import json
import os
import sys
import unittest

# only the repository dir goes on sys.path (as tests/test_dialect.py); the fixtures sit beside client_fit.py
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import client_fit as cf  # noqa: E402

CLIENTS = cf.load_clients()
GOOD = "nano_3mr761i87o7o33hmrd67a1emt81j6djgdqeyod95ip5qcidz77b71x4ukqea"
BAD = GOOD[:-1] + ("a" if GOOD[-1] != "a" else "b")
W = "x402-mcp-wrapper+x402nano-exact-1.1.0"  # B19: reads only an MCP tool result, so every HTTP quote is no:where
W2 = "x402-mcp-wrapper+x402nano-exact-findDefaultAsset"  # pending: dhyabi2/exact feat/nano-default-asset 199f9ba
BP = "buyer_plan"  # ours, the 7th row (expert GUIDE 2026-11-22T12:50Z): what our planner plans
# buyer_plan is `pending` here (not published), so it is never in CLIENTS; WITH_BP adds it back to
# check its verdicts next to the installable clients
WITH_BP = dict(CLIENTS)
WITH_BP[BP] = cf.load_clients(include_pending=True)[BP]


def b64(doc):
    return base64.b64encode(json.dumps(doc).encode()).decode()


def accept(amount="1000000000000000000000000000", network="nano:mainnet", extra=True, pay_to=GOOD, **kw):
    a = {"scheme": "exact", "network": network, "asset": "XNO", "amount": amount, "payTo": pay_to}
    if extra:
        a["extra"] = {}
    a.update(kw)
    return a


class Spec(unittest.TestCase):
    """The seven tests of specs/agent-tool-registry-dialect.md (7 = the vector is untouched: not here)."""

    def test_1_header_only(self):
        doc = {"x402Version": 2, "accepts": [accept(amount="1" + "0" * 27)]}
        v = cf.verdicts({"PAYMENT-REQUIRED": b64(doc)}, "", WITH_BP)
        self.assertEqual(v["where"], "header:PAYMENT-REQUIRED")
        # x402-dotnet drops a header without `resource` (a required member of PaymentRequiredResponse)
        self.assertEqual(v["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "yes", "x402-dotnet-client": "no:resource",
                                           W: "no:where", BP: "yes"})

    def test_2_hyphen_network(self):
        v = cf.verdicts({}, {"accepts": [accept(network="nano-mainnet")]}, WITH_BP)
        # nano-pay keeps any network starting with "nano" (feeless402@fab7f69 x402.py:250-257, run 439)
        self.assertEqual(v["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "no:network", "x402-dotnet-client": "no:where",
                                           W: "no:where", BP: "yes"})

    def test_2b_nano_pay_network_rule_from_source(self):
        """PR agent run 439 (GUIDE 19Z): pick_nano_offer keeps network.lower().startswith("nano") or
        asset.lower() in (xno, nano); the other two clients need the exact string."""
        np = CLIENTS["nano-pay"]
        for net, asset, want in (("nano-mainnet", "XNO", True), ("NANO:mainnet", "x", True),
                                 ("eip155:8453", "XNO", True), ("eip155:8453", "nano", True),
                                 ("eip155:8453", "USDC", False), (None, None, False),
                                 (["nano:mainnet"], "USDC", False), (5, "USDC", False)):
            self.assertIs(cf.network_ok({"network": net, "asset": asset}, np), want, (net, asset))
        self.assertIs(cf.network_ok({"network": "nano-mainnet", "asset": "XNO"}, CLIENTS["kilkelly-mcp"]), False)
        self.assertIs(cf.network_ok({"network": "nano:mainnet"}, CLIENTS["x402-dotnet-client"]), True)

    def test_2c_nanswap_nodes_fixture_paid_by_nano_pay(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            fx = [x for x in json.load(f) if x["id"] == "nanswap-nodes"][0]
        v = cf.verdicts(fx["headers"], fx["body"], CLIENTS)
        self.assertEqual(v["payable_by"]["nano-pay"], "yes")
        self.assertEqual(v["payable_by"]["kilkelly-mcp"], "no:network")

    def test_3_cap(self):
        v = cf.verdicts({}, {"accepts": [accept(amount="28760000000000000000000000000")]}, WITH_BP)
        self.assertEqual(v["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "no:cap", "x402-dotnet-client": "no:where",
                                           W: "no:where", BP: "yes"})

    def test_4_bad_header_is_unknown_never_no(self):
        v = cf.verdicts({"Payment-Required": "%%% not base64 %%%"}, "", WITH_BP)
        self.assertEqual(v["where"], "header:PAYMENT-REQUIRED")
        self.assertEqual(v["accepts"], [])
        self.assertEqual(v["payable_by"], {"nano-pay": "UNKNOWN", "kilkelly-mcp": "UNKNOWN", "x402-dotnet-client": "UNKNOWN",
                                           W: "UNKNOWN", BP: "UNKNOWN"})

    def test_5_payto_moves(self):
        a = cf.parse_402({}, {"accepts": [accept()]})
        b = cf.parse_402({}, {"accepts": [accept(pay_to="nano_3z335ug5oz6sxfgcfz3kdqdrgn5otx7ht3epuc3kuimka6hc59xqem1jrzqy")]})
        self.assertIs(cf.payto_fixed(a, b), False)
        self.assertIs(cf.payto_fixed(a, a), True)
        self.assertIsNone(cf.payto_fixed(a, None))

    def test_6_count(self):
        rows = [{"payable_by": {"nano-pay": "yes", "kilkelly-mcp": "no:extra"}},
                {"payable_by": {"nano-pay": "no:scheme", "kilkelly-mcp": "no:scheme"}},
                {"payable_by": {"nano-pay": "yes", "kilkelly-mcp": "yes"}}]
        self.assertEqual(cf.count_payable(rows), {"nano-pay": 2, "kilkelly-mcp": 1})


class Errors(unittest.TestCase):
    def test_body_not_json(self):
        v = cf.verdicts({}, "<html>402</html>", CLIENTS)
        self.assertEqual((v["where"], v["accepts"], v["dialect"]), ("body", [], "UNKNOWN"))
        self.assertEqual(set(v["payable_by"].values()), {"UNKNOWN"})

    def test_payto_checksum(self):
        self.assertTrue(cf.nano_checksum_ok(GOOD))
        self.assertFalse(cf.nano_checksum_ok(BAD))
        self.assertFalse(cf.nano_checksum_ok("0xabc"))
        v = cf.verdicts({}, {"accepts": [accept(pay_to=BAD)]}, CLIENTS)
        self.assertEqual(v["payable_by"]["nano-pay"], "no:payTo")

    def test_amount_ambiguous(self):
        v = cf.verdicts({}, {"accepts": [accept(maxAmountRequired="2000000000000000000000000000")]}, CLIENTS)
        self.assertEqual(v["payable_by"]["nano-pay"], "no:amount_ambiguous")
        v = cf.verdicts({}, {"accepts": [accept(maxAmountRequired="1000000000000000000000000000")]}, CLIENTS)
        self.assertEqual(v["payable_by"]["nano-pay"], "yes")

    def test_max_amount_required_alone(self):
        a = accept()
        del a["amount"]
        a["maxAmountRequired"] = "1000000000000000000000000000"
        self.assertEqual(cf.verdicts({}, {"accepts": [a]}, CLIENTS)["payable_by"]["nano-pay"], "yes")

    def test_missing_extra_is_paid_by_kilkelly_as_installed(self):
        # PR agent run 434: kilkelly 1.1.0 installs @x402nano/exact 0.1.1, which never reads `extra`
        v = cf.verdicts({}, {"accepts": [accept(extra=False)]}, WITH_BP)
        self.assertEqual(v["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "yes", "x402-dotnet-client": "no:where",
                                           W: "no:where", BP: "yes"})
        # the mechanism stays for a client that does need it (a 1.x client without the extra?. fix)
        needy = {"needy": dict(CLIENTS["kilkelly-mcp"], needs_extra=True)}
        self.assertEqual(cf.verdicts({}, {"accepts": [accept(extra=False)]}, needy)["payable_by"],
                         {"needy": "no:extra"})

    def test_any_accept_that_fits_is_yes(self):
        v = cf.verdicts({}, {"accepts": [accept(network="base"), accept()]}, CLIENTS)
        self.assertEqual(v["payable_by"]["nano-pay"], "yes")

    def test_unicode_digit_and_zero_amount_are_no_cap(self):
        # PR agent run 432: '²'.isdigit() is True and int('²') raised ValueError; 0 raw is no send
        for amt in ("²", "٣", "0", "00", " 1", "-1"):
            v = cf.verdicts({}, {"accepts": [accept(amount=amt)]}, CLIENTS)
            self.assertEqual(v["payable_by"]["nano-pay"], "no:cap", amt)

    def test_deeply_nested_body_is_unknown_not_raised(self):
        # PR agent run 432: json.loads raised RecursionError, which is not a ValueError
        deep = "[" * 100000 + "]" * 100000
        self.assertEqual(cf.verdicts({}, deep, CLIENTS)["dialect"], "UNKNOWN")
        header = {cf.HEADER_NAMES[0]: base64.b64encode(deep.encode()).decode()}
        self.assertFalse(cf.parse_402(header, None)["parsed"])

    def test_first_failure_named(self):
        v = cf.verdicts({}, {"accepts": [accept(network="base", extra=False)]}, CLIENTS)
        self.assertEqual(v["payable_by"]["kilkelly-mcp"], "no:network")


class Fixtures(unittest.TestCase):
    """Real 402 shapes read by source (USAGE.md lane 3 04:5xZ and 05:4xZ; Feeless402 server.py at HEAD)."""

    def test_every_fixture(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            fixtures = json.load(f)
        self.assertGreaterEqual(len(fixtures), 8)
        allc = cf.load_clients(include_pending=True)
        for fx in fixtures:
            v = cf.verdicts(fx["headers"], fx["body"], CLIENTS)
            exp = fx["expect"]
            with self.subTest(fx["id"]):
                self.assertEqual(v["dialect"], exp["dialect"])
                self.assertEqual(v["payable_by"]["nano-pay"], exp["nano-pay"])
                self.assertEqual(v["payable_by"]["kilkelly-mcp"], exp["kilkelly-mcp"])
                # any other client a fixture pins, pending rows included
                va = cf.verdicts(fx["headers"], fx["body"], allc)["payable_by"]
                for k in exp:
                    if k != "dialect":
                        self.assertEqual(va[k], exp[k], k)
                for case in fx.get("expect_buyer", []):  # B19: verdicts under a stated buyer configuration
                    got = cf.verdicts(fx["headers"], fx["body"], allc, case["buyer"])["payable_by"]
                    self.assertEqual(got[case["client"]], case["verdict"], case)

    def test_pending_client_left_out_by_default(self):
        self.assertNotIn("kilkelly-mcp+extra", CLIENTS)
        self.assertIn("kilkelly-mcp+extra", cf.load_clients(include_pending=True))

    def test_extra_fix_pays_3_of_8(self):
        """PR agent run 434 corrects the 11-22 claim: kilkelly as installed (@x402nano/exact 0.1.1)
        already pays 3 of 8 (feeless402 and busyman-probe have no `extra`); the `extra?.` fix gains
        kilkelly nothing (nanswap-nodes stays no:network, cedarproof no:cap). nano-pay 5 of 8 since run 439
        (it pays nanswap-nodes' nano-mainnet)."""
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            fixtures = json.load(f)
        allc = cf.load_clients(include_pending=True)
        rows = [cf.verdicts(fx["headers"], fx["body"], allc) for fx in fixtures]
        counts = cf.count_payable(rows)
        # 9th: xmcp-65be4ee, 10th: xmcp-e3fcfca-v2 (B19): MCP results, UNKNOWN for every HTTP-era client;
        # 11th: x402-gateway-0.18.2-rep (run 454, rep-binding), paid by no client but ours (buyer_plan, GUIDE 2026-11-22T12:50Z), so these counts stay
        self.assertEqual(len(rows), 11)
        self.assertEqual(counts["kilkelly-mcp"], 3)
        self.assertEqual(counts["kilkelly-mcp+extra"], 3)
        self.assertEqual(counts["nano-pay"], 5)
        self.assertEqual(counts[W], 0)  # the default spendControls {} refuses the one MCP v2 offer
        self.assertEqual(counts[BP], 10)  # ours (GUIDE 2026-11-22T12:50Z): all but xmcp-65be4ee
        gained = sorted(fx["id"] for fx, r in zip(fixtures, rows)
                        if r["payable_by"]["kilkelly-mcp+extra"] == "yes"
                        and r["payable_by"]["kilkelly-mcp"] != "yes")
        self.assertEqual(gained, [])

    def test_three_dialects_present(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            fixtures = json.load(f)
        dialects = {cf.verdicts(fx["headers"], fx["body"], CLIENTS)["dialect"] for fx in fixtures}
        self.assertTrue({"exact", "send-hash", "invoice"} <= dialects)


class DotnetClient(unittest.TestCase):
    """x402-dotnet-client (michielpost/x402-dotnet@127c1fd, NuGet x402.Client.Nano 0.0.3), read from source:
    header only, x402Version 2, `resource` required, asset XNO, `amount` key, cap = host allowance."""

    C = {"d": CLIENTS["x402-dotnet-client"]}

    def v(self, doc, body=""):
        return cf.verdicts({"PAYMENT-REQUIRED": b64(doc)}, body, self.C)["payable_by"]["d"]

    def test_full_v2_header_is_yes(self):
        self.assertEqual(self.v({"x402Version": 2, "resource": {"url": "/x"}, "accepts": [accept()]}), "yes")

    def test_body_only_is_no_where(self):
        doc = {"x402Version": 2, "resource": {"url": "/x"}, "accepts": [accept()]}
        self.assertEqual(cf.verdicts({}, doc, self.C)["payable_by"]["d"], "no:where")

    def test_v1_header_is_no_version(self):
        self.assertEqual(self.v({"x402Version": 1, "resource": {}, "accepts": [accept()]}), "no:version")

    def test_missing_resource(self):
        self.assertEqual(self.v({"x402Version": 2, "accepts": [accept()]}), "no:resource")

    def test_asset_case_insensitive_and_other_asset(self):
        self.assertEqual(self.v({"x402Version": 2, "resource": {}, "accepts": [accept(asset="xno")]}), "yes")
        self.assertEqual(self.v({"x402Version": 2, "resource": {}, "accepts": [accept(asset="nano")]}), "no:asset")

    def test_max_amount_required_alone_is_no_amount_key(self):
        a = accept()
        del a["amount"]
        a["maxAmountRequired"] = "1000000000000000000000000000"
        self.assertEqual(self.v({"x402Version": 2, "resource": {}, "accepts": [a]}), "no:amount_key")

    def test_no_fixed_cap_but_zero_is_no(self):
        big = "9" * 40
        self.assertEqual(self.v({"x402Version": 2, "resource": {}, "accepts": [accept(amount=big)]}), "yes")
        self.assertEqual(self.v({"x402Version": 2, "resource": {}, "accepts": [accept(amount="0")]}), "no:cap")

    def test_old_clients_unchanged_by_new_keys(self):
        # the two older rows carry none of the new keys, so their verdicts are as before
        for k in ("nano-pay", "kilkelly-mcp"):
            for key in ("versions", "needs_resource", "asset", "amount_key"):
                self.assertNotIn(key, CLIENTS[k])

    def test_fixture_count_1_of_8(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            fixtures = json.load(f)
        rows = [cf.verdicts(fx["headers"], fx["body"], CLIENTS) for fx in fixtures]
        counts = cf.count_payable(rows)
        self.assertEqual((counts["x402-dotnet-client"], len(rows)), (1, 11))
        yes = [fx["id"] for fx, r in zip(fixtures, rows) if r["payable_by"]["x402-dotnet-client"] == "yes"]
        self.assertEqual(yes, ["feeless402"])


class XmcpFixture(unittest.TestCase):
    """basementstudio/xmcp @ 65be4ee examples/x402-http word-count, read from source (never run): the
    unpaid tools/call is answered HTTP 200 with the terms inside a JSON-RPC result (provider.ts:200-216),
    V1 (x402Version 1, network "nano", maxAmountRequired; verify.ts:97-109, provider.ts:204)."""

    ALL = cf.load_clients(include_pending=True)

    def fixture(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            return [x for x in json.load(f) if x["id"] == "xmcp-65be4ee"][0]

    def test_four_verdicts_pinned(self):
        fx = self.fixture()
        v = cf.verdicts(fx["headers"], fx["body"], self.ALL)
        self.assertEqual(v["dialect"], "UNKNOWN")
        # no HTTP-era client reads terms nested in result.structuredContent: nothing at the top level
        # parses. The MCP wrapper (B19) reads them, and stops at x402Version 1 (core client/index.mjs:254-256)
        self.assertEqual(v["payable_by"], {"nano-pay": "UNKNOWN", "kilkelly-mcp": "UNKNOWN",
                                           "kilkelly-mcp+extra": "UNKNOWN",
                                           "x402-dotnet-client": "UNKNOWN", W: "no:version",
                                           W2: "no:version", BP: "no:network"})
        self.assertEqual(v["payable_by"], {k: fx["expect"][k] for k in self.ALL})

    def test_unwrapped_terms_if_a_client_read_structured_content(self):
        """Not a claim that any client reads it: what each row says of the terms themselves."""
        fx = self.fixture()
        inner = fx["body"]["result"]["structuredContent"]
        self.assertEqual(json.loads(fx["body"]["result"]["content"][0]["text"]), inner)
        v = cf.verdicts({}, inner, self.ALL)
        self.assertEqual(v["payable_by"], {"nano-pay": "yes", "kilkelly-mcp": "no:network",
                                           "kilkelly-mcp+extra": "no:network",
                                           "x402-dotnet-client": "no:where", W: "no:where", W2: "no:where", BP: "no:network"})
        a = v["accepts"][0]
        self.assertEqual((a["network"], a["amount_raw"], a["asset"]),
                         ("nano", "1000000000000000000000000000", "XNO"))

    def test_bridged_v1_offer_still_fails_kilkelly(self):
        # the host bridge changes the form, not the terms: v1 network "nano" stays no:network
        fx = self.fixture()
        v = cf.verdicts(fx["headers"], fx["body"], self.ALL, {"mcp_handoff": "base64-header"})
        self.assertEqual(v["payable_by"]["kilkelly-mcp"], "no:network")
        self.assertEqual(cf.verdicts(fx["headers"], fx["body"], self.ALL,
                                     {"mcp_handoff": "raw"})["payable_by"]["kilkelly-mcp"], "no:bridge")


class XmcpV2Fixture(unittest.TestCase):
    """B19: basementstudio/xmcp PR #805 head e3fcfca, examples/x402-http word-count with nano.x402Version 2
    (middleware.ts:18-19), read from source, never run: HTTP 200, JSON-RPC result isError true (provider.ts:213),
    v2 terms in structuredContent (verify.ts:141-155), extra {name XNO, decimals 30} (constants.ts:40).
    One pinning test per client."""

    ALL = cf.load_clients(include_pending=True)
    NANO = {"spendControls": {"allowedAssets": [{"network": "nano:mainnet", "asset": "XNO"}]}}

    def fixture(self):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            return [x for x in json.load(f) if x["id"] == "xmcp-e3fcfca-v2"][0]

    def v(self, buyer=None, body=None):
        fx = self.fixture()
        return cf.verdicts(fx["headers"], fx["body"] if body is None else body, self.ALL, buyer)

    def without_extra(self):
        body = copy.deepcopy(self.fixture()["body"])
        for a in body["result"]["structuredContent"]["accepts"]:
            del a["extra"]
        body["result"]["content"][0]["text"] = json.dumps(body["result"]["structuredContent"])
        return body

    def test_fixture_is_what_e3fcfca_emits(self):
        fx = self.fixture()
        r = fx["body"]["result"]
        self.assertIs(r["isError"], True)
        self.assertEqual(fx["headers"], {})
        sc = r["structuredContent"]
        self.assertEqual(json.loads(r["content"][0]["text"]), sc)
        self.assertEqual((sc["x402Version"], sc["resource"]["url"]), (2, "mcp://tool/word-count"))
        self.assertEqual(sc["accepts"], [{"scheme": "exact", "network": "nano:mainnet",
                                          "amount": "1000000000000000000000000000",
                                          "payTo": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
                                          "asset": "XNO", "maxTimeoutSeconds": 300,
                                          "extra": {"name": "XNO", "decimals": 30}}])
        for cite in ("e3fcfca", "constants.ts:40", "provider.ts:213", "provider.ts:166-167", "payment-header.ts",
                     "PLACEHOLDER"):
            self.assertIn(cite, fx["source"])

    def test_default_view_and_dialect(self):
        v = self.v()
        self.assertEqual((v["dialect"], v["where"]), ("UNKNOWN", "body"))  # the HTTP view, as for 65be4ee
        self.assertEqual((v["mcp"]["where"], v["mcp"]["x402Version"], v["mcp"]["dialect"]),
                         ("mcp:structuredContent", 2, "exact"))
        self.assertEqual(v["payable_by"], {"nano-pay": "UNKNOWN", "kilkelly-mcp": "UNKNOWN",
                                           "kilkelly-mcp+extra": "UNKNOWN", "x402-dotnet-client": "UNKNOWN",
                                           W: "no:spend_controls", W2: "yes", BP: "yes"})

    def test_client_1_nano_pay_http_only(self):
        # x402_pay fetches a URL over HTTP; it is never handed a tool result, bridged or not
        for buyer in (None, {"mcp_handoff": "raw"}, {"mcp_handoff": "base64-header"}, self.NANO):
            self.assertEqual(self.v(buyer)["payable_by"]["nano-pay"], "UNKNOWN", buyer)

    def test_client_2_kilkelly_yes_via_host_bridge_raw_refused(self):
        self.assertEqual(self.v({"mcp_handoff": "raw"})["payable_by"]["kilkelly-mcp"], "no:bridge")
        self.assertEqual(self.v({"mcp_handoff": "base64-header"})["payable_by"]["kilkelly-mcp"], "yes")
        self.assertEqual(self.v()["payable_by"]["kilkelly-mcp"], "UNKNOWN")  # no handoff stated
        # the bridge is exactly base64 of the terms, read as a PAYMENT-REQUIRED header
        sc = self.fixture()["body"]["result"]["structuredContent"]
        hdr = {"PAYMENT-REQUIRED": cf.bridge_header(sc)}
        self.assertEqual(json.loads(base64.b64decode(hdr["PAYMENT-REQUIRED"])), sc)
        self.assertEqual(cf.verdicts(hdr, "", {"k": CLIENTS["kilkelly-mcp"]})["payable_by"]["k"], "yes")

    def test_client_3_kilkelly_extra_pending_same_bridge(self):
        self.assertNotIn("kilkelly-mcp+extra", CLIENTS)
        self.assertEqual(self.v({"mcp_handoff": "raw"})["payable_by"]["kilkelly-mcp+extra"], "no:bridge")
        self.assertEqual(self.v({"mcp_handoff": "base64-header"})["payable_by"]["kilkelly-mcp+extra"], "yes")

    def test_client_4_dotnet_http_header_only(self):
        # an HttpClient handler reads the HTTP response's header; a JSON-RPC result reaches it as a body
        for buyer in (None, {"mcp_handoff": "raw"}, {"mcp_handoff": "base64-header"}):
            self.assertEqual(self.v(buyer)["payable_by"]["x402-dotnet-client"], "UNKNOWN", buyer)

    def test_client_5_mcp_wrapper_three_asserts(self):
        self.assertEqual(self.v(self.NANO)["payable_by"][W], "yes")
        self.assertEqual(self.v({})["payable_by"][W], "no:spend_controls")
        self.assertEqual(self.v()["payable_by"][W], "no:spend_controls")  # default = {}
        self.assertEqual(self.v(self.NANO, self.without_extra())["payable_by"][W], "no:extra")

    def test_client_5_spend_controls_variants(self):
        def w(sc, body=None):
            return self.v({"spendControls": sc}, body)["payable_by"][W]
        self.assertEqual(w(False), "yes")
        self.assertEqual(w({"allowedAssets": True}), "yes")
        self.assertEqual(w({"allowedAssets": [{"network": "nano:*", "asset": "xno"}]}), "yes")  # glob, any case
        self.assertEqual(w({"allowedAssets": [{"network": "eip155:*", "asset": "XNO"}]}), "no:spend_controls")
        self.assertEqual(w({"allowedAssets": [{"network": "nano:mainnet", "asset": "USDC"}]}), "no:spend_controls")
        self.assertEqual(w({"maxAmountPerPayment": "$100"}), "no:spend_controls")  # USD cap: no default asset
        cap = {"network": "nano:mainnet", "asset": "XNO"}
        self.assertEqual(w({"allowedAssets": [dict(cap, maxAmountPerPayment="1" + "0" * 27)]}), "yes")
        self.assertEqual(w({"allowedAssets": [dict(cap, maxAmountPerPayment="9" * 26)]}), "no:spend_controls")
        self.assertEqual(w({"allowedAssets": [dict(cap, maxAmountPerPayment="$1")]}), "no:spend_controls")
        # spend controls come before the extra read (selectPaymentRequirements runs first)
        self.assertEqual(w({}, self.without_extra()), "no:spend_controls")

    def test_client_5_on_find_default_asset_branch(self):
        """GUIDE 09Z: on dhyabi2/exact feat/nano-default-asset 199f9ba the fifth client on default {} turns
        from no:spend_controls to yes; the default "$1" cap is 1 whole XNO (core client/index.mjs:21, :55-56)."""
        self.assertNotIn(W2, CLIENTS)  # pending: never counted as installable
        self.assertEqual(self.v()["payable_by"][W2], "yes")
        self.assertEqual(self.v({})["payable_by"][W2], "yes")
        self.assertEqual(self.v()["payable_by"][W], "no:spend_controls")  # 1.1.0 unchanged

        def w(sc, amount=None, **kw):
            body = copy.deepcopy(self.fixture()["body"])
            for a in body["result"]["structuredContent"]["accepts"]:
                if amount is not None:
                    a["amount"] = amount
                a.update(kw)
            body["result"]["content"][0]["text"] = json.dumps(body["result"]["structuredContent"])
            return self.v({} if sc is None else {"spendControls": sc}, body)["payable_by"][W2]
        one, two = "1" + "0" * 30, "2" + "0" * 30
        self.assertEqual(w(None, one), "yes")                       # exactly 1 XNO
        self.assertEqual(w(None, two), "no:spend_controls")         # the branch's own 2 XNO test
        self.assertEqual(w({"maxAmountPerPayment": "$2"}, two), "yes")
        self.assertEqual(w({"maxAmountPerPayment": False}, two), "yes")
        self.assertEqual(w({"maxAmountPerPayment": "two"}, one), "no:spend_controls")  # parseMoney throws
        self.assertEqual(w(None, asset="xno"), "no:spend_controls")  # exact "XNO" match only (scheme.ts:53)
        # an allowedAssets entry's atomic cap wins over the USD default
        cap = {"network": "nano:*", "asset": "XNO", "maxAmountPerPayment": "3" + "0" * 30}
        self.assertEqual(w({"allowedAssets": [cap]}, two), "yes")
        # the branch is cut from c390127 (`extra?.workOptional`, scheme.ts:90): no extra is no TypeError
        self.assertEqual(self.v({}, self.without_extra())["payable_by"][W2], "yes")
        self.assertEqual(self.v(self.NANO, self.without_extra())["payable_by"][W], "no:extra")  # 1.1.0 unchanged

    def test_client_5_reads_content_text_when_no_structured_content(self):
        body = copy.deepcopy(self.fixture()["body"])
        del body["result"]["structuredContent"]
        v = self.v(self.NANO, body)
        self.assertEqual((v["mcp"]["where"], v["payable_by"][W]), ("mcp:content[0].text", "yes"))
        body["result"]["isError"] = False  # extractPaymentRequiredFromResult returns null (index.mjs:715-717)
        self.assertNotIn("mcp", self.v(self.NANO, body))
        self.assertEqual(self.v(self.NANO, body)["payable_by"][W], "UNKNOWN")

    def test_client_5_v2_needs_resource(self):
        body = copy.deepcopy(self.fixture()["body"])
        del body["result"]["structuredContent"]["resource"]
        self.assertEqual(self.v(self.NANO, body)["payable_by"][W], "no:resource")

    def test_backward_compatible_signatures(self):
        a = cf.parse_402({}, {"accepts": [accept()]})["accepts"][0]
        self.assertEqual(cf.client_fit(a, CLIENTS["nano-pay"], "body"), "yes")
        self.assertEqual(cf.client_fit(a, CLIENTS[W], "mcp:structuredContent"), "no:spend_controls")
        self.assertEqual(cf.client_fit(a, CLIENTS[W], "mcp:structuredContent", self.NANO), "yes")
        self.assertIsNone(cf.parse_mcp("not json"))
        self.assertIsNone(cf.parse_mcp("[" * 100000 + "]" * 100000))


class RepBindingFixture(unittest.TestCase):
    """PR agent run 454 (expert GUIDE 2026-11-22T11Z): profullstack/x402-gateway 0.18.2 (package.json:3; the
    GUIDE named 0.18.1), README.md:86 and :258-280, src/x402.js:105-158, src/nano.js:166-189, :293-311.
    Three USDC accepts, then XNO on network "nano" whose extra carries binding "xno-binding/v1/rep" and
    an orderId; the send's representative must commit to that order. No client others ship signs that; ours (buyer_plan) plans it since GUIDE 2026-11-22T12:50Z."""
    FID = "x402-gateway-0.18.2-rep"
    # every client, pending rows included, as the 10 earlier fixtures were judged BEFORE run 454 (computed
    # from the unmodified client_fit.py); run 454 must not move any of them
    W2N = "x402-mcp-wrapper+x402nano-exact-findDefaultAsset"
    OLD = {
        "feeless402": ("exact", "yes", "yes", "yes", "yes", "no:where", "no:where"),
        "busyman-probe": ("exact", "yes", "yes", "yes", "no:resource", "no:where", "no:where"),
        "cedarproof-diagnose": ("exact", "yes", "no:cap", "no:cap", "no:where", "no:where", "no:where"),
        "opscontrol-page-extract": ("exact", "yes", "yes", "yes", "no:where", "no:where", "no:where"),
        "noxid-nano-echo": ("send-hash",) + ("no:scheme",) * 6,
        "pururin-sequence": ("send-hash",) + ("no:scheme",) * 6,
        "pinnacle-url-check": ("invoice",) + ("no:invoice",) * 6,
        "nanswap-nodes": ("exact", "yes", "no:network", "no:network", "no:where", "no:where", "no:where"),
        "xmcp-65be4ee": ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "no:version", "no:version"),
        "xmcp-e3fcfca-v2": ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "no:spend_controls", "yes"),
    }
    ORDER = ("nano-pay", "kilkelly-mcp", "kilkelly-mcp+extra", "x402-dotnet-client", W, W2N)

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            cls.fixtures = json.load(f)
        cls.fx = [x for x in cls.fixtures if x["id"] == cls.FID][0]
        cls.allc = cf.load_clients(include_pending=True)

    def v(self, headers=None, body=None, clients=None):
        h = self.fx["headers"] if headers is None else headers
        return cf.verdicts(h, self.fx["body"] if body is None else body, clients or self.allc)

    def header_doc(self):
        return json.loads(base64.b64decode(self.fx["headers"]["PAYMENT-REQUIRED"]))

    def test_fixture_is_the_11th_and_cites_readme_and_source(self):
        self.assertEqual(len(self.fixtures), 11)
        self.assertEqual(self.fixtures[-1]["id"], self.FID)
        for cite in ("README.md:86", "README.md:258-280", ":277", "src/x402.js:140", "src/nano.js:293-311",
                     "package.json:3"):
            self.assertIn(cite, self.fx["source"])

    def test_fixture_is_what_build_offer_emits(self):
        doc = self.header_doc()
        self.assertEqual(doc["x402Version"], 2)
        self.assertEqual(sorted(doc["resource"]), ["description", "mimeType", "url"])  # x402.js:236-240
        self.assertEqual([a["network"] for a in doc["accepts"]], ["eip155:8453", "eip155:137", "eip155:1", "nano"])
        for a in doc["accepts"]:  # paymentRequiredHeader keeps exactly these keys (x402.js:241-249)
            self.assertEqual(sorted(a), ["amount", "asset", "extra", "maxTimeoutSeconds", "network", "payTo",
                                         "scheme"])
        xno = doc["accepts"][-1]
        self.assertEqual(sorted(xno["extra"]), ["binding", "decimals", "orderId"])  # x402.js:140
        self.assertEqual((xno["extra"]["binding"], xno["extra"]["decimals"], xno["asset"]),
                         ("xno-binding/v1/rep", 30, "XNO"))
        self.assertEqual(xno["amount"], "125" + "0" * 28)  # xnoRaw(100 cents, rate 0.8) = 1.25 XNO
        # the body is a second offer() call (index.js:334/:344 vs :378): same terms, its own orderId
        bx = self.fx["body"]["accepts"][-1]["extra"]
        self.assertNotEqual(bx["orderId"], xno["extra"]["orderId"])
        for oid in (bx["orderId"], xno["extra"]["orderId"]):
            self.assertRegex(oid, r"^[A-Za-z0-9_-]{22}$")  # newOrderId: 16 bytes base64url (nano.js:170-176)

    def test_dialect_is_rep_binding(self):
        v = self.v()
        self.assertEqual((v["dialect"], v["where"], v["x402Version"]), ("rep-binding", "header:PAYMENT-REQUIRED", 2))
        self.assertEqual([a.get("binding") for a in v["accepts"]], [None, None, None, "xno-binding/v1/rep"])
        self.assertEqual(self.fx["expect"]["dialect"], "rep-binding")
        # the body alone reads the same
        self.assertEqual(self.v(headers={})["dialect"], "rep-binding")

    def test_each_client_verdict(self):
        got = self.v()["payable_by"]
        self.assertEqual(got, {
            "nano-pay": "no:binding",  # nano-prefix network rule reaches the XNO accept; it signs no binding
            "kilkelly-mcp": "no:network",  # needs "nano:mainnet" exactly; the gateway says "nano"
            "kilkelly-mcp+extra": "no:network",
            "x402-dotnet-client": "no:network",  # header, v2 and resource pass; network then fails
            W: "no:where",  # reads only an MCP tool result
            self.W2N: "no:where",
            BP: "yes",  # ours: plans the bound XNO accept (GUIDE 2026-11-22T12:50Z)
        })
        # before the 7th row no client paid it; now ours does and no other count moves
        self.assertEqual(cf.count_payable([self.v()]), {k: (1 if k == BP else 0) for k in got})

    def test_binding_is_what_stops_each_client_on_nano_mainnet(self):
        # were the gateway to name the network "nano:mainnet", every HTTP client would reach the binding
        doc = self.header_doc()
        doc["accepts"][-1]["network"] = "nano:mainnet"
        got = self.v(headers={"PAYMENT-REQUIRED": b64(doc)})["payable_by"]
        for k in ("nano-pay", "kilkelly-mcp", "kilkelly-mcp+extra", "x402-dotnet-client"):
            self.assertEqual(got[k], "no:binding", k)

    def test_a_client_listing_the_binding_passes_it(self):
        row = dict(CLIENTS["nano-pay"], bindings=["xno-binding/v1/rep"], cap_raw=None)
        got = self.v(clients={"rep-signer": row})["payable_by"]["rep-signer"]
        self.assertEqual(got, "yes")

    def test_detection_needs_binding_and_order_id(self):
        base = accept(extra=False)
        for extra, want in (({"binding": "xno-binding/v1/rep", "orderId": "A" * 22}, "rep-binding"),
                            ({"binding": "xno-binding/v1/rep", "orderId": "A" * 21}, "exact"),
                            ({"binding": "xno-binding/v1/rep", "orderId": "A" * 22 + "!"}, "exact"),
                            ({"binding": "xno-binding/v1/rep"}, "exact"),
                            ({"orderId": "A" * 22}, "exact"),
                            ({"binding": "xno-binding/v1/other", "orderId": "A" * 22}, "exact"),
                            ({"binding": "xno-binding/v1/rep", "orderId": 5}, "exact")):
            a = dict(base, extra=extra)
            v = cf.verdicts({}, {"accepts": [a]}, CLIENTS)
            self.assertEqual(v["dialect"], want, extra)
            self.assertEqual(v["payable_by"]["nano-pay"], "no:binding" if want == "rep-binding" else "yes", extra)
        # a non-exact scheme carrying the pair is not this dialect
        a = dict(base, scheme="nano-send-hash", extra={"binding": "xno-binding/v1/rep", "orderId": "A" * 22})
        self.assertNotEqual(cf.verdicts({}, {"accepts": [a]}, CLIENTS)["dialect"], "rep-binding")

    def test_unbound_accept_normalises_as_before(self):
        a = cf.parse_402({}, {"accepts": [accept()]})["accepts"][0]
        self.assertNotIn("binding", a)

    def test_ten_old_fixture_verdicts_unchanged(self):
        old = [x for x in self.fixtures if x["id"] != self.FID]
        self.assertEqual([x["id"] for x in old], list(self.OLD))
        for x in old:
            v = cf.verdicts(x["headers"], x["body"], self.allc)
            self.assertEqual((v["dialect"],) + tuple(v["payable_by"][k] for k in self.ORDER), self.OLD[x["id"]],
                             x["id"])
            for case in x.get("expect_buyer", []):
                got = cf.verdicts(x["headers"], x["body"], self.allc, case["buyer"])["payable_by"]
                self.assertEqual(got[case["client"]], case["verdict"], case)

    def test_multi_accept_reason_is_the_own_chain_accept(self):
        usdc = {"scheme": "exact", "network": "eip155:8453", "asset": "0xabc", "amount": "1000000",
                "payTo": "0x0000000000000000000000000000000000000000"}
        v = cf.verdicts({}, {"accepts": [usdc, accept(amount="9" * 40)]}, CLIENTS)["payable_by"]
        self.assertEqual(v["nano-pay"], "no:cap")  # the XNO accept's reason, not the USDC one's no:network
        v = cf.verdicts({}, {"accepts": [usdc]}, CLIENTS)["payable_by"]
        self.assertEqual(v["nano-pay"], "no:network")  # no accept on its chain: the first accept's reason


class BuyerPlanRow(unittest.TestCase):
    """The 7th row, ours (expert GUIDE 2026-11-22T12:50Z): the buyer_plan planner, which is not in this
    repository. Its row is judged by client_fit's own rules; the check that each verdict equals what the
    planner really plans runs where the planner lives. Adding the row moves no other row."""

    WANT = {"feeless402": "yes", "busyman-probe": "yes", "cedarproof-diagnose": "yes",
            "opscontrol-page-extract": "yes", "noxid-nano-echo": "yes", "pururin-sequence": "yes",
            "pinnacle-url-check": "yes", "nanswap-nodes": "yes",
            "xmcp-65be4ee": "no:network",  # v1 network "nano", unbound: the planner's default MCP profile refuses it
            "xmcp-e3fcfca-v2": "yes", "x402-gateway-0.18.2-rep": "yes"}

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "client_fit_fixtures.json")) as f:
            cls.fixtures = json.load(f)
        cls.allc = cf.load_clients(include_pending=True)

    def test_seventh_row_listed_and_ours(self):
        self.assertNotIn(BP, CLIENTS)  # not published: `pending`, so never counted as installable here
        self.assertIn("pending", self.allc[BP])
        self.assertEqual(len(self.allc), 7)
        self.assertEqual([k for k, v in self.allc.items() if v.get("ours")], [BP])
        self.assertEqual(self.allc[BP]["bindings"], ["xno-binding/v1/rep"])

    def test_eleven_verdicts(self):
        got = {fx["id"]: cf.verdicts(fx["headers"], fx["body"], self.allc)["payable_by"][BP] for fx in self.fixtures}
        self.assertEqual(got, self.WANT)

    def test_rep_fixture_yes_only_with_the_seventh_row(self):
        # FAILS without buyer_plan in clients.json: before, no row read `yes` on the bound quote
        fx = [x for x in self.fixtures if x["id"] == "x402-gateway-0.18.2-rep"][0]
        yes = [k for k, v in cf.verdicts(fx["headers"], fx["body"], self.allc)["payable_by"].items() if v == "yes"]
        self.assertEqual(yes, [BP])

    def test_other_six_unchanged_without_the_row(self):
        six = {k: v for k, v in self.allc.items() if k != BP}
        self.assertEqual(len(six), 6)
        for fx in self.fixtures:
            a = cf.verdicts(fx["headers"], fx["body"], self.allc)["payable_by"]
            b = cf.verdicts(fx["headers"], fx["body"], six)["payable_by"]
            self.assertEqual({k: a[k] for k in six}, b, fx["id"])

    def test_account_from_key_round_trips_the_checksum(self):
        self.assertEqual(cf.account_from_key(bytes(32)),
                         "nano_1111111111111111111111111111111111111111111111111111hifc8npp")  # nano.test.js:25
        self.assertTrue(cf.nano_checksum_ok(cf.account_from_key(bytes(range(32)))))
        bits = "".join(format(cf.ALPHABET.index(c), "05b") for c in GOOD[5:])
        self.assertEqual(cf.account_from_key(int(bits[4:260], 2).to_bytes(32, "big")), GOOD)


if __name__ == "__main__":
    unittest.main()
