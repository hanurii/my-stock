import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
BT='C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json'
ev=json.load(open(BT,encoding='utf-8'))['events']
pit=json.load(open('C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
uppit={dt:bool(u) for dt,u in zip(pit['dates'],pit['up'])}
mr=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
upmr={x['date']:bool(x['up']) for x in mr['series']}
for i,e in enumerate(ev): e['idx']=i
BUY=0.0014; SELL=0.0034
def nm(g): return (1+g/100.0)*(1-SELL)/(1+BUY)
def sim(pool,seed,slots=5,same_day=False,size='equity'):
    rng=random.Random(seed); byday=defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    alld=sorted(set(byday)|set(e['resolve_date'] for e in pool))
    cash=1.0; op=[]; n=0
    for dt in alld:
        keep=[]
        for rd,inv,g,idx in op:
            if (rd<=dt) if same_day else (rd<dt):
                cash+=inv*nm(g)
            else: keep.append((rd,inv,g,idx))
        op=keep
        c=byday.get(dt,[])
        if not c: continue
        rng.shuffle(c)
        for e in c:
            if len(op)>=slots: break
            eq=cash+sum(x[1] for x in op)
            s=eq/slots if size=='equity' else cash/max(1,slots-len(op))
            s=min(s,cash)
            if s<=1e-9: break
            cash-=s; op.append((e['resolve_date'],s,e['gain_at_resolve_pct'],e['idx'])); n+=1
    for rd,inv,g,idx in op: cash+=inv*nm(g)
    return (cash-1)*100, n
def run(pool,**kw):
    r=[sim(pool,s,**kw) for s in range(300)]
    return st.median([x[0] for x in r]), st.median([x[1] for x in r])
for same_day in [False,True]:
  for tag,fn in [('pit/scan',lambda e:uppit.get(e['scan_date'],False)),
                 ('pit/entry',lambda e:uppit.get(e['entry_date'],False)),
                 ('mr/scan',lambda e:upmr.get(e['scan_date'],False)),
                 ('mr/entry',lambda e:upmr.get(e['entry_date'],False))]:
    upp=[e for e in ev if fn(e)]
    a,na=run(ev,same_day=same_day); b,nb=run(upp,same_day=same_day)
    print(f'same_day={same_day} {tag:10s} n_up={len(upp):3d} ALL {a:+7.2f}% ({na:.0f}건) UP {b:+7.2f}% ({nb:.0f}건)')
