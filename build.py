#!/usr/bin/env python3
"""Build registry.json: pursekeeper's seller list + extras, each probed live (one UNPAID request,
nothing is paid), every payTo checksum-validated here. Usage:
  python3 build.py data/pursekeeper-sellers-<date>.json extras.json registry.json
stdlib only."""
import json, sys, datetime
import probe, nanoaddr
from concurrent.futures import ThreadPoolExecutor
PAYTO_KEYS = ('payto', 'pay_to', 'nano_address', 'x-nano-payto')
def payto_of(r):
    seen = {}
    for p in r.get('address_paths', []):
        last = p['path'].rsplit('/', 1)[-1].lower()
        if last in PAYTO_KEYS:
            seen[p['address']] = nanoaddr.is_valid(p['address'])
    return [{'address': a, 'checksum_valid': v} for a, v in seen.items()]
def state(s, r):
    if r.get('door') == 'mail': return 'mail_only', 'contact by mail; not probed'
    st = r.get('http_status')
    if st is None: return 'dead', 'no HTTP answer: ' + r.get('error', '')[:80]
    if 'DEPLOYMENT_DISABLED' in r.get('body_head', ''): return 'dead', 'Vercel deployment disabled'
    if r.get('expect') and st == r['expect'] and st != 402: return 'live_status_route', 'status route answered %d as the seller declared; Nano payTo not read by us' % st
    if r.get('payment_required_header') is None and st == 402 and not r.get('mentions_nano'):
        return 'dead' if 'DEPLOYMENT_DISABLED' in json.dumps(r) else 'unclear', '402 without any Nano mention'
    if st == 402 and r.get('mentions_nano'): return 'live_402_nano', 'answered 402 and mentions Nano'
    if st == 200 and r.get('address_paths'): return 'live_free_tier', '200 with a Nano payTo (first call free or open route)'
    if st >= 500 or st == 404: return 'dead', 'HTTP %d on the probe route' % st
    return 'unclear', 'HTTP %d on our probe; route or method may differ from the seller declared' % st
def main(src, extras, out):
    d = json.load(open(src)); ex_all = json.load(open(extras))
    statics = [x for x in ex_all if x.get('static')]; sellers = d['sellers'] + [x for x in ex_all if not x.get('static')]
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(probe.probe, sellers))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    rows = []
    for s, r in zip(sellers, res):
        stt, why = state(s, r); pt = payto_of(r)
        nets = sorted({n.get('network') for n in r.get('nano_accepts', []) if n.get('network')})
        raws = sorted({str(n.get('amount') or n.get('maxAmountRequired')) for n in r.get('nano_accepts', []) if (n.get('amount') or n.get('maxAmountRequired'))})
        rows.append({
          'id': s['id'], 'name': s.get('name'), 'operator': s.get('operator'), 'what': s.get('what'),
          'endpoint': s['endpoint'], 'price_quoted_by_operator': s.get('price'),
          'price_raw_seen_in_402': raws or None, 'networks_seen': nets or None,
          'payto': pt, 'payto_all_checksum_valid': bool(pt) and all(p['valid'] if 'valid' in p else p['checksum_valid'] for p in pt),
          'payto_note': 'per-payment deposit address; moves per quote' if s['id'] == 'nanogpt' else None,
          'state_today': stt, 'state_reason': why, 'probe': {'http_status': r.get('http_status'), 'ms': r.get('ms'), 'at': now},
          'evidence': ('endpoint_read' if pt and r.get('http_status') in (200, 402) else 'unverified'),
          'listed_by': s.get('listed_by', 'pursekeeper.dev/sellers.json'),
          'paid_verification_by_listing_party': s.get('verified'),
          'note': s.get('note')})
    import urllib.request
    for s in statics:
        try: st = urllib.request.urlopen(urllib.request.Request(s['endpoint'], headers={'User-Agent': 'xno-acceptance-registry/0.1'}), timeout=20); code = st.status; page = st.read(400000).decode('utf-8', 'replace')
        except Exception as ex_: code, page = None, ''
        ok = code == 200 and s['payto_address'] in page
        rows.append({'id': s['id'], 'name': None, 'operator': s['operator'], 'what': s['what'], 'endpoint': s['endpoint'],
          'price_quoted_by_operator': s['price_quoted_by_operator'], 'price_raw_seen_in_402': None, 'networks_seen': None,
          'payto': [{'address': s['payto_address'], 'checksum_valid': nanoaddr.is_valid(s['payto_address'])}],
          'payto_all_checksum_valid': nanoaddr.is_valid(s['payto_address']), 'payto_note': None,
          'state_today': 'live_portal' if ok else 'dead', 'state_reason': 'portal answered 200 and prints the address' if ok else 'portal did not answer 200 with the address',
          'probe': {'http_status': code, 'ms': None, 'at': now}, 'evidence': 'operator_statement_plus_portal' if ok else 'unverified',
          'listed_by': s['listed_by'], 'paid_verification_by_listing_party': None, 'note': s['note']})
    reg = {'schema': 1, 'generated_at': now, 'probe_method': 'one unpaid request per endpoint (method/body as the seller declared); no payment is made; payTo checksum computed here',
           'counts': {k: sum(1 for x in rows if x['state_today'] == k) for k in sorted({x['state_today'] for x in rows})}, 'entries': rows}
    reg['counts']['total'] = len(rows)
    json.dump(reg, open(out, 'w'), indent=1, ensure_ascii=False); print(reg['counts'], len(rows))
if __name__ == '__main__': main(*sys.argv[1:4])
