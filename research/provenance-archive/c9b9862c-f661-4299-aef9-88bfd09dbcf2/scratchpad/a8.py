import json, collections, math
import numpy as np
from scipy.special import gammaln
from scipy.optimize import minimize
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
reg=json.load(open(P+'public/data/market-regime.json',encoding='utf-8'))
up={r['date']:r['up'] for r in reg['series']}
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
MIN=4
days=sorted(k for k in byday if len(byday[k])>=MIN)
def nll(th,ns,ks):
    mu=1/(1+np.exp(-th[0])); rho=1/(1+np.exp(-th[1]))
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    v=gammaln(ks+a)+gammaln(ns-ks+b)-gammaln(ns+a+b)+gammaln(a+b)-gammaln(a)-gammaln(b)
    return -v.sum()
def fit(ns,ks):
    best=None
    for s in ([0,-1.5],[-0.5,-2.5],[0.5,-0.5]):
        r=minimize(nll,s,args=(ns,ks),method='Nelder-Mead',options={'xatol':1e-9,'fatol':1e-11,'maxiter':6000})
        if best is None or r.fun<best.fun: best=r
    return -best.fun, 1/(1+np.exp(-best.x[0])), 1/(1+np.exp(-best.x[1]))
def rep(tag,dl):
    ns=np.array([len(byday[k]) for k in dl],float); ks=np.array([sum(1 for x in byday[k] if x['result']=='win') for k in dl],float)
    p=ks.sum()/ns.sum(); ll,mu,rho=fit(ns,ks)
    lb=(ks*np.log(p)+(ns-ks)*np.log(1-p)).sum()
    obs=int((ks==0).sum()); expi=float(((1-p)**ns).sum())
    m=(1-rho)/rho;a=mu*m;b=(1-mu)*m
    expb=float(np.exp(gammaln(ns+b)-gammaln(ns+a+b)+gammaln(a+b)-gammaln(b)).sum())
    print(f"{tag}: days={len(dl)} trades={int(ns.sum())} p={100*p:.1f}% rho={rho:.3f} LR={2*(ll-lb):.1f} | wipeout obs={obs} indep_exp={expi:.2f} BB_exp={expb:.2f}")
# regime by scan_date (uniform within an entry-day)
def dayup(k):
    sd=byday[k][0]['scan_date']; return up.get(sd)
rep("ALL n>=4", days)
rep("UP (scan_date regime)", [k for k in days if dayup(k)])
rep("DOWN (scan_date regime)", [k for k in days if dayup(k)==False])

# ---- practical: does spreading buys across days help? ----
rng=np.random.default_rng(3)
alld=sorted(byday)
res={k:[1 if x['result']=='win' else 0 for x in byday[k]] for k in alld}
import datetime as DT
ordn={k:DT.date.fromisoformat(k).toordinal() for k in alld}
def draw_same_day(k):
    cands=[dd for dd in alld if len(res[dd])>=k]
    dd=cands[rng.integers(len(cands))]
    idx=rng.choice(len(res[dd]),k,replace=False)
    return [res[dd][i] for i in idx]
def draw_spread(k,minsep,maxspan=None):
    for _ in range(400):
        start=alld[rng.integers(len(alld))]
        picked=[start]; 
        pool=[dd for dd in alld if dd!=start]
        rng.shuffle(pool)
        for dd in pool:
            if len(picked)==k: break
            if all(abs(ordn[dd]-ordn[q])>=minsep for q in picked) and (maxspan is None or (max(ordn[dd],*[ordn[q] for q in picked])-min(ordn[dd],*[ordn[q] for q in picked]))<=maxspan):
                picked.append(dd)
        if len(picked)==k:
            return [res[dd][rng.integers(len(res[dd]))] for dd in picked]
    return None
def draw_random(k):
    flat=[v for dd in alld for v in res[dd]]
    idx=rng.choice(len(flat),k,replace=False)
    return [flat[i] for i in idx]
S=40000
for tag,fn in (("same day (6 at once)",lambda: draw_same_day(6)),
               ("6 different days within 1 week",lambda: draw_spread(6,1,7)),
               ("6 days >=14d apart",lambda: draw_spread(6,14)),
               ("6 fully random trades (no time link)",lambda: draw_random(6))):
    wipe=0;sweep=0;wins=0;cnt=0
    for _ in range(S):
        o=fn()
        if o is None: continue
        cnt+=1; s=sum(o); wins+=s
        if s==0: wipe+=1
        if s==6: sweep+=1
    print(f"{tag}: n={cnt} winrate={100*wins/(6*cnt):.1f}% wipeout={100*wipe/cnt:.1f}% sweep={100*sweep/cnt:.1f}%")
