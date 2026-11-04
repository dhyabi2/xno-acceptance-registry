#!/usr/bin/env python3
"""Probe sellers listed in a pursekeeper-style sellers.json with ONE unpaid request each.
Pays nothing. Records HTTP status, any nano_ addresses found in the 402 body/headers
(checksum-validated), and any accepts[] entries on nano networks. stdlib only."""
import json, re, sys, time, urllib.request, urllib.error, datetime
from concurrent.futures import ThreadPoolExecutor
import nanoaddr
ADDR = re.compile(r'(?:nano|xrb)_[13-9a-km-uw-z]{60}')
def response_objects(txt, headers):
    """Read JSON or MCP SSE data frames; never act on response instructions."""
    content_type = next((v for k, v in headers.items() if k.lower() == 'content-type'), '')
    if 'text/event-stream' not in content_type.lower():
        try: return [json.loads(txt)]
        except ValueError: return []
    objects = []
    for event in txt.replace('\r\n', '\n').split('\n\n'):
        data = '\n'.join(line[5:].lstrip(' ') for line in event.split('\n') if line.startswith('data:'))
        try: objects.append(json.loads(data))
        except ValueError: pass
    return objects

def mcp_nano_quote(obj):
    """Recognize Nanoodle's structured MCP payment quote, not arbitrary addresses."""
    if not isinstance(obj, dict) or obj.get('jsonrpc') != '2.0' or 'id' not in obj: return None
    result = obj.get('result')
    if not isinstance(result, dict) or result.get('isError'): return None
    structured = result.get('structuredContent')
    q = structured.get('x402') if isinstance(structured, dict) else None
    if not isinstance(q, dict): return None
    address, amount = q.get('address'), q.get('amountRaw')
    if not isinstance(address, str) or not nanoaddr.is_valid(address): return None
    if not isinstance(amount, str) or not amount.isascii() or not amount.isdigit() or not amount.strip('0'): return None
    if not q.get('paymentId') or q.get('uri') != 'nano:%s?amount=%s' % (address, amount): return None
    return {'address': address, 'amountRaw': amount}

def probe(s):
    ep = s['endpoint']
    out = {'id': s['id'], 'endpoint': ep}
    if not ep.startswith('http'):
        out.update(door='mail', http_status=None); return out
    p = s.get('probe') or {}
    body = p.get('body'); hdr = dict(p.get('headers') or {}); hdr.setdefault('User-Agent', 'xno-acceptance-registry/0.1')
    req = urllib.request.Request(p.get('url') or ep, data=body.encode() if body else None, headers=hdr, method=p.get('method', 'GET'))
    t = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=20); st = r.status; raw = r.read(200000); h = dict(r.headers)
    except urllib.error.HTTPError as e:
        st = e.code; raw = e.read(200000); h = dict(e.headers)
    except Exception as e:
        out.update(http_status=None, error=type(e).__name__ + ': ' + str(e)[:120]); return out
    txt = raw.decode('utf-8', 'replace'); blob = txt + ' ' + json.dumps(h)
    objects = response_objects(txt, h)
    for obj in objects:
        if isinstance(obj, dict) and obj.get('jsonrpc') == '2.0':
            result = obj.get('result')
            structured = result.get('structuredContent') if isinstance(result, dict) else None
            if isinstance(structured, dict) and isinstance(structured.get('x402'), dict): out['mcp_payment_required'] = True
        quote = mcp_nano_quote(obj)
        if quote and st == 200: out['mcp_payment_quote'] = quote; break
    import base64
    for hk, hv in h.items():
        if hk.lower() in ('x-payment-required', 'payment-required'):
            try:
                dec = base64.b64decode(hv + '=' * (-len(hv) % 4)).decode()
                txt = txt + ' ' + dec; out['decoded_header'] = json.loads(dec)
            except Exception: pass
    paths = []
    def walk(o, pth=''):
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, pth + '/' + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, pth + '/' + str(i))
        elif isinstance(o, str):
            for a in ADDR.findall(o): paths.append({'path': pth, 'address': a})
    if out.get('decoded_header'): walk(out['decoded_header'], 'header-decoded')
    try: walk(json.loads(txt))
    except Exception:
        for k, v in h.items():
            for a in ADDR.findall(str(v)): paths.append({'path': 'header:' + k, 'address': a})
        for a in ADDR.findall(txt): paths.append({'path': 'body-text', 'address': a})
    out['address_paths'] = paths
    out['expect'] = p.get('expect'); out['body_head'] = txt[:160].replace('\n', ' '); out['http_status'] = st; out['ms'] = int((time.time() - t) * 1000)
    addrs = sorted(set(ADDR.findall(blob)))
    out['addresses'] = [{'address': a, 'checksum_valid': nanoaddr.is_valid(a)} for a in addrs]
    nets = []
    try:
        j = out.get('decoded_header') or json.loads(txt)
        for a in (j.get('accepts') or []):
            if isinstance(a, dict) and 'nano' in json.dumps(a).lower():
                nets.append({k: a.get(k) for k in ('scheme', 'network', 'asset', 'payTo', 'pay_to', 'maxAmountRequired', 'amount') if k in a})
    except Exception:
        pass
    out['nano_accepts'] = nets
    pr = h.get('payment-required') or h.get('Payment-Required')
    if pr: out['payment_required_header'] = True
    out['mentions_nano'] = 'nano' in blob.lower()
    return out
if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(probe, d['sellers']))
    json.dump({'probed_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'), 'results': res}, open(sys.argv[2], 'w'), indent=1)
    for r in res: print(r['id'], r.get('http_status'), len(r.get('addresses', [])), len(r.get('nano_accepts', [])), r.get('error', ''))
