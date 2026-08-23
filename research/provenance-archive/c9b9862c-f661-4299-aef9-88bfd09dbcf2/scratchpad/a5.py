import json, collections, math
import numpy as np
from scipy.special import gammaln
from scipy.optimize import minimize
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
MIN=4
days=sorted(k for k in byday if len(byday[k])>=MIN)
ns=np.array([len(byday[k]) for k in days],float)
ks=np.array([sum(1 for x in byday[k] if x['result']=='win') for k in days],float)

def nll(th,ns,ks):
    mu=1/(1+np.exp(-th[0])); rho=1/(1+np.exp(-th[1]))
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    if a<=0 or b<=0 or not np.isfinite(a+b): return 1e12
    v=gammaln(ks+a)+gammaln(ns-ks+b)-gammaln(ns+a+b)+gammaln(a+b)-gammaln(a)-gammaln(b)
    return -v.sum()
def fit(ns,ks):
    best=None
    for s in ([0,-1.5],[-0.5,-2.5],[0.5,-0.5]):
        r=minimize(nll,s,args=(ns,ks),method='Nelder-Mead',options={'xatol':1e-8,'fatol':1e-10,'maxiter':5000})
        if best is None or r.fun<best.fun: best=r
    mu=1/(1+np.exp(-best.x[0])); rho=1/(1+np.exp(-best.x[1]))
    return -best.fun, mu, rho
ll,mu,rho=fit(ns,ks)
print(f"MLE mu={mu:.4f} rho={rho:.4f} ll={ll:.3f}")
def bb_pk(n,k,mu,rho):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    return math.exp(gammaln(n+1)-gammaln(k+1)-gammaln(n-k+1)+gammaln(k+a)+gammaln(n-k+b)-gammaln(n+a+b)+gammaln(a+b)-gammaln(a)-gammaln(b))
print("\n=== 6 buys in one day ===")
print(f"independent(p={mu:.3f}): P(0 wins)={(1-mu)**6*100:.2f}%  P(all 6 win)={mu**6*100:.2f}%")
print(f"beta-binom(rho={rho:.3f}):  P(0 wins)={bb_pk(6,0,mu,rho)*100:.2f}%  P(all 6 win)={bb_pk(6,6,mu,rho)*100:.2f}%")
for j in range(1,7):
    cur=bb_pk(j,0,mu,rho); prev=bb_pk(j-1,0,mu,rho) if j>1 else 1.0
    print(f"  P(#{j} also loses | first {j-1} all lost) = {100*cur/prev:.1f}%")
print("  wins-out-of-6 BB :", " ".join(f"{k}:{bb_pk(6,k,mu,rho)*100:.1f}" for k in range(7)))
print("  wins-out-of-6 bin:", " ".join(f"{k}:{math.comb(6,k)*mu**k*(1-mu)**(6-k)*100:.1f}" for k in range(7)))

rng=np.random.default_rng(7)
rhos=np.empty(3000); p0=np.empty(3000)
for i in range(3000):
    idx=rng.integers(0,len(ns),len(ns))
    _,m2,r2=fit(ns[idx],ks[idx])
    rhos[i]=r2; p0[i]=bb_pk(6,0,m2,r2)
print(f"\nbootstrap(3000 days-resample): rho median={np.median(rhos):.3f} 90%CI=[{np.percentile(rhos,5):.3f},{np.percentile(rhos,95):.3f}] P(rho<0.05)={100*np.mean(rhos<0.05):.1f}%")
print(f"  P(0 of 6) median={100*np.median(p0):.1f}% 90%CI=[{100*np.percentile(p0,5):.1f}%,{100*np.percentile(p0,95):.1f}%]")
