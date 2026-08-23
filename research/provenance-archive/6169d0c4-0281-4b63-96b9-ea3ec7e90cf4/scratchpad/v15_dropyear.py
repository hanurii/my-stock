# -*- coding: utf-8 -*-
import json, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        paths.append({'code':p['code'],'pat':p['pattern'],'sd':p['scan_date'],'ed':p['entry_date'],
                      'E':p['entry_price'],'o':p['o'],'h':p['h'],'l':p['l'],'c':p['c'],'dt':p['dates']})
    del d
def resolve(p, day=None):
    E=p['E']; T=E*1.20; S=E*0.90; o,h,l,c=p['o'],p['h'],p['l'],p['c']; n=len(c)
    for i in range(n):
        ht,hs=h[i]>=T,l[i]<=S
        if ht and hs: return i,'loss',(c[i]/E-1)*100
        if ht: return i,'win',(c[i]/E-1)*100
        if hs: return i,'loss',(c[i]/E-1)*100
        if day is not None and i==day and (c[i]/E-1)*100 <= -5.0:
            if i+1<n:
                g=(o[i+1]/E-1)*100; return i+1,('win' if g>0 else 'loss'),g
            g=(c[i]/E-1)*100; return i,('win' if g>0 else 'loss'),g
    g=(c[-1]/E-1)*100; return n-1,('win' if g>0 else 'loss'),g
def mk(day):
    out=[]
    for p in paths:
        i,lb,g=resolve(p,day)
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':p['dt'][i],'gain':g,'result':lb})
    return out
B=mk(None); V=mk(5); N=100
print("%-12s %10s %10s %10s" % ("","현행","변형2","차이"))
fb=st.median(slot_sim.sim(B,seed=i)['equity_pct'] for i in range(N))
fv=st.median(slot_sim.sim(V,seed=i)['equity_pct'] for i in range(N))
print("%-12s %+9.1f%% %+9.1f%% %+9.1f%%p" % ("전체", fb, fv, fv-fb))
for y in ('2021','2022','2023','2024','2025','2026'):
    b=[t for t in B if t['scan_date'][:4]!=y]; v=[t for t in V if t['scan_date'][:4]!=y]
    eb=st.median(slot_sim.sim(b,seed=i)['equity_pct'] for i in range(N))
    ev=st.median(slot_sim.sim(v,seed=i)['equity_pct'] for i in range(N))
    print("%-12s %+9.1f%% %+9.1f%% %+9.1f%%p %s" % (y+" 제외", eb, ev, ev-eb,
          "← 변형2도 플러스" if ev>0 else ""))
