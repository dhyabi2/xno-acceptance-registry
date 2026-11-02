import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import demand_register as dr

CONV = json.dumps({"exchange": [{"speaker": "x", "text": "I would pay Acme in XNO if it took it"}]})
fetch = lambda reg, name, local=None: CONV


def reg(requests=(), gates=()):
    return {"threshold": 3, "conversations_base": "x", "requests": list(requests), "gates": list(gates)}


def req(who, host="acme.example", quote="I would pay Acme in XNO if it took it"):
    return {"requester": who, "host": host, "quote": quote, "conversation": "c.json"}


class T(unittest.TestCase):
    def test_empty_register_says_zero(self):
        self.assertIn("**0** distinct requesters across **0** sellers", dr.render(reg()))

    def test_quote_must_exist_verbatim(self):
        self.assertEqual(dr.validate(reg([req("a")]), fetch=fetch), [])
        p = dr.validate(reg([req("a", quote="invented words")]), fetch=fetch)
        self.assertTrue(p and "not found verbatim" in p[0])

    def test_own_accounts_refused_and_not_counted(self):
        r = reg([req("Unstuck")])
        self.assertTrue(any("our own" in x for x in dr.validate(r, fetch=fetch)))
        self.assertEqual(dr.counts(r), {})

    def test_one_requester_counts_once_per_host(self):
        self.assertEqual(dr.counts(reg([req("a"), req("A"), req("b")])), {"acme.example": 2})

    def test_gate_needs_threshold(self):
        r = reg([req("a"), req("b")])
        self.assertEqual(dr.counts(r)["acme.example"], 2)
        r["requests"].append(req("c"))
        self.assertEqual(dr.counts(r)["acme.example"], 3)

    def test_shipped_register_is_valid_shape_and_gate_closed(self):
        r = dr.load()
        self.assertEqual(dr.counts(r).get("apexfaucet.xyz", 0), 0)
        self.assertEqual(r["requests"], [])

if __name__ == "__main__":
    unittest.main()
