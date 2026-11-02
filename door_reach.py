#!/usr/bin/env python3
"""Is each listed seller's door reachable by a plain non-browser client? ONE unpaid request per door; pays nothing.
Records HTTP status, the server header, Cloudflare markers (cf-ray, cf-mitigated) and whether the body is a challenge page.
A challenge or 403 from a Cloudflare-proxied door means a client without a browser fingerprint may never see the 402.
This client is Python urllib (one fingerprint); pursekeeper saw the same split between curl and Node fetch, so a
different client can get a different answer: read this as one client's view, not as proof of unreachability.
  python3 door_reach.py out.json"""
import json, sys, time, urllib.request, urllib.error, datetime
reg = json.load(open('registry.json'))['entries']
sell = json.load(open('data/pursekeeper-sellers-2026-11-02.json'))
sell = sell['sellers'] if isinstance(sell, dict) and 'sellers' in sell else sell
probes = {s['id']: (s.get('probe') or {}) for s in sell}
rows = []
for e in reg:
    if e.get('state_today') not in ('live_402_nano', 'live_portal', 'live_status_route') or not str(e.get('endpoint', '')).startswith('http'):
        continue
    p = probes.get(e['id'], {})
    body = p.get('body'); hdr = dict(p.get('headers') or {}); hdr.setdefault('User-Agent', 'door-reach/0.1 (read-only, one unpaid request)')
    req = urllib.request.Request(p.get('url') or e['endpoint'], data=body.encode() if body else None, headers=hdr, method=p.get('method', 'GET'))
    row = {'id': e['id'], 'endpoint': e['endpoint']}
    try:
        r = urllib.request.urlopen(req, timeout=20); st = r.status; raw = r.read(20000); h = {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as ex:
        st = ex.code; raw = ex.read(20000); h = {k.lower(): v for k, v in ex.headers.items()}
    except Exception as ex:
        row['error'] = type(ex).__name__; rows.append(row); time.sleep(1); continue
    txt = raw.decode('utf-8', 'replace').lower()
    row.update(http_status=st, server=h.get('server'), cloudflare=('cf-ray' in h or 'cloudflare' in (h.get('server') or '').lower()),
               cf_mitigated=h.get('cf-mitigated'), challenge_page=('just a moment' in txt or 'cf-chl' in txt or 'challenge-platform' in txt))
    rows.append(row); time.sleep(1.5)
out = {'read_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'doors': len(rows),
       'cloudflare': sum(1 for r in rows if r.get('cloudflare')), 'cloudflare_answered_402': sum(1 for r in rows if r.get('cloudflare') and r.get('http_status') == 402),
       'challenged': [r['id'] for r in rows if r.get('cf_mitigated') or r.get('challenge_page')], 'errors': [r['id'] for r in rows if r.get('error')], 'rows': rows}
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print({k: v for k, v in out.items() if k != 'rows'})
