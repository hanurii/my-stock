import json, math
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
days=defaultdict(list)
for x in ev: days[x['entry_date']].append(x)

def wipe(sel,minn,label):
    ds=[(d,v) for d,v in sorted(sel.items()) if len(v)>=minn]
    k=len(ds); N=sum(len(v) for _,v in ds); W=sum(1 for _,v in ds for x in v if x['result']=='win'); p=W/N
    z=[(d,v) for d,v in ds if all(x['result']=='loss' for x in v)]
    full=[(d,v) for d,v in ds if all(x['result']=='win' for x in v)]
    expz=sum((1-p)**len(v) for _,v in ds)
    expf=sum(p**len(v) for _,v in ds)
    print('%s min%d days=%d N=%d p=%.3f  wipeout=%d(%.0f%%) exp=%.1f(%.0f%%)  sweep=%d exp=%.1f'%(
        label,minn,k,N,p,len(z),100*len(z)/k,expz,100*expz/k,len(full),expf))
    return ds,z
allsel={d:v for d,v in days.items()}
upsel={}
for d,v in days.items():
    u=[x for x in v if reg[x['scan_date']]]
    if u: upsel[d]=u
wipe(allsel,4,'ALL'); wipe(upsel,4,'UP(scan)'); wipe(upsel,3,'UP(scan)')
# entry_date regime version
upe={}
for d,v in days.items():
    u=[x for x in v if reg[d]]
    if u: upe[d]=u
wipe(upe,4,'UP(entry)')
# distribution for UP min3
ds=[(d,v) for d,v in sorted(upsel.items()) if len(v)>=3]
buck=[0]*5
for d,v in ds:
    r=sum(1 for x in v if x['result']=='win')/len(v)
    if r==0: buck[0]+=1
    elif r<0.25: buck[1]+=1
    elif r<0.5: buck[2]+=1
    elif r<1.0: buck[3]+=1
    else: buck[4]+=1
print('UP min3 dist 전멸/0-25/25-50/50-99/전승 =',buck,'sum',sum(buck))
# variance variants for UP min4
ds4=[(d,v) for d,v in upsel.items() if len(v)>=4]
k=len(ds4); N=sum(len(v) for _,v in ds4); W=sum(1 for _,v in ds4 for x in v if x['result']=='win'); p=W/N
rates=[sum(1 for x in v if x['result']=='win')/len(v) for _,v in ds4]
mr=sum(rates)/k
print('k',k,'N',N,'p',round(p,4),'nbar',round(N/k,3))
print('pop var about mean %.4f ; about p %.4f ; sample var %.4f'%(sum((r-mr)**2 for r in rates)/k, sum((r-p)**2 for r in rates)/k, sum((r-mr)**2 for r in rates)/(k-1)))
print('exp p(1-p)/nbar %.4f ; mean p(1-p)/n %.4f'%(p*(1-p)/(N/k), sum(p*(1-p)/len(v) for _,v in ds4)/k))
