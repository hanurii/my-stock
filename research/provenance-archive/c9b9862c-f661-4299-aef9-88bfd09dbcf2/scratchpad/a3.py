import json, collections, math
from math import lgamma
import numpy as np
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
reg=json.load(open(P+'public/data/market-regime.json',encoding='utf-8'))
up={r['date']: r['up'] for r in reg['series']}
print("regime series:", len(up), min(up), max(up))

def build(results_map):
    ev=[x for x in d['events'] if results_map(x) is not None]
    byday=collections.defaultdict(list)
    for x in ev: byday[x['entry_date']].append(results_map(x))
    return byday

base=lambda x: (1 if x['result']=='win' else 0) if x['result'] in ('win','loss') else None
amb_win=lambda x: (1 if x['result'] in ('win',) else (1 if x['result']=='ambiguous' else 0)) if x['result'] in ('win','loss','ambiguous') else None
amb_loss=lambda x: (1 if x['result']=='win' else 0) if x['result'] in ('win','loss','ambiguous') else None

def betabin_ll(mu,rho,data):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m; s=0.0
    for n,k in data:
        s+= lgamma(k+a)+lgamma(n-k+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(a)-lgamma(b)
    return s
def fit(data):
    best=(-1e18,0,0)
    for mu in np.linspace(0.05,0.9,171):
        for rho in np.linspace(0.001,0.7,350):
            ll=betabin_ll(mu,rho,data)
            if ll>best[0]: best=(ll,mu,rho)
    return best
def binll(data):
    N=sum(n for n,_ in data); K=sum(k for _,k in data); p=K/N; s=0
    for n,k in data:
        s+=(k*math.log(p) if k else 0)+((n-k)*math.log(1-p) if n-k else 0)
    return s,p

def report(tag,data):
    if len(data)<8: print(f"{tag}: too few days ({len(data)})"); return
    N=sum(n for n,_ in data); K=sum(k for _,k in data)
    ll,mu,rho=fit(data); lb,p=binll(data); lr=2*(ll-lb)
    obs=sum(1 for n,k in data if k==0); expi=sum((1-p)**n for n,_ in data)
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    expb=sum(math.exp(lgamma(n+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(b)) for n,_ in data)
    print(f"{tag}: days={len(data)} trades={N} p={100*p:.1f}% rho={rho:.3f} LR={lr:.1f} | wipeout obs={obs} indep={expi:.2f} BB={expb:.2f}")

MIN=4
byday=build(base)
days=sorted(dt for dt in byday if len(byday[dt])>=MIN)
data=[(len(byday[dt]),sum(byday[dt])) for dt in days]
report("ALL n>=4", data)

# regime split (entry_date regime; fall back to nearest prior date)
regdates=sorted(up)
import bisect
def isup(dt):
    if dt in up: return up[dt]
    i=bisect.bisect_left(regdates,dt)-1
    return up[regdates[i]] if i>=0 else None
u=[(len(byday[dt]),sum(byday[dt])) for dt in days if isup(dt)]
dn=[(len(byday[dt]),sum(byday[dt])) for dt in days if isup(dt)==False]
report("UP days", u); report("DOWN days", dn)

# front/back half
cut='2026-03-25'
f=[(len(byday[dt]),sum(byday[dt])) for dt in days if dt< cut]
b=[(len(byday[dt]),sum(byday[dt])) for dt in days if dt>=cut]
report("FIRST half (<2026-03-25)", f); report("SECOND half (>=2026-03-25)", b)

# ambiguous sensitivity
for tag,fn in (("amb->win",amb_win),("amb->loss",amb_loss)):
    bd=build(fn); dd=sorted(dt for dt in bd if len(bd[dt])>=MIN)
    report(tag, [(len(bd[dt]),sum(bd[dt])) for dt in dd])

# does day size predict win rate? (alternative explanation)
ns=np.array([n for n,_ in data],float); ks=np.array([k for _,k in data],float)
r=np.corrcoef(ns,ks/ns)[0,1]
print(f"corr(day size, day win rate) = {r:.3f} over {len(data)} days")
