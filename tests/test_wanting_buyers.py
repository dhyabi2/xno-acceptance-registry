import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class T(unittest.TestCase):
    def test_every_seller_has_source_and_no_door_claim(self):
        w = json.load(open(os.path.join(ROOT, "sellers-wanting-buyers.json")))
        self.assertTrue(w["sellers"])
        for s in w["sellers"]:
            self.assertTrue(s["source"].startswith("https://github.com/dhyabi2/agent-conversations/"))
            self.assertIs(s["xno_door"], False)

    def test_markdown_is_generated_from_the_json(self):
        subprocess.run([sys.executable, "wanting_buyers.py"], cwd=ROOT, check=True, capture_output=True)
        md = open(os.path.join(ROOT, "WANTING-BUYERS.md")).read()
        for s in json.load(open(os.path.join(ROOT, "sellers-wanting-buyers.json")))["sellers"]:
            self.assertIn(s["agent"], md)


if __name__ == "__main__":
    unittest.main()
