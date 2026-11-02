import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import request_count as rc


def issue(n, login, url, labels=("wanted-in-xno",), typ="User"):
    return {"number": n, "html_url": "https://github.com/x/y/issues/%d" % n, "user": {"login": login, "type": typ},
            "labels": [{"name": l} for l in labels], "body": "### Seller URL\n\n%s\n\n### What you would buy\n\nx" % url}


class T(unittest.TestCase):
    def test_distinct_accounts_per_seller_host(self):
        iss = [issue(1, "alice", "https://www.Seller.example/api"), issue(2, "alice", "seller.example"),
               issue(3, "bob", "https://other.example")]
        react = {1: [{"content": "+1", "user": {"login": "carol"}}, {"content": "+1", "user": {"login": "bob"}},
                     {"content": "heart", "user": {"login": "dave"}}], 2: [], 3: []}
        c = rc.count(iss, lambda n: react[n])
        self.assertEqual(c["seller.example"]["distinct_requesters"], 3)   # alice once, carol, bob; heart is not a +1
        self.assertEqual(c["other.example"]["distinct_requesters"], 1)

    def test_own_account_bots_and_other_labels_are_not_counted(self):
        iss = [issue(1, "dhyabi2", "https://s.example"), issue(2, "robot[bot]", "https://s.example"),
               issue(3, "eve", "https://s.example", labels=("bug",)), issue(4, "zed", "https://s.example", typ="Bot")]
        c = rc.count(iss, lambda n: [])
        self.assertEqual(c["s.example"]["distinct_requesters"], 0)

    def test_nothing_is_seeded(self):
        self.assertIn("Count today: **0** across **0** sellers", rc.render({}))
        self.assertEqual(rc.count([], lambda n: []), {})

    def test_issue_without_a_seller_url_is_ignored(self):
        i = issue(1, "a", "x"); i["body"] = "I want it"
        self.assertEqual(rc.count([i], lambda n: []), {})


if __name__ == "__main__":
    unittest.main()
