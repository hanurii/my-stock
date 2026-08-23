import json, collections, math, datetime as dt
from math import lgamma
import numpy as np
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
MIN=4
days=sorted(dt_ for dt_ in byday if len(byday[dt_])>=MIN)
data=[(len(byday[k]),sum(1 for x in byday[k] if x['result']=='win')) for k in days]
N=sum(n for n,_ in data); K=sum(k for _,k in data); p=K/N

def betabin_ll(mu,rho,data):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m; s=0.0
    for n,k in data:
        s+= lgamma(k+a)+lgamma(n-k+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(a)-lgamma(b)
    return s
def fit(data):
    best=(-1e18,0,0)
    for mu in np.linspace(0.10,0.80,141):
        for rho in np.linspace(0.0005,0.8,400):
            ll=betabin_ll(mu,rho,data)
            if ll>best[0]: best=(ll,mu,rho)
    return best
ll,mu,rho=fit(data)
print(f"MLE mu={mu:.4f} rho={rho:.4f}")

def bb_p0(n,mu,rho):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    return math.exp(lgamma(n+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(b))
def bb_pk(n,k,mu,rho):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    return math.exp(lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)+lgamma(k+a)+lgamma(n-k+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(a)-lgamma(b))

print("\n=== buying 6 on one day ===")
print(f"binomial p={mu:.3f}: P(0 wins)={(1-mu)**6*100:.2f}%  P(6 wins)={mu**6*100:.2f}%")
print(f"beta-binom rho={rho:.3f}: P(0 wins)={bb_p0(6,mu,rho)*100:.2f}%  P(6 wins)={bb_pk(6,6,mu,rho)*100:.2f}%")
# conditional sequential failure
def Pfail_first_j(j):  # P(first j all lose)
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    return math.exp(lgamma(j+b)-lgamma(j+a+b)+lgamma(a+b)-lgamma(b))
for j in range(1,7):
    prev=Pfail_first_j(j-1) if j>1 else 1.0
    print(f"  P(loss #{j} | previous {j-1} all lost) = {100*Pfail_first_j(j)/prev:.1f}%")
print("  BB distribution of wins out of 6:", " ".join(f"{k}:{bb_pk(6,k,mu,rho)*100:.1f}%" for k in range(7)))
print("  binom distribution of wins out of 6:", " ".join(f"{k}:{math.comb(6,k)*mu**k*(1-mu)**(6-k)*100:.1f}%" for k in range(7)))

print("\n=== bootstrap CI over days (2000) ===")
rng=np.random.default_rng(7)
rhos=[];p0s=[]
for _ in range(2000):
    idx=rng.integers(0,len(data),len(data))
    dboot=[data[i] for i in idx]
    _,m2,r2=fit(dboot)
    rhos.append(r2); p0s.append(bb_p0(6,m2,r2))
rhos=np.array(rhos);p0s=np.array(p0s)
print(f"rho  median={np.median(rhos):.3f} 90%CI=[{np.percentile(rhos,5):.3f},{np.percentile(rhos,95):.3f}]  P(rho<0.05)={np.mean(rhos<0.05)*100:.1f}%")
print(f"P(0 of 6) median={np.median(p0s)*100:.1f}% 90%CI=[{np.percentile(p0s,5)*100:.1f}%,{np.percentile(p0s,95)*100:.1f}%]")
