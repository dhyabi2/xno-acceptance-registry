import json, os, sys, unittest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import board, nanoaddr


class T(unittest.TestCase):
    def setUp(self):
        self.b = json.load(open(os.path.join(HERE, "board.json")))

    def test_every_row_address_passes_the_nano_checksum(self):
        for s in self.b["sellers"]:
            self.assertTrue(nanoaddr.is_valid(s["address"]), s["name"])

    def test_every_row_quotes_where_it_was_said(self):
        for s in self.b["sellers"]:
            self.assertTrue(s["source"].strip() and s["price"].strip(), s["name"])

    def test_render_without_nodes_says_not_re_read_and_makes_no_network_call(self):
        md = board.render(self.b, [])
        self.assertIn("not re-read", md)
        self.assertIn(self.b["sellers"][0]["address"], md)

    def test_ledger_note_is_printed_so_our_own_send_is_not_read_as_a_buyer(self):
        rows = [s for s in self.b["sellers"] if s.get("ledger_note")]
        self.assertTrue(rows)
        md = board.render({"sellers": rows, "notes": []}, [])
        for s in rows:
            self.assertIn(s["ledger_note"], md)

    def test_unopened_account_is_not_called_empty(self):
        orig = board.rpc
        board.rpc = lambda n, body: {"error": "Account not found"}
        try:
            self.assertEqual(board.state(self.b["sellers"][0]["address"], ["x"])["opened"], False)
        finally:
            board.rpc = orig


if __name__ == "__main__":
    unittest.main()
