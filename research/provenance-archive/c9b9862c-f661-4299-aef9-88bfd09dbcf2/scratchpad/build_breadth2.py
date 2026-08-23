import json, os, sys
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix as om
from collections import defaultdict
SD = str(om.SERIES_DIR)
files = [f for f in os.listdir(SD) if f.endswith('.json')]
C = lambda: defaultdict(int)
up,dn,up3,dn3 = C(),C(),C(),C()
a20,a50,a200 = C(),C(),C()
d20,d50,d200 = C(),C(),C()
nh,nl,dnh = C(),C(),C()
tot=C()
for f in files:
    try: s = json.load(open(os.path.join(SD,f),encoding='utf-8'))
    except Exception: continue
    ds=s['dates']; cl=s['closes']; vol=s.get('volumes') or []
    n=len(ds)
    for j in range(n):
        c=cl[j]
        if not c or c<=0: continue
        if vol and j<len(vol) and vol[j]==0: continue
        d=ds[j]; tot[d]+=1
        if j>0 and cl[j-1]:
            r=c/cl[j-1]-1
            if r>0.0005: up[d]+=1
            elif r<-0.0005: dn[d]+=1
            if r>=0.03: up3[d]+=1
            if r<=-0.03: dn3[d]+=1
        for w,acc,den in ((20,a20,d20),(50,a50,d50),(200,a200,d200)):
            if j>=w-1:
                win=[x for x in cl[j-w+1:j+1] if x]
                if len(win)==w:
                    den[d]+=1
                    if c>sum(win)/w: acc[d]+=1
        if j>=249:
            win=[x for x in cl[j-249:j+1] if x]
            if len(win)==250:
                dnh[d]+=1
                if c>=max(win): nh[d]+=1
                if c<=min(win): nl[d]+=1
out=[]
for d in sorted(tot):
    t=tot[d]
    if t<200: continue
    pc=lambda a,b: round(100*a/b,2) if b else None
    out.append(dict(date=d,n=t,adv=up[d],dec=dn[d],adv_pct=pc(up[d],up[d]+dn[d]),
        up3_pct=pc(up3[d],t),dn3_pct=pc(dn3[d],t),
        a20=pc(a20[d],d20[d]),a50=pc(a50[d],d50[d]),a200=pc(a200[d],d200[d]),
        nh_pct=pc(nh[d],dnh[d]),nl_pct=pc(nl[d],dnh[d]),nh_den=dnh[d]))
json.dump(out,open('breadth.json','w',encoding='utf-8'))
print(len(out))
for r in out[-3:]: print(r)
for r in out[:2]: print(r)
