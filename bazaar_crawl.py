import urllib.request,json,time,sys,threading
start=int(sys.argv[1]) if len(sys.argv)>1 else 0; total=71975
lock=threading.Lock(); out=open('bazaar.jsonl','a'); offs=list(range(start,total,100)); fails=[]
def worker():
    while True:
        with lock:
            if not offs: return
            off=offs.pop(0)
        d=None
        for i in range(5):
            try: d=json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100&offset={off}",headers={'User-Agent':'Mozilla/5.0'}),timeout=60));break
            except Exception: time.sleep(2+i*2)
        if d is None:
            fails.append(off); continue
        lines=[]
        for it in d['items']:
            q=it.get('quality') or {}
            lines.append(json.dumps({'off':off,'r':it.get('resource'),'t':it.get('type'),'acc':[{k:a.get(k) for k in ('network','asset','amount','maxAmountRequired','payTo','scheme')} for a in it.get('accepts',[])],'calls':q.get('l30DaysTotalCalls'),'payers':q.get('l30DaysUniquePayers'),'last':q.get('lastCalledAt')}))
        with lock: out.write("\n".join(lines)+"\n"); out.flush()
ts=[threading.Thread(target=worker) for _ in range(6)]
[t.start() for t in ts]; [t.join() for t in ts]
print('done fails',fails,file=sys.stderr)
