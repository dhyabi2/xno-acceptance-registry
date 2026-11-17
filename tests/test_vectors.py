import base64, copy, hashlib, io, json, os, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from urllib.parse import urlparse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import nanoaddr
import vector_check as vc

VEC_PATH = os.path.join(ROOT, "vectors", "nano-exact-v1.json")
BURN = "nano_1111111111111111111111111111111111111111111111111111hifc8npp"
# Freeze guard: these literals pin v1. Editing the vector fails here; a change is nano-exact-v2.json, never an edit.
PINNED_BODY_SHA256 = "5860ad53e0c7eb09de81bc4c5cdebe6a17090583f47671cdb64cd822d2994ca2"
PINNED_REQUEST_BODY_SHA256 = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
# nanogpt shape (registry.json: recorded payTo and raw amount; its payTo moves per quote)
NANOGPT = {"accepts": [{"amount": "4020000000000000000000000", "asset": "XNO", "maxTimeoutSeconds": 300,
                        "network": "nano:mainnet",
                        "payTo": "nano_14r6q7get5jm99jpiski4y53tne6hxwi7c3n65ncabi9jmygp353o5zrqhhg",
                        "scheme": "exact"}], "error": "payment required", "x402Version": 2}


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


class T(unittest.TestCase):
    def setUp(self):
        with open(VEC_PATH, "rb") as f:
            self.raw_vec = f.read()
        self.vec = json.loads(self.raw_vec)
        self.body = self.vec["response"]["body"].encode("utf-8")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = os.path.join(self.tmp.name, name)
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        return p

    def run_cli(self, observed, *extra, vector=VEC_PATH):
        out = io.StringIO()
        with redirect_stdout(out):
            code = vc.main(["--vector", vector, "--observed", observed] + list(extra))
        return code, json.loads(out.getvalue())

    # 1. file, hashes, header
    def test_hashes_recompute(self):
        self.assertEqual(hashlib.sha256(self.body).hexdigest(), self.vec["response"]["body_sha256"])
        self.assertEqual(hashlib.sha256(self.vec["request"]["body"].encode()).hexdigest(),
                         self.vec["request"]["body_sha256"])
        self.assertEqual(base64.b64decode(self.vec["response"]["header_payment_required_b64"]), self.body)

    def test_file_is_canonical(self):
        self.assertEqual(self.raw_vec, (json.dumps(self.vec, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
        self.assertEqual(self.body, canon(json.loads(self.body)))

    # 6. freeze guard
    def test_freeze_guard(self):
        self.assertEqual(self.vec["status"], "frozen")
        self.assertEqual(self.vec["response"]["body_sha256"], PINNED_BODY_SHA256)
        self.assertEqual(self.vec["request"]["body_sha256"], PINNED_REQUEST_BODY_SHA256)

    # 2. unpayable by construction
    def test_burn_address_unpayable(self):
        e = self.vec["expected_fields"]
        self.assertEqual(e["payTo"], BURN)
        self.assertTrue(nanoaddr.is_valid(BURN))
        self.assertEqual(nanoaddr.decode(BURN), bytes(32))
        self.assertIs(self.vec["payable"], False)
        self.assertTrue(urlparse(self.vec["request"]["url"]).hostname.endswith(".invalid"))
        entry = json.loads(self.body)["accepts"][0]
        self.assertEqual((entry["payTo"], entry["amount"]), (e["payTo"], e["amount_raw"]))

    # 3. self-check, both forms
    def test_self_check_body(self):
        code, r = self.run_cli(self.write("body.json", self.body))
        self.assertEqual(code, 0, r)
        self.assertTrue(r["byte_identical"])
        self.assertEqual(r["observed_sha256"], PINNED_BODY_SHA256)
        self.assertEqual(set(r["structural"].values()), {"match"})
        self.assertTrue(r["payTo_checksum_valid"])
        self.assertEqual(r["outcome"], "observed")
        self.assertEqual(r["challenge"]["pay_to"], BURN)

    def test_self_check_header_form(self):
        hdr = self.vec["response"]["header_payment_required_b64"]
        for data in (hdr, hdr + "\n", "PAYMENT-REQUIRED: " + hdr):
            code, r = self.run_cli(self.write("hdr.txt", data), "--parser-client", "x", "--parser-version", "1")
            self.assertEqual(code, 0, r)
            self.assertEqual(r["observed_form"], "header_b64")
            self.assertTrue(r["byte_identical"])
            self.assertEqual(r["parser_profile"], {"client": "x", "client_version": "1"})

    def test_subprocess_exit_codes(self):
        ok = subprocess.run([sys.executable, os.path.join(ROOT, "vector_check.py"), "--vector", VEC_PATH,
                             "--observed", self.write("b.json", self.body)], capture_output=True)
        self.assertEqual(ok.returncode, 0)
        self.assertTrue(json.loads(ok.stdout)["byte_identical"])
        bad = subprocess.run([sys.executable, os.path.join(ROOT, "vector_check.py"), "--vector", VEC_PATH,
                              "--observed", self.write("g.txt", "not json at all")], capture_output=True)
        self.assertEqual(bad.returncode, 2)

    # mutations -> 1
    def test_mutated_payto_or_amount(self):
        doc = json.loads(self.body)
        for field, value in (("payTo", NANOGPT["accepts"][0]["payTo"]), ("amount", "2000000000000000000000000")):
            m = copy.deepcopy(doc); m["accepts"][0][field] = value
            code, r = self.run_cli(self.write("m.json", canon(m)))
            self.assertEqual(code, 1, r)
            self.assertFalse(r["byte_identical"])
            self.assertEqual(r["structural"]["payTo" if field == "payTo" else "amount_raw"], "differs")

    def test_reformatted_body_is_not_byte_identical(self):
        code, r = self.run_cli(self.write("pretty.json", json.dumps(json.loads(self.body), indent=2)))
        self.assertEqual(code, 1)
        self.assertFalse(r["byte_identical"])
        self.assertEqual(set(r["structural"].values()), {"match"})
        code, r = self.run_cli(self.write("pretty.json", json.dumps(json.loads(self.body), indent=2)), "--structure-only")
        self.assertEqual(code, 0)

    # 4. real seller shape
    def test_nanogpt_fixture(self):
        p = self.write("nanogpt.json", canon(NANOGPT))
        code, r = self.run_cli(p, "--structure-only")
        self.assertEqual(code, 0, r)
        self.assertEqual(r["structural"]["amount_raw"], "differs")
        self.assertEqual(r["structural"]["payTo"], "differs")
        self.assertEqual(r["structural"]["scheme"], "match")
        code, r = self.run_cli(p)
        self.assertEqual(code, 1)
        hdr = self.write("nanogpt.b64", base64.b64encode(canon(NANOGPT)))
        self.assertEqual(self.run_cli(hdr, "--structure-only")[0], 0)

    def test_structure_only_still_fails_on_scheme(self):
        m = copy.deepcopy(NANOGPT); m["accepts"][0]["scheme"] = "upto"
        code, r = self.run_cli(self.write("s.json", canon(m)), "--structure-only")
        self.assertEqual(code, 1)
        self.assertEqual(r["structural"]["scheme"], "differs")

    # 5. error table
    def test_err_not_json(self):
        for junk in (b"\x00\xff garbage", b"<html>402</html>", base64.b64encode(b"not json")):
            code, r = self.run_cli(self.write("junk", junk))
            self.assertEqual((code, r["error"]), (2, "not_json"))

    def test_err_no_accepts(self):
        for doc in ({"x402Version": 2}, {"x402Version": 2, "accepts": []}, [1, 2]):
            code, r = self.run_cli(self.write("na.json", canon(doc)))
            self.assertEqual((code, r["error"]), (1, "no_accepts"))

    def test_err_no_nano_entry(self):
        doc = {"x402Version": 2, "accepts": [{"network": "eip155:8453", "scheme": "exact", "payTo": "0xabc"}]}
        code, r = self.run_cli(self.write("evm.json", canon(doc)))
        self.assertEqual((code, r["error"]), (1, "no_nano_entry"))

    def test_err_payto_checksum(self):
        m = json.loads(self.body); m["accepts"][0]["payTo"] = BURN[:-1] + "q"
        code, r = self.run_cli(self.write("ck.json", canon(m)), "--structure-only")
        self.assertEqual((code, r["error"]), (1, "payto_checksum"))
        self.assertFalse(r["payTo_checksum_valid"])

    def test_err_vector_corrupt(self):
        v = copy.deepcopy(self.vec); v["response"]["body"] = v["response"]["body"].replace("300", "301")
        code, r = self.run_cli(self.write("b.json", self.body), vector=self.write("v.json", json.dumps(v)))
        self.assertEqual((code, r["error"]), (2, "vector_corrupt"))

    def test_err_vector_not_frozen(self):
        v = copy.deepcopy(self.vec); v["status"] = "draft"
        code, r = self.run_cli(self.write("b.json", self.body), vector=self.write("v.json", json.dumps(v)))
        self.assertEqual((code, r["error"]), (2, "vector_not_frozen"))


if __name__ == "__main__":
    unittest.main()
