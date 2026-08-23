import json, math
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
days=defaultdict(list)
for x in ev: days[x['entry_date']].append(x)
print('entry days total', len(days))
def stats(sel,label,minn):
    ds={d:v for d,v in sel.items() if len(v)>=minn}
    k=len(ds); N=sum(len(v) for v in ds.values()); W=sum(1 for v in ds.values() for x in v if x['result']=='win')
    p=W/N
    chi2=0.0; rates=[]; ns=[]
    for d,v in ds.items():
        n=len(v); w=sum(1 for x in v if x['result']=='win')
        chi2+=(w-n*p)**2/(n*p*(1-p)); rates.append(w/n); ns.append(n)
    mr=sum(rates)/k
    obs=sum((r-mr)**2 for r in rates)/(k-1)
    exp=sum(p*(1-p)/n for n in ns)/k
    print('%s min%d: days=%d N=%d p=%.4f  obsVar=%.4f expVar=%.4f ratio=%.2f chi2=%.1f df=%d'%(label,minn,k,N,p,obs,exp,obs/exp,chi2,k-1))
    return chi2,k-1
# uptrend by scan_date
upd=defaultdict(list); alld=defaultdict(list)
for d,v in days.items():
    alld[d]=v
    u=[x for x in v if reg[x['scan_date']]]
    if u: upd[d]=u
for m in (3,4):
    stats(upd,'UP(scan)',m); stats(alld,'ALL',m)
# p-value
def chisq_sf(x,df):
    # regularized upper incomplete gamma via series/continued fraction
    a=df/2.0; xx=x/2.0
    if xx< a+1:
        # series for P(a,x)
        ap=a; s=1.0/a; term=s
        for _ in range(10000):
            ap+=1; term*=xx/ap; s+=term
            if abs(term)<abs(s)*1e-16: break
        return 1.0-s*math.exp(-xx+a*math.log(xx)-math.lgamma(a))
    else:
        b=xx+1-a; c=1e308; d=1.0/b; h=d
        for i in range(1,10000):
            an=-i*(i-a); b+=2
            d=an*d+b; 
            if abs(d)<1e-300: d=1e-300
            c=b+an/c
            if abs(c)<1e-300: c=1e-300
            d=1.0/d; de=d*c; h*=de
            if abs(de-1)<1e-16: break
        return math.exp(-xx+a*math.log(xx)-math.lgamma(a))*h
c,df=stats(upd,'UP(scan)',3)
print('p=%.3g'%chisq_sf(c,df))
