import json, math
from collections import defaultdict, Counter
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
# mixed regime within an entry day?
byday=defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
mixed=0
for d,v in byday.items():
    s=set(reg[x['scan_date']] for x in v)
    if len(s)>1: mixed+=1
print('entry days',len(byday),'mixed-regime days',mixed)
# lag structure
lag=Counter()
for x in ev:
    lag[(reg[x['scan_date']],reg[x['entry_date']])]+=1
print('(scan_up,entry_up) counts',dict(lag))

# --- DOWN-regime days: wipeout rate ---
dnsel={}
for d,v in byday.items():
    u=[x for x in v if not reg[x['scan_date']]]
    if u: dnsel[d]=u
def report(sel,minn,label):
    ds=[(d,v) for d,v in sorted(sel.items()) if len(v)>=minn]
    if not ds: print(label,'no days'); return
    k=len(ds); N=sum(len(v) for _,v in ds); W=sum(1 for _,v in ds for x in v if x['result']=='win'); p=W/N
    z=sum(1 for _,v in ds if all(x['result']=='loss' for x in v))
    expz=sum((1-p)**len(v) for _,v in ds)
    print('%-14s min%d days=%2d N=%3d p=%.3f wipeout=%d (%.0f%%) exp=%.1f (%.0f%%)'%(label,minn,k,N,p,z,100*z/k,expz,100*expz/k))
upsel={}
for d,v in byday.items():
    u=[x for x in v if reg[x['scan_date']]]
    if u: upsel[d]=u
for m in (2,3,4):
    report(upsel,m,'UP(scan)'); report(dnsel,m,'DOWN(scan)')
print()
# distinct correction calendar clusters
dnd=sorted(set(x['scan_date'] for x in ev if not reg[x['scan_date']]))
print('correction scan-days with entries:',len(dnd))
# cluster into runs
runs=[]; cur=[dnd[0]]
alld=sorted(reg)
idx={d:i for i,d in enumerate(alld)}
for a,b in zip(dnd,dnd[1:]):
    if idx[b]-idx[a]<=3: cur.append(b)
    else: runs.append(cur); cur=[b]
runs.append(cur)
print('correction episodes:',len(runs))
for r in runs:
    n=sum(1 for x in ev if x['scan_date'] in r); w=sum(1 for x in ev if x['scan_date'] in r and x['result']=='win')
    print('  %s..%s  days=%d trades=%d wins=%d (%.0f%%)'%(r[0],r[-1],len(r),n,w,100*w/n if n else 0))
