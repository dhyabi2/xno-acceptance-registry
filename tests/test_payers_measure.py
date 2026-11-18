import io, json, os, sys, tempfile, types, unittest
from contextlib import redirect_stderr, redirect_stdout
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import payers_measure as pm

PAYEE = "nano_3z335ug5oz6sxfgcfz3kdqdrgn5otx7ht3epuc3kuimka6hc59xqem1jrzqy"
A = "nano_1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
B = "nano_1bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def recv(acct, amt=10 ** 27, ts=1):
    return {"type": "receive", "account": acct, "amount": str(amt), "local_timestamp": str(ts), "confirmed": "true"}


class T(unittest.TestCase):
    def run_payee(self, post_json):
        fake = types.ModuleType("nano_settlement_verify")
        fake.post_json = post_json
        saved = sys.modules.get("nano_settlement_verify"), pm.PAUSE_S, pm.time.sleep
        sys.modules["nano_settlement_verify"] = fake
        pm.PAUSE_S = 0
        pm.time.sleep = lambda s: None
        try:
            with tempfile.TemporaryDirectory() as d:
                out, reg = os.path.join(d, "o.json"), os.path.join(d, "registry.json")
                with open(reg, "w") as f:
                    json.dump(dict(entries=[]), f)
                err, so = io.StringIO(), io.StringIO()
                with redirect_stderr(err), redirect_stdout(so):
                    code = pm.main(["--verify-dir", d, "--registry", reg, "--out", out,
                                    "--payee", PAYEE, "--label", "t", "--node", "http://n1", "--node", "http://n2"])
                return code, json.load(open(out)), err.getvalue()
        finally:
            if saved[0] is None:
                sys.modules.pop("nano_settlement_verify", None)
            else:
                sys.modules["nano_settlement_verify"] = saved[0]
            pm.PAUSE_S, pm.time.sleep = saved[1], saved[2]

    def test_every_node_failing_is_unread_not_zero(self):
        calls = []

        def post_json(url, payload):
            calls.append(url)
            raise OSError("Tunnel connection failed: 403 Forbidden")
        code, res, err = self.run_payee(post_json)
        self.assertEqual(code, 2)
        self.assertEqual(set(calls), {"http://n1", "http://n2"})   # --node replaced NODES
        self.assertFalse(res["payees"][PAYEE]["history_read"])
        self.assertFalse(res["summary"][PAYEE]["history_read"])
        self.assertIsNone(res["summary"][PAYEE]["distinct_payers"])
        self.assertIn("UNREAD " + PAYEE + " t ", err)
        self.assertIn("403", err)
        self.assertNotIn("payers 0", err)

    def test_node_error_reply_is_unread(self):
        code, res, err = self.run_payee(lambda url, p: {"error": "Too many requests"})
        self.assertEqual(code, 2)
        self.assertIn("Too many requests", err)

    def test_unopened_account_is_a_real_zero(self):
        code, res, err = self.run_payee(lambda url, p: {"error": "Account not found"})
        self.assertEqual(code, 0)
        self.assertTrue(res["payees"][PAYEE]["history_read"])
        self.assertEqual(res["summary"][PAYEE]["distinct_payers"], 0)

    def test_fake_history_counts_payers(self):
        def post_json(url, payload):
            if payload["action"] == "account_history":
                return {"history": [recv(A, ts=1), recv(B, ts=2), recv(A, ts=3)]}
            return {"error": "Account not found"}
        code, res, err = self.run_payee(post_json)
        self.assertEqual(code, 0)
        s = res["summary"][PAYEE]
        self.assertTrue(s["history_read"])
        self.assertEqual(s["distinct_payers"], 2)
        self.assertEqual(s["repeat_payers_any_amount"], 1)
        self.assertNotIn("UNREAD", err)


if __name__ == "__main__":
    unittest.main()
