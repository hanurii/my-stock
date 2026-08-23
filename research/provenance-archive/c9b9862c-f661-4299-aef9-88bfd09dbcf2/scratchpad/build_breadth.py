import json, os, sys
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix as om

SD = str(om.SERIES_DIR)
files = [f for f in os.listdir(SD) if f.endswith('.json')]
# date -> counters
from collections import defaultdict
up = defaultdict(int); dn = defaultdict(int); flat = defaultdict(int)
up3 = defaultdict(int); dn3 = defaultdict(int)
above20 = defaultdict(int); above50 = defaultdict(int); above200 = defaultdict(int); tot = defaultdict(int)
nh = defaultdict(int); nl = defaultdict(int)

for i,f in enumerate(files):
    try:
        s = json.load(open(os.path.join(SD,f),encoding='utf-8'))
    except Exception:
        continue
    ds = s['dates']; cl = s['closes']; vol = s.get('volumes') or []
    n = len(ds)
    if n < 60: continue
    # rolling means
    run20=0.0; run50=0.0; run200=0.0
    for j in range(n):
        c = cl[j]
        if c is None or c<=0: continue
        # volume 0 -> halted, skip
        if vol and j < len(vol) and vol[j] == 0: continue
        d = ds[j]
        tot[d]+=1
        if j>0 and cl[j-1] and cl[j-1]>0:
            r = c/cl[j-1]-1
            if r>0.0005: up[d]+=1
            elif r<-0.0005: dn[d]+=1
            else: flat[d]+=1
            if r>=0.03: up3[d]+=1
            if r<=-0.03: dn3[d]+=1
        if j>=19:
            w=[x for x in cl[j-19:j+1] if x]
            if w and c> sum(w)/len(w): above20[d]+=1
        if j>=49:
            w=[x for x in cl[j-49:j+1] if x]
            if w and c> sum(w)/len(w): above50[d]+=1
        if j>=199:
            w=[x for x in cl[j-199:j+1] if x]
            if w and c> sum(w)/len(w): above200[d]+=1
        if j>=249:
            w=[x for x in cl[j-249:j+1] if x]
            if w and c>=max(w): nh[d]+=1
            if w and c<=min(w): nl[d]+=1

dates = sorted(tot)
out=[]
for d in dates:
    t=tot[d]
    if t<200: continue
    out.append(dict(date=d, n=t,
        adv=up[d], dec=dn[d],
        adv_pct=round(100*up[d]/max(1,up[d]+dn[d]),2),
        up3_pct=round(100*up3[d]/t,2), dn3_pct=round(100*dn3[d]/t,2),
        a20=round(100*above20[d]/t,2), a50=round(100*above50[d]/t,2), a200=round(100*above200[d]/t,2),
        nh=nh[d], nl=nl[d], nh_pct=round(100*nh[d]/t,3)))
json.dump(out, open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/breadth.json','w',encoding='utf-8'))
print('dates',len(out), out[0]['date'], out[-1]['date'])
print(out[-1])
