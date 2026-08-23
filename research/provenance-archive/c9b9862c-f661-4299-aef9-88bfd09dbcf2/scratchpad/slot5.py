import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

BT='C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json'
PIT='C:/Users/hanul/AppData/Local/Temp/pit_index.json'
ev=json.load(open(BT,encoding='utf-8'))['events']
pit=json.load(open(PIT,encoding='utf-8'))
up={dt:u for dt,u in zip(pit['dates'],pit['up'])}
for i,e in enumerate(ev):
    e['idx']=i
    e['up']=bool(up.get(e['scan_date']))

BUY_FEE=0.0014; SELL_FEE=0.0014+0.0020

def net_mult(g):
    """net return multiple on invested KRW incl. fees"""
    return (1+g/100.0)*(1-SELL_FEE)/(1+BUY_FEE)

def simulate(pool, slots=5, seed=0, size_mode='equity', exclude=frozenset(), track=False):
    rng=random.Random(seed)
    byday=defaultdict(list)
    for e in pool:
        if e['idx'] in exclude: continue
        byday[e['entry_date']].append(e)
    dates=sorted(byday.keys())
    alldates=sorted(set(dates)|set(e['resolve_date'] for e in pool))
    cash=1.0
    open_pos=[]   # (resolve_date, invested, gain, idx)
    contrib=defaultdict(float)
    ntrades=0
    for dt in alldates:
        # close positions resolving before today (free capital at resolve; assume reuse next day)
        still=[]
        for rd,inv,g,idx in open_pos:
            if rd < dt:
                pnl=inv*net_mult(g)-inv
                cash+=inv*net_mult(g)
                contrib[idx]+=pnl
            else: still.append((rd,inv,g,idx))
        open_pos=still
        cands=byday.get(dt,[])
        if not cands: continue
        rng.shuffle(cands)
        for e in cands:
            if len(open_pos)>=slots: break
            equity=cash+sum(inv for _,inv,_,_ in open_pos)
            if size_mode=='equity': size=equity/slots
            else: size=cash/max(1,slots-len(open_pos))
            size=min(size,cash)
            if size<=1e-9: break
            cash-=size
            open_pos.append((e['resolve_date'],size,e['gain_at_resolve_pct'],e['idx']))
            ntrades+=1
    for rd,inv,g,idx in open_pos:
        pnl=inv*net_mult(g)-inv
        cash+=inv*net_mult(g); contrib[idx]+=pnl
    if track: return (cash-1)*100, ntrades, dict(contrib)
    return (cash-1)*100, ntrades

def run(pool, n=300, exclude=frozenset(), size_mode='equity', slots=5):
    rs=[];nt=[]
    for s in range(n):
        r,t=simulate(pool,slots=slots,seed=s,size_mode=size_mode,exclude=exclude)
        rs.append(r);nt.append(t)
    return st.median(rs), st.mean(rs), st.median(nt), rs

allpool=ev
uppool=[e for e in ev if e['up']]
for mode in ['equity','cash']:
    m1,a1,t1,_=run(allpool,size_mode=mode)
    m2,a2,t2,_=run(uppool,size_mode=mode)
    print(f'size_mode={mode}: ALL median {m1:+.2f}% (mean {a1:+.2f}) trades~{t1:.0f} | UP median {m2:+.2f}% (mean {a2:+.2f}) trades~{t2:.0f}')
