import json, collections, math, random
from math import lgamma
import numpy as np
d=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)

def daydata(minn):
    ds=sorted(dt for dt in byday if len(byday[dt])>=minn)
    return [(dt, len(byday[dt]), sum(1 for x in byday[dt] if x['result']=='win')) for dt in ds]

def betabin_ll(a,b,data):
    s=0.0
    for _,n,k in data:
        s+= lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1) + lgamma(k+a)+lgamma(n-k+b)-lgamma(n+a+b) + lgamma(a+b)-lgamma(a)-lgamma(b)
    return s

def fit_bb(data):
    # grid + refine on (mu, rho)
    best=None
    for mu in np.linspace(0.15,0.65,101):
        for rho in np.linspace(0.0005,0.6,300):
            m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
            ll=betabin_ll(a,b,data)
            if best is None or ll>best[0]: best=(ll,mu,rho)
    ll,mu,rho=best
    # refine
    for _ in range(6):
        step_mu=0.01; step_rho=0.01
        improved=True
        while improved:
            improved=False
            for dmu,drho in [(step_mu,0),(-step_mu,0),(0,step_rho),(0,-step_rho),(step_mu,step_rho),(-step_mu,-step_rho),(step_mu,-step_rho),(-step_mu,step_rho)]:
                m2=min(max(mu+dmu,0.01),0.99); r2=min(max(rho+drho,1e-6),0.95)
                mm=(1-r2)/r2
                l2=betabin_ll(m2*mm,(1-m2)*mm,data)
                if l2>ll: ll,mu,rho=l2,m2,r2; improved=True
        step_mu/=3; step_rho/=3
    return ll,mu,rho

def bin_ll(p,data):
    s=0.0
    for _,n,k in data:
        s+= lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1) + (k*math.log(p) if k>0 else 0) + ((n-k)*math.log(1-p) if n-k>0 else 0)
    return s

def bb_pmf0(n,mu,rho):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    # P(X=0)
    return math.exp(lgamma(n+b)-lgamma(n+a+b)+lgamma(a+b)-lgamma(b))
def bb_pmfn(n,mu,rho):
    m=(1-rho)/rho; a=mu*m; b=(1-mu)*m
    return math.exp(lgamma(n+a)-lgamma(n+a+b)+lgamma(a+b)-lgamma(a))

rng=np.random.default_rng(20260822)
print("=== per-cut check (is n>=4 cherry-picked?) ===")
for minn in (1,2,3,4,5,6):
    data=daydata(minn)
    N=sum(n for _,n,_ in data); K=sum(k for _,_,k in data); p=K/N
    exp_wipe=sum((1-p)**n for _,n,_ in data)
    exp_swp=sum(p**n for _,n,_ in data)
    obs_wipe=sum(1 for _,n,k in data if k==0)
    obs_swp=sum(1 for _,n,k in data if k==n)
    # simulate
    S=20000
    ns=np.array([n for _,n,_ in data])
    sims=rng.binomial(ns[None,:],p,size=(S,len(ns)))
    w=(sims==0).sum(axis=1)
    pv=( (w>=obs_wipe).sum()+1 )/(S+1)
    # overdispersion chi2
    chi2=sum((k-n*p)**2/(n*p*(1-p)) for _,n,k in data)
    df=len(data)-1
    ll,mu,rho=fit_bb(data)
    llb=bin_ll(p,data)
    lr=2*(ll-llb)
    ebw=sum(bb_pmf0(n,mu,rho) for _,n,_ in data)
    ebs=sum(bb_pmfn(n,mu,rho) for _,n,_ in data)
    print(f"n>={minn}: days={len(data)} trades={N} p={100*p:.2f}% | wipeout obs={obs_wipe} exp_indep={exp_wipe:.2f} p_sim={pv:.5f} | sweep obs={obs_swp} exp_indep={exp_swp:.2f}")
    print(f"        chi2={chi2:.1f}/df={df} ratio={chi2/df:.2f} | BB mu={mu:.4f} rho={rho:.4f} LR={lr:.1f} | BB exp wipeout={ebw:.2f} sweep={ebs:.2f}")
