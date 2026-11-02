#!/usr/bin/env python3
"""Derive directory-ready feeds from registry.json: only entries that answered live today with a
checksum-valid Nano payTo. Writes feeds/nano-sellers.json (x402-style accepts) and feeds/nano-sellers.csv."""
import json, csv, os, sys
reg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'registry.json'))
os.makedirs('feeds', exist_ok=True)
out = []
for e in reg['entries']:
    if e['state_today'] not in ('live_402_nano', 'live_portal') or not e['payto_all_checksum_valid']: continue
    out.append({'id': e['id'], 'name': e['name'] or e['id'], 'operator': e['operator'], 'description': e['what'], 'resource': e['endpoint'],
      'accepts': [{'scheme': 'exact', 'network': 'nano:mainnet', 'asset': 'XNO', 'payTo': p['address']} for p in e['payto']] if e['id'] != 'nanogpt' else [{'scheme': 'exact', 'network': 'nano:mainnet', 'asset': 'XNO', 'payTo': 'per-payment (read it from the 402)'}],
      'price_quoted_by_operator': e['price_quoted_by_operator'], 'price_raw_seen_in_402': e['price_raw_seen_in_402'], 'last_probed': e['probe']['at'], 'evidence': e['evidence']})
json.dump({'generated_at': reg['generated_at'], 'source': 'https://github.com/dhyabi2/xno-acceptance-registry', 'note': 'live-today entries only; CC0', 'count': len(out), 'services': out}, open('feeds/nano-sellers.json', 'w'), indent=1, ensure_ascii=False)
with open('feeds/nano-sellers.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['id', 'resource', 'network', 'payTo', 'price_quoted_by_operator', 'last_probed'])
    for s in out:
        for a in s['accepts']: w.writerow([s['id'], s['resource'], a['network'], a['payTo'], s['price_quoted_by_operator'], s['last_probed']])
print(len(out))
