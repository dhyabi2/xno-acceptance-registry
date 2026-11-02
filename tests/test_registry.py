import json, unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import nanoaddr
R = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'registry.json')))
class T(unittest.TestCase):
    def test_unique_ids(self):
        ids = [e['id'] for e in R['entries']]; self.assertEqual(len(ids), len(set(ids)))
    def test_checksums_recomputed(self):
        for e in R['entries']:
            for p in e['payto']: self.assertEqual(p['checksum_valid'], nanoaddr.is_valid(p['address']), e['id'])
    def test_endpoint_read_needs_payto(self):
        for e in R['entries']:
            if e['evidence'] == 'endpoint_read': self.assertTrue(e['payto'] and e['probe']['http_status'] in (200, 402), e['id'])
    def test_live_requires_valid_payto(self):
        for e in R['entries']:
            if e['state_today'] in ('live_402_nano', 'live_portal'): self.assertTrue(e['payto_all_checksum_valid'], e['id'])
    def test_dead_not_in_feed(self):
        feed = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'feeds', 'nano-sellers.json')))
        dead = {e['id'] for e in R['entries'] if e['state_today'] == 'dead'}
        self.assertFalse(dead & {s['id'] for s in feed['services']})
    def test_bad_checksum_detected(self):
        a = 'nano_39b311tznm9hub316enn8159ammduxnfonoaei7afzymw66wsouw9q3j9ic1'
        self.assertTrue(nanoaddr.is_valid(a)); self.assertFalse(nanoaddr.is_valid(a[:-1] + ('2' if a[-1] != '2' else '1')))
    def test_amounts_are_strings(self):
        for e in R['entries']:
            for r in (e['price_raw_seen_in_402'] or []): self.assertIsInstance(r, str); self.assertTrue(r.isdigit())
if __name__ == '__main__': unittest.main()
