# -*- coding: utf-8 -*-
"""③규칙 견고성 + 수수료 + 승자 집중도 + 국면통제 2x2"""
import sys, math, random
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from collections import defaultdict

rows=build()
res=[r for r in rows if r['nres']>0]
lab=[];prev=None;k=0
for r in rows:
    if prev is None or r['days_since_flip']<prev: k+=1
    lab.append(k); prev=r['days_since_flip']
for r,l in zip(rows,lab): r['ep']=l

SLOT=5; SIZE=10_000_000; FEE=0.34   # 왕복 수수료+세금 %
def cutv(key,q,sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]
C=cutv('ret10',0.75, lambda r:r['up'])
R3=lambda r: r['up'] and r['ret10']<C
R1=lambda r: True
R2=lambda r: r['up']

def sim(passfn, subset=None, fee=FEE):
    open_pos=[]; pnl=0.0; taken=[]
    for r in rows:
        D=r['entry_date']
        open_pos=[p for p in open_pos if p[0]>=D]
        free=SLOT-len(open_pos)
        if not passfn(r): continue
        if subset and not subset(r): continue
        for e in sorted(r['events'], key=lambda e:-(e.get('turnover_eok') or 0)):
            if free<=0: break
            g=e['gain_at_resolve_pct']-fee
            open_pos.append((e['resolve_date'],g)); pnl+=SIZE*g/100.0; taken.append((e,g)); free-=1
    w=sum(1 for e,_ in taken if e['result']=='win'); l=sum(1 for e,_ in taken if e['result']=='loss')
    return taken, pnl, w, l

print("=== 수수료·세금 0.34% 반영 슬롯5 시뮬 ===")
YEARS=(date(2026,8,21)-date(2025,11,26)).days/365.0
for nm,fn in (('①전부',R1),('②상승국면',R2),('③상승국면+과열제외',R3)):
    t,p,w,l=sim(fn)
    print(f"{nm:16s} 매수{len(t):3d} 승{w:3d} 패{l:3d} 승률{100*w/(w+l):5.1f}% 건당{sum(g for _,g in t)/len(t):+6.2f}% 총{p:12,.0f}원 연환산{p/YEARS:12,.0f}원 ({100*p/YEARS/(SLOT*SIZE):.0f}%/년)")

print("\n=== 전후반 분할 (진입일 2026-03-25) ===")
for half,sel in (('전반',lambda r:r['entry_date']<'2026-03-25'),('후반',lambda r:r['entry_date']>='2026-03-25')):
    line=f"{half}  "
    for nm,fn in (('①전부',R1),('②상승국면',R2),('③과열제외',R3)):
        t,p,w,l=sim(fn,subset=sel)
        line+=f"| {nm} 매수{len(t):3d} 승률{100*w/(w+l) if w+l else 0:5.1f}% 건당{sum(g for _,g in t)/len(t) if t else 0:+6.2f}% "
    print(line)

print("\n=== 에피소드 하나씩 빼기 (③ vs ①, 건당 수익 차이) ===")
eps=sorted(set(r['ep'] for r in rows))
t3,_,w3,l3=sim(R3); t1,_,w1,l1=sim(R1)
base=sum(g for _,g in t3)/len(t3) - sum(g for _,g in t1)/len(t1)
print(f"전체: ③ {sum(g for _,g in t3)/len(t3):+.2f}% - ① {sum(g for _,g in t1)/len(t1):+.2f}% = {base:+.2f}%p")
for e in eps:
    sel=lambda r,e=e: r['ep']!=e
    a,_,aw,al=sim(R3,subset=sel); b,_,bw,bl=sim(R1,subset=sel)
    if not a or not b: continue
    d=sum(g for _,g in a)/len(a) - sum(g for _,g in b)/len(b)
    print(f"  #{e} 제외 → 차이 {d:+.2f}%p (③매수{len(a)} 승률{100*aw/(aw+al) if aw+al else 0:.0f}%)")

print("\n=== ③ 규칙 승자 집중도 (상위 수익 몇 건이 이익의 몇 %) ===")
gs=sorted((g for _,g in t3), reverse=True)
tot=sum(gs)
for k in (1,3,5):
    print(f"  상위 {k}건이 총이익의 {100*sum(gs[:k])/tot:.0f}%")

print("\n=== 국면 통제 2x2 (상승국면 안에서, 지수10일 과열 × 신고가비율 과열) ===")
up=[r for r in res if r['up']]
c10=cutv('ret10',0.75, lambda r:r['up']); cnh=cutv('pct_nh52',0.75, lambda r:r['up'])
for a in (False,True):
    for b in (False,True):
        g=[r for r in up if (r['ret10']>=c10)==a and (r['pct_nh52']>=cnh)==b]
        w=sum(r['w'] for r in g); l=sum(r['l'] for r in g)
        print(f"  지수10일 과열={'예' if a else '아니오'} · 신고가 과열={'예' if b else '아니오'}: 날{len(g):3d} 거래{w+l:3d} 승률 {100*w/(w+l) if w+l else 0:5.1f}%")

print("\n=== 그림자 검사: 후보 수·시장폭이 국면 통제 뒤에도 남나 (상승국면 안 4분위) ===")
for key,name in (('n_candidates','그날 후보 수'),('ad','그날 상승종목 비율'),('ad_liq','상승비율(유동성)')):
    vs=sorted(r[key] for r in up)
    cuts=[vs[int(len(vs)*i/4)] for i in (1,2,3)]
    out=[]
    for i in range(4):
        g=[r for r in up if (i==0 and r[key]<cuts[0]) or (i==3 and r[key]>=cuts[2]) or (0<i<3 and cuts[i-1]<=r[key]<cuts[i])]
        w=sum(r['w'] for r in g); l=sum(r['l'] for r in g)
        out.append(f"Q{i+1} {100*w/(w+l) if w+l else 0:.0f}%({w+l})")
    print(f"  {name:18s} " + " · ".join(out))
