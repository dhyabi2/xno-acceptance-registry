import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import buyer_wants as b

GOOD = "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"


def want(**kw):
    w = {"id": "x", "status": "open", "buyer": "B", "wants": "a brief", "amount_raw": str(10 ** 30 // 1000),
         "expires": "2999-01-01", "buyer_account": GOOD, "funded": True, "funded_note": "balance read 2026-11-02 by owner",
         "ask_url": "https://example.org/ask/1"}
    w.update(kw)
    return w


class T(unittest.TestCase):
    def test_checksum(self):
        self.assertTrue(b.address_ok(GOOD))
        self.assertFalse(b.address_ok(GOOD[:-1] + ("1" if GOOD[-1] != "1" else "3")))
        self.assertFalse(b.address_ok("nano_bad"))

    def test_good_want_passes(self):
        self.assertEqual(b.problems(want()), [])

    def test_open_without_funding_or_account_or_expired_is_refused(self):
        self.assertTrue(b.problems(want(funded=False)))
        self.assertTrue(b.problems(want(funded_note="")))
        self.assertTrue(b.problems(want(buyer_account="nano_x")))
        self.assertTrue(b.problems(want(expires="2000-01-01")))
        self.assertTrue(b.problems(want(ask_url="http://x")))

    def test_amount_is_integer_raw_in_band(self):
        self.assertTrue(b.problems(want(amount_raw="0.5")))
        self.assertTrue(b.problems(want(amount_raw="1")))
        self.assertTrue(b.problems(want(amount_raw=str(101 * 10 ** 30))))
        self.assertEqual(b.xno(10 ** 30 // 1000), "0.001")

    def test_template_is_never_an_offer(self):
        t = json.load(open(os.path.join(ROOT, "wants", "TEMPLATE.json")))
        self.assertEqual(b.problems(t), [])
        self.assertIn("None open", b.render([t]))

    def test_render_and_dm_use_exact_amount(self):
        out = b.render([want()])
        self.assertIn("| B | 0.001 |", out)
        self.assertIn("0.001 XNO", b.dm(want(), "Vera"))

    def test_cli_exit_code(self):
        p = os.path.join(ROOT, "wants", "TEMPLATE.json")
        self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "buyer_wants.py"), "validate", p]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
