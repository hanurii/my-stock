import json, collections, math, random
import numpy as np

ROOT=r"C:\Users\hanul\playground\my-stock"
d=json.load(open(ROOT+r"\public\data\backtest-volatility-pilot.json",encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
reg={r['date']:r['up'] for r in json.load(open(ROOT+r"\public\data\market-regime.json",encoding='utf-8'))['series']}

for x in ev:
    x['w']=1 if x['result']=='win' else 0
    x['ret']=20.0 if x['result']=='win' else -10.0
    x['up']=reg.get(x['scan_date'])

print("resolved:",len(ev),"win rate %.2f"%(100*np.mean([x['w'] for x in ev])))
print("regime missing:",sum(1 for x in ev if x['up'] is None))

# ---- within-day rank by turnover_eok (descending: bigger turnover = better rank) ----
bydate=collections.defaultdict(list)
for x in ev: bydate[x['scan_date']].append(x)

def assign_ranks(group):
    # descending by turnover; rank_frac in [0,1)
    g=sorted(group,key=lambda z:-z['turnover_eok'])
    n=len(g)
    for i,z in enumerate(g):
        z['n_day']=n
        z['rank_i']=i
        z['rank_frac']=i/n            # 0 = biggest turnover
        z['pct_rank']=(n-1-i)/(n-1) if n>1 else 0.5   # 1 = biggest
for k,g in bydate.items(): assign_ranks(g)

def signtest(k,n):
    # two-sided exact binomial p
    if n==0: return 1.0
    p=0.0
    for i in range(n+1):
        pr=math.comb(n,i)*0.5**n
        if pr<=math.comb(n,k)*0.5**n + 1e-12: p+=pr
    return min(1.0,p)

def sameday(events, grouper, label, stat='win'):
    """grouper(x)->True(treat)/False(ctrl)/None(skip). Sign test over days where both present."""
    days=collections.defaultdict(lambda:([],[]))
    for x in events:
        g=grouper(x)
        if g is None: continue
        val = x['w'] if stat=='win' else x['ret']
        days[x['scan_date']][0 if g else 1].append(val)
    diffs=[]; used=0
    for dt,(a,b) in days.items():
        if a and b:
            used+=1
            diffs.append(np.mean(a)-np.mean(b))
    diffs=np.array(diffs)
    pos=int((diffs>0).sum()); neg=int((diffs<0).sum()); tie=int((diffs==0).sum())
    p=signtest(max(pos,neg),pos+neg)
    return dict(label=label,days=used,pos=pos,neg=neg,tie=tie,p=p,mean_diff=float(diffs.mean()) if used else float('nan'),
                median_diff=float(np.median(diffs)) if used else float('nan'))

def perm_sameday(events,grouper,stat='win',B=5000,seed=1):
    """Within-day label permutation: shuffle turnover ranks inside each day."""
    rng=random.Random(seed)
    days=collections.defaultdict(list)
    for x in events:
        g=grouper(x)
        if g is None: continue
        days[x['scan_date']].append((g, x['w'] if stat=='win' else x['ret']))
    # observed: day-weighted? use pooled trade-level diff of means within-day averaged over days weighted by day
    def stat_fn(assign):
        num=[];
        for dt,items in assign.items():
            a=[v for g,v in items if g]; b=[v for g,v in items if not g]
            if a and b: num.append(np.mean(a)-np.mean(b))
        return np.mean(num) if num else float('nan')
    obs=stat_fn(days)
    cnt=0
    keys=list(days)
    for _ in range(B):
        perm={}
        for dt in keys:
            items=days[dt]
            labs=[g for g,_ in items]; vals=[v for _,v in items]
            rng.shuffle(labs)
            perm[dt]=list(zip(labs,vals))
        if stat_fn(perm)>=obs: cnt+=1
    return obs,(cnt+1)/(B+1)

print("\n=== 1) SAME-DAY SIGN TESTS (independent recompute) ===")
grp_med   = lambda x: None if x['n_day']<2 else (x['rank_frac']<0.5)
grp_top3  = lambda x: None if x['n_day']<2 else (x['rank_frac']<1/3)
grp_top3b = lambda x: None if x['n_day']<3 else (x['rank_frac']<1/3)
for name,g in [("median split",grp_med),("top1/3 (n>=2)",grp_top3),("top1/3 (n>=3)",grp_top3b)]:
    r=sameday(ev,g,name); print(" %-16s days=%3d  +%d/-%d (tie %d)  p=%.4f  meanDiff=%+.2f%%p"%(
        r['label'],r['days'],r['pos'],r['neg'],r['tie'],r['p'],100*r['mean_diff']))
    o,p=perm_sameday(ev,g,B=5000); print("     perm(win) obs=%+.2f%%p p=%.4f"%(100*o,p))
    o,p=perm_sameday(ev,g,stat='ret',B=5000); print("     perm(EV)  obs=%+.2f%%   p=%.4f"%(o,p))
