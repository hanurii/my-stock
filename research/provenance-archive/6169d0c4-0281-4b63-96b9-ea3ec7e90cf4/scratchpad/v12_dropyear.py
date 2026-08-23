# -*- coding: utf-8 -*-
"""플러스 여섯 칸이 한 해를 빼면 정말 마이너스가 되는가."""
import json, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        paths.append({'code':p['code'],'pat':p['pattern'],'sd':p['scan_date'],'ed':p['entry_date'],
                      'E':p['entry_price'],'h':p['h'],'l':p['l'],'c':p['c'],'dt':p['dates']})
    del d
def cell(tg,sp):
    out=[]
    for p in paths:
        E=p['E']; T=E*(1+tg/100); S=E*(1-sp/100); h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=(0,'loss') if i==0 else 'amb'; break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r=='amb': continue
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=r
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':p['dt'][i],'gain':(c[i]/E-1)*100,'result':lb})
    return out
CELLS=[(30,7),(40,7),(40,10),(50,7),(50,10),(50,12),(20,10)]
N=100
print("%-10s %9s %s" % ("칸","전체", " ".join("%8s"%y for y in (2021,2022,2023,2024,2025,2026))))
for tg,sp in CELLS:
    tr=cell(tg,sp)
    full=st.median(slot_sim.sim(tr,seed=i)['equity_pct'] for i in range(N))
    row=[]
    for y in (2021,2022,2023,2024,2025,2026):
        sub=[t for t in tr if t['scan_date'][:4]!=str(y)]
        row.append(st.median(slot_sim.sim(sub,seed=i)['equity_pct'] for i in range(N)))
    nm="+%d/-%d%s" % (tg,sp," (현행)" if (tg,sp)==(20,10) else "")
    print("%-10s %+8.1f%% %s  → 최악 %+.1f%% [%d] %s"
          % (nm, full, " ".join("%+7.1f%%"%v for v in row), min(row),
             (2021,2022,2023,2024,2025,2026)[row.index(min(row))],
             "⚠부호뒤집힘" if full>0 and min(row)<0 else ""))
