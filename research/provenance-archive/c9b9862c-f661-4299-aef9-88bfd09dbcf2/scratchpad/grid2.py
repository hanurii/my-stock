import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ev=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))['events']
pit=json.load(open('C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
uppit={dt:bool(u) for dt,u in zip(pit['dates'],pit['up'])}
for i,e in enumerate(ev): e['idx']=i; e['up']=uppit.get(e['scan_date'],False)
def mk(buy,sell):
    def nm(g): return (1+g/100.0)*(1-sell)/(1+buy)
    return nm
def sim(pool,seed,nm,slots=5):
    rng=random.Random(seed); byday=defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    alld=sorted(set(byday)|set(e['resolve_date'] for e in pool))
    cash=1.0; op=[]; n=0
    for dt in alld:
        keep=[]
        for rd,inv,g in op:
            if rd<=dt: cash+=inv*nm(g)
            else: keep.append((rd,inv,g))
        op=keep
        c=byday.get(dt,[])
        if not c: continue
        rng.shuffle(c)
        for e in c:
            if len(op)>=slots: break
            eq=cash+sum(x[1] for x in op); s=min(eq/slots,cash)
            if s<=1e-9: break
            cash-=s; op.append((e['resolve_date'],s,e['gain_at_resolve_pct'])); n+=1
    for rd,inv,g in op: cash+=inv*nm(g)
    return (cash-1)*100,n
def run(pool,nm):
    r=[sim(pool,s,nm) for s in range(300)]
    return st.median([x[0] for x in r]), st.median([x[1] for x in r])
sets={'전체614':ev,'확정580':[e for e in ev if e['result'] in('win','loss')]}
fees={'미래에셋 0.14/0.34':(0.0014,0.0034),'무수수료':(0,0),'세금만 0.2':(0,0.002)}
for sname,pool in sets.items():
    for fname,(b,s) in fees.items():
        nm=mk(b,s)
        a,na=run(pool,nm); u,nu=run([e for e in pool if e['up']],nm)
        print(f'{sname} {fname:16s} ALL {a:+7.2f}% ({na:.0f}건)  UP {u:+7.2f}% ({nu:.0f}건)')
