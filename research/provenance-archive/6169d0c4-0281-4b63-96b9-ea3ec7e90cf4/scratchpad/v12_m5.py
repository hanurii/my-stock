# -*- coding: utf-8 -*-
"""문턱 5 진단 — 귀무 분포의 넓이가 '달력 재추출' 때문인가 '무작위 순서' 때문인가.

핵심: 관측 통계는 400회 중앙값인데 귀무 통계는 매 복제마다 seed 하나짜리다.
달력을 전혀 바꾸지 않고(항등 블록) 같은 중심화 최대통계를 만들어 보면,
그 넓이가 순전히 seed 잡음에서 오는 몫이다.
"""
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

def cell(tg, sp):
    """판 (가) — 매수 당일 손절/동시접촉은 그날 종가 손실로 편입,
       그 뒤 날의 목표·손절 동시 접촉은 ambiguous 로 제외(조사 세션과 동일)."""
    out=[]; namb=0
    for p in paths:
        E=p['E']; T=E*(1+tg/100); S=E*(1-sp/100); h,l,c,dt=p['h'],p['l'],p['c'],p['dt']
        r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs:
                if i==0: r=(0,'loss')           # 매수 당일 = M1 편입
                else:    r='amb'                 # 이후 날 동시접촉 = 제외
                break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r=='amb': namb+=1; continue
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=r
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':dt[i],'gain':(c[i]/E-1)*100,'result':lb,'days_held':i})
    return out, namb

TG=[15,20,25,30,40,50]; SP=[5,7,10,12]
N=200
cells={}; 
for tg in TG:
    for sp in SP:
        tr,namb = cell(tg,sp); cells[(tg,sp)] = tr
        if (tg,sp) in ((20,10),(50,7),(15,5)):
            print("  +%d/-%d 확정 %d (제외 %d)" % (tg,sp,len(tr),namb))
print("적재 완료 — 슬롯5 %d칸 × %d seed" % (len(cells), N), flush=True)
E={}
for k,tr in cells.items():
    E[k]=[slot_sim.sim(tr,seed=i)['equity_pct'] for i in range(N)]
    print("   +%d/-%d 중앙 %+.1f%%" % (k[0],k[1],st.median(E[k])), flush=True)
base=E[(20,10)]
obs={k: st.median([E[k][i]-base[i] for i in range(N)]) for k in cells if k!=(20,10)}
obs_max_cell=max(obs,key=obs.get); obs_max=obs[obs_max_cell]
print("\n관측 최고 칸 +%d/-%d · 관측 우위 %+.1f%%p" % (obs_max_cell[0],obs_max_cell[1],obs_max))
stat=[max(E[k][i]-base[i]-obs[k] for k in obs) for i in range(N)]
ss=sorted(stat)
print("\n★ 달력을 전혀 바꾸지 않은 '항등 귀무' (무작위 순서 잡음만):")
print("   중앙 %+.1f · 95%% 분위 %+.1f · 최대 %+.1f" % (st.median(ss), ss[int(N*.95)], ss[-1]))
print("   → 조사 세션 부트스트랩 귀무 95%% 분위 = +358.2%%p")
print("   → 관측 통계(400회 중앙) = %+.1f%%p" % obs_max)
print("\n   항등 귀무만으로 계산한 p = %.3f" % (sum(1 for x in stat if x>=obs_max)/N))
