# -*- coding: utf-8 -*-
import sys, json, random, math
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from pathlib import Path
rows=build(); res=[r for r in rows if r['nres']>0]

# 1) 신고가비율 규칙이 조정국면·전체에서도 되나
def split(sub,C):
    hot=[r for r in sub if r['pct_nh52']>=C]; cool=[r for r in sub if r['pct_nh52']<C]
    f=lambda g:(sum(r['w'] for r in g), sum(r['l'] for r in g))
    (wh,lh),(wc,lc)=f(hot),f(cool)
    return (100*wh/(wh+lh) if wh+lh else None, wh+lh, 100*wc/(wc+lc) if wc+lc else None, wc+lc)
def cutv(key,q,sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]
Cup=cutv('pct_nh52',0.80,lambda r:r['up'])
print(f"신고가비율 '과열' 컷 = {Cup:.2f}% (상승국면 날의 상위 20%)")
for lab,sub in (('전체',res),('상승국면',[r for r in res if r['up']]),('조정국면',[r for r in res if not r['up']])):
    a,na,b,nb=split(sub,Cup)
    print(f"  {lab:6s}: 과열날 {a if a is None else round(a,1)}%({na}) vs 평소날 {b if b is None else round(b,1)}%({nb})")

# 2) 슬롯5 시뮬 — 신고가비율 규칙
SLOT=5; SIZE=10_000_000; FEE=0.34
YEARS=(date(2026,8,21)-date(2025,11,26)).days/365.0
def sim(passfn, fee=FEE):
    op=[]; pnl=0; taken=[]
    for r in rows:
        D=r['entry_date']; op=[p for p in op if p[0]>=D]; free=SLOT-len(op)
        if not passfn(r): continue
        for e in sorted(r['events'], key=lambda e:-(e.get('turnover_eok') or 0)):
            if free<=0: break
            g=e['gain_at_resolve_pct']-fee
            op.append((e['resolve_date'],g)); pnl+=SIZE*g/100; taken.append((e,g)); free-=1
    w=sum(1 for e,_ in taken if e['result']=='win'); l=sum(1 for e,_ in taken if e['result']=='loss')
    ev=sum(g for _,g in taken)/len(taken) if taken else 0
    # 최대 낙폭(누적 손익 곡선)
    op2=sorted(((e['resolve_date'],g) for e,g in taken))
    cum=0; peak=0; mdd=0
    for d,g in op2:
        cum+=SIZE*g/100; peak=max(peak,cum); mdd=min(mdd,cum-peak)
    return dict(n=len(taken),w=w,l=l,wr=100*w/(w+l) if w+l else 0,ev=ev,pnl=pnl,ann=pnl/YEARS,mdd=mdd,
                days=sum(1 for r in rows if passfn(r)))
Cr10=cutv('ret10',0.75,lambda r:r['up'])
RULES=[('①전부 산다(현행)', lambda r:True),
       ('②상승국면 날만', lambda r:r['up']),
       ('③상승국면 + 신고가과열일 쉼', lambda r:r['up'] and r['pct_nh52']<Cup),
       ('④신고가과열일만 쉼(국면 무시)', lambda r:r['pct_nh52']<Cup),
       ('⑤상승국면 + 신고가과열 + 지수10일과열 둘다 쉼', lambda r:r['up'] and r['pct_nh52']<Cup and r['ret10']<Cr10)]
print(f"\n=== 슬롯5 × 1,000만원 (수수료·세금 0.34% 차감), {YEARS:.2f}년 ===")
print(f"{'규칙':40s}{'매매일':>6s}{'매수':>5s}{'승률':>7s}{'건당':>8s}{'총손익':>13s}{'연환산':>13s}{'연%':>7s}{'최대낙폭':>13s}")
for nm,fn in RULES:
    s=sim(fn)
    print(f"{nm:40s}{s['days']:6d}{s['n']:5d}{s['wr']:6.1f}%{s['ev']:+7.2f}%{s['pnl']:13,.0f}{s['ann']:13,.0f}{100*s['ann']/(SLOT*SIZE):6.0f}%{s['mdd']:13,.0f}")

# 3) 전멸일 감소 효과
print("\n=== '전멸(0승)' 하루 빈도 변화 (4건+ 진입일 기준) ===")
for nm,fn in (('전부',lambda r:True),('상승국면만',lambda r:r['up']),('상승국면+신고가과열 쉼',lambda r:r['up'] and r['pct_nh52']<Cup)):
    g=[r for r in res if r['nres']>=4 and fn(r)]
    z=sum(1 for r in g if r['w']==0)
    print(f"  {nm:22s} 해당일 {len(g):3d}일 중 전멸 {z:2d}일 ({100*z/len(g) if g else 0:.0f}%)")

# 4) 지금(2026-08-21) 값
SP=Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
br=json.loads((SP/"breadth_series.json").read_text(encoding='utf-8'))
i=len(br['dates'])-1
print(f"\n=== 오늘 기준 값 ({br['dates'][i]}) ===")
print(f"  52주 신고가 종목 비율 = {100*br['nh52'][i]/br['tot52'][i]:.2f}%  (과열 컷 {Cup:.2f}%) → {'과열(쉬어라)' if 100*br['nh52'][i]/br['tot52'][i]>=Cup else '평소(사도 되는 날)'}")
print(f"  200일선 위 종목 비율 = {100*br['above200'][i]/br['tot200'][i]:.1f}%")
reg=json.loads(Path(r'C:\Users\hanul\playground\my-stock\public\data\market-regime.json').read_text(encoding='utf-8'))
print(f"  국면 = {'상승' if reg['series'][-1]['up'] else '조정'} ({reg['series'][-1]['date']})")
