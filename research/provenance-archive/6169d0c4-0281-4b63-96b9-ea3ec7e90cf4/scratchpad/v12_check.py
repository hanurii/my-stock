# -*- coding: utf-8 -*-
"""12번 독립 검증 1부 — 격자 값 재현 + 짝비교 차이의 분포(단일 seed) 계량."""
import json, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"

paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    modal=collections.Counter(p['dates'][-1] for p in d['paths']).most_common(1)[0][0]
    for p in d['paths']:
        paths.append({'code':p['code'],'pat':p['pattern'],'sd':p['scan_date'],'ed':p['entry_date'],
                      'E':p['entry_price'],'h':p['h'],'l':p['l'],'c':p['c'],'dt':p['dates'],
                      'dead':p['dates'][-1]!=modal})
    del d
print("경로 %d건 적재" % len(paths))

def cell_trades(tg, sp):
    """판 (가): 매수 당일 손절·동시접촉도 그날 종가 체결 손실로 편입."""
    out=[]
    for p in paths:
        E=p['E']; T=E*(1+tg/100); S=E*(1-sp/100); h,l,c,dt=p['h'],p['l'],p['c'],p['dt']
        r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=(i,'loss'); break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r is None:
            g=(c[-1]/E-1)*100
            r=(len(c)-1, 'win' if g>0 else 'loss')
        i,lb=r
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':dt[i],'gain':(c[i]/E-1)*100,'result':lb,'days_held':i})
    return out

base=cell_trades(20,10)
best=cell_trades(50,7)
N=400
eb=[slot_sim.sim(base,seed=i)['equity_pct'] for i in range(N)]
ec=[slot_sim.sim(best,seed=i)['equity_pct'] for i in range(N)]
print("\n[격자 재현] +20/-10 중앙(200회) %+.1f%%   결과파일 -32.4%%" % st.median(eb[:200]))
print("[격자 재현] +50/-7  중앙(200회) %+.1f%%   결과파일 +40.8%%" % st.median(ec[:200]))
d=[ec[i]-eb[i] for i in range(N)]
ds=sorted(d)
print("\n[짝비교] +50/-7 vs 현행, 같은 seed 400회")
print("  우세율 %.1f%% (결과파일 89.0%%) · 차이 중앙 %+.1f%%p (결과파일 +67.6%%p)"
      % (sum(1 for x in d if x>0)/N*100, st.median(d)))
print("  차이의 분포: 5%% %+.1f · 25%% %+.1f · 75%% %+.1f · 95%% %+.1f · 최대 %+.1f"
      % (ds[int(N*.05)], ds[int(N*.25)], ds[int(N*.75)], ds[int(N*.95)], ds[-1]))
print("\n★ 핵심 대조")
print("  관측 통계(400회 중앙)          = %+.1f%%p" % st.median(d))
print("  같은 자료 · 단일 seed 차이의 95%% = %+.1f%%p" % ds[int(N*.95)])
print("  부트스트랩 귀무 95%% 분위(결과파일) = +358.2%%p")
