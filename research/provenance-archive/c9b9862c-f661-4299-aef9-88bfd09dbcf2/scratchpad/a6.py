import json, collections, math, datetime as DT
import numpy as np
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
MIN=4
days=sorted(k for k in byday if len(byday[k])>=MIN)
sub=[x for k in days for x in byday[k]]
print("subset trades:",len(sub),"days:",len(days))
y=np.array([1 if x['result']=='win' else 0 for x in sub])
dayidx=np.array([days.index(x['entry_date']) for x in sub])
code=[x['code'] for x in sub]
p=y.mean()

def stat(yv):
    wipe=0; chi2=0.0
    for i,k in enumerate(days):
        m=(dayidx==i); n=m.sum(); w=yv[m].sum()
        if w==0: wipe+=1
        chi2+=(w-n*p)**2/(n*p*(1-p))
    return wipe, chi2
obs=stat(y); print("observed wipeout days=%d chi2=%.1f"%obs)

# stock-block permutation: swap whole stocks' outcome vectors among stocks with same trade count
bycode=collections.defaultdict(list)
for i,c in enumerate(code): bycode[c].append(i)
groups=collections.defaultdict(list)
for c,idxs in bycode.items(): groups[len(idxs)].append(idxs)
print("stocks by trade-count:", {k:len(v) for k,v in sorted(groups.items())})
rng=np.random.default_rng(11)
B=3000
wipes=np.empty(B); chis=np.empty(B)
for b in range(B):
    yv=np.empty_like(y)
    for cnt,lst in groups.items():
        order=rng.permutation(len(lst))
        for a,bi in enumerate(order):
            src=lst[bi]; dst=lst[a]
            yv[dst]=y[src]
    wipes[b],chis[b]=stat(yv)
print(f"stock-block perm (B={B}): wipeout mean={wipes.mean():.2f} p(>=obs)={(np.sum(wipes>=obs[0])+1)/(B+1):.5f} | chi2 mean={chis.mean():.1f} p(>=obs)={(np.sum(chis>=obs[1])+1)/(B+1):.5f}")

# free permutation for comparison
wipes2=np.empty(B); chis2=np.empty(B)
for b in range(B):
    yv=rng.permutation(y); wipes2[b],chis2[b]=stat(yv)
print(f"free perm       (B={B}): wipeout mean={wipes2.mean():.2f} p(>=obs)={(np.sum(wipes2>=obs[0])+1)/(B+1):.5f} | chi2 mean={chis2.mean():.1f} p(>=obs)={(np.sum(chis2>=obs[1])+1)/(B+1):.5f}")

# ---- pair correlation by entry-date gap (all 580 resolved trades) ----
ev2=ev
y2=np.array([1 if x['result']=='win' else 0 for x in ev2],float)
dts=np.array([DT.date.fromisoformat(x['entry_date']).toordinal() for x in ev2],float)
p2=y2.mean(); c=(y2-p2)
n=len(ev2)
I,J=np.triu_indices(n,1)
gap=np.abs(dts[I]-dts[J])
prod=c[I]*c[J]/(p2*(1-p2))
bins=[(0,0),(1,1),(2,3),(4,7),(8,15),(16,31),(32,63),(64,400)]
print("\npair correlation of outcomes by calendar gap between entry dates (n=%d trades):"%n)
for lo,hi in bins:
    m=(gap>=lo)&(gap<=hi)
    if m.sum()==0: continue
    print(f"  gap {lo}-{hi}d: pairs={m.sum():7d} rho_hat={prod[m].mean():+.4f}")
