import sys,json,collections,urllib.parse,statistics
rows={}
for fn in ('bazaar.jsonl',):
    for l in open(fn):
        l=l.strip()
        if not l: continue
        try:d=json.loads(l)
        except: continue
        rows[d['r']]=d
USDC={'0x833589fcd6edb6e08f4c7c32d4f71b54bda02913','epjfwdd5aufqssqem2qn1xzybapc8g4weggkzwytdt1v','0x036cbd53842c5426634e7929541ec2318f3dcf7e'}
nets=collections.Counter(); priced=[];nonusdc=0;noamt=0
for d in rows.values():
    best=None
    for a in d['acc']: nets[a.get('network')]+=1
    for a in d['acc']:
        amt=a.get('amount') or a.get('maxAmountRequired')
        if a.get('asset') and a['asset'].lower() in USDC and amt and str(amt).isdigit():
            best=int(amt)/1e6;break
    if best is None:
        if any((a.get('amount') or a.get('maxAmountRequired')) for a in d['acc']): nonusdc+=1
        else: noamt+=1
    else: priced.append((best,d))
res={'unique_resources':len(rows),'priced_usdc':len(priced),'other_asset':nonusdc,'no_amount':noamt,'networks':nets.most_common(8)}
p=sorted(x for x,_ in priced)
res['median_price']=statistics.median(p); res['share_le_0.01']=round(sum(1 for x in p if x<=0.01)/len(p),4); res['share_le_0.001']=round(sum(1 for x in p if x<=0.001)/len(p),4)
act=[(x,d) for x,d in priced if (d['calls'] or 0)>0]
res['with_calls']=len(act); res['with_calls_le_0.01']=sum(1 for x,d in act if x<=0.01)
nano=[d['r'] for d in rows.values() if any('nano' in (a.get('network') or '').lower() for a in d['acc'])]
res['nano_accepts']=len(nano)
host=collections.defaultdict(lambda:{'res':0,'calls':0,'payers':0,'minp':9,'maxp':0,'payto':set()})
for x,d in priced:
    if x<=0.01:
        h=urllib.parse.urlparse(d['r']).netloc
        e=host[h];e['res']+=1;e['calls']+=d['calls'] or 0;e['payers']=max(e['payers'],d['payers'] or 0);e['minp']=min(e['minp'],x);e['maxp']=max(e['maxp'],x)
        for a in d['acc']:
            if a.get('payTo'): e['payto'].add(a['payTo'])
tot=sum(e['calls'] for e in host.values())
top=sorted(host.items(),key=lambda kv:-kv[1]['calls'])[:40]
res['hosts_le_0.01']=len(host); res['calls_le_0.01']=tot
res['top']=[{'host':h,'resources_le_0.01':e['res'],'l30_calls':e['calls'],'max_l30_unique_payers_one_resource':e['payers'],'min_price_usd':e['minp'],'max_price_usd':e['maxp'],'payTo_count':len(e['payto'])} for h,e in top]
res['top40_share_of_calls']=round(sum(e['calls'] for _,e in top)/tot,4)
res['crawl_rows_sample_last_called']=max((d['last'] or '') for d in rows.values())
json.dump(res,open('analysis.json','w'),indent=1); print(json.dumps({k:v for k,v in res.items() if k!='top'},indent=0)); 
for t in res['top'][:15]: print(t)

# --- second pass: host-weighted view, excluding the one host that holds most resources
byhost=collections.defaultdict(list)
for x,d in priced: byhost[urllib.parse.urlparse(d['r']).netloc].append((x,d))
big=max(byhost,key=lambda h:len(byhost[h]))
res['largest_host']={'host':big,'resources':len(byhost[big]),'share_of_all_resources':round(len(byhost[big])/len(priced),4)}
rest=[x for h,v in byhost.items() if h!=big for x,_ in v]
res['excluding_largest_host']={'resources':len(rest),'median_price':statistics.median(rest),'share_le_0.01':round(sum(1 for x in rest if x<=0.01)/len(rest),4)}
hm=[statistics.median([x for x,_ in v]) for h,v in byhost.items()]
res['hosts_total']=len(hm); res['hosts_median_price_le_0.01']=sum(1 for m in hm if m<=0.01)
res['nano_resources']=sorted(nano)
nanohosts={urllib.parse.urlparse(u).netloc for u in nano}
cand=[]
for h,e in sorted(host.items(),key=lambda kv:-kv[1]['calls']):
    if h in nanohosts or e['calls']<1000: continue
    ex=[d['r'] for x,d in byhost[h] if x<=0.01][:1]
    cand.append({'host':h,'resources_le_0.01':e['res'],'l30_calls':e['calls'],'max_l30_unique_payers_one_resource':e['payers'],'min_price_usd':e['minp'],'max_price_usd':e['maxp'],'sample_resource':ex[0] if ex else None})
res['targets']=cand[:60]; res['targets_total_ge_1000_calls']=len(cand)
json.dump(res,open('analysis.json','w'),indent=1)
print(json.dumps({k:res[k] for k in ('largest_host','excluding_largest_host','hosts_total','hosts_median_price_le_0.01','nano_resources','targets_total_ge_1000_calls')},indent=0))
