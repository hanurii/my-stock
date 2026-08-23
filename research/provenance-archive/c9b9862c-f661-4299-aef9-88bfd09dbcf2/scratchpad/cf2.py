# -*- coding: utf-8 -*-
import sys, json, os, statistics
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load, simulate, series
rows = json.load(open(os.path.join(SCR,"rows.json"), encoding="utf-8"))
sc = load("scorecard.json"); T={(t['code'],t['open_date']):t for t in sc['trades']}
FEE=0.34

# 조기청산 승자 20건: 붙잡았으면 +20% 갔을까?
early=[r for r in rows if r['outcome']=='win' and r['gross_pct']<20]
hit=0; res=[]
for r in early:
    t=T[(r['code'],r['d'])]
    s=simulate(r['code'], r['d'], t['avg_buy'], 20, -10, last_date='2026-08-21')
    res.append((r['name'], r['d'], r['net_pct'], s['result'], round(s['gain'],2) if s['gain'] is not None else None, round(s['mg'],1)))
    if s['result']=='win': hit+=1
print(f"조기청산 승자 {len(early)}건을 +20/-10 규칙으로 붙잡았다면: 목표달성 {hit}건, 손절 {sum(1 for x in res if x[3]=='loss')}건, 미결 {sum(1 for x in res if x[3]=='unresolved')}건")
for x in sorted(res,key=lambda y:y[2]): print("   ",x)
print()
# 월별 반사실1
for lab, sel in [("7월 매수", [r for r in rows if r['d']<'2026-08-01']), ("8월 매수",[r for r in rows if r['d']>='2026-08-01'])]:
    tot=0; w=l=o=0; gs=[]
    for r in sel:
        t=T[(r['code'],r['d'])]; s=simulate(r['code'],r['d'],t['avg_buy'],20,-10,last_date='2026-08-21')
        g=s['gain']; st=s['result']
        if st=='ambiguous': g=-10; st='loss'
        if st=='win': w+=1
        elif st=='loss': l+=1
        else: o+=1
        gs.append(g-FEE); tot += t['avg_buy']*t['buy_qty']*(g-FEE)/100
    real=sum(r['net_won'] for r in sel); rw=sum(1 for r in sel if r['outcome']=='win')
    print(f"{lab} {len(sel)}건 | 실제: 승{rw}({100*rw/len(sel):.1f}%) {real:,.0f}원  →  +20/-10 유지: 승{w}·패{l}·미청산{o} ({100*w/(w+l) if w+l else 0:.1f}%) {tot:,.0f}원  평균{statistics.mean(gs):+.2f}%")
print()
# 피벗 기준 기계적 진입 (entry_ready 건만)
tot=0; w=l=o=0; n=0
for r in rows:
    if not r['entry_ready'] or not r['pivot']: continue
    t=T[(r['code'],r['d'])]; s=series(r['code'])
    try: i=s['dates'].index(r['d'])
    except ValueError: continue
    if s['highs'][i] < r['pivot']: continue   # 그날 피벗 미돌파 -> 미진입
    ep=max(r['pivot'], s['opens'][i])
    sim=simulate(r['code'], r['d'], ep, 20, -10, last_date='2026-08-21')
    g=sim['gain']; st=sim['result']
    if st=='ambiguous': g=-10; st='loss'
    if st=='win': w+=1
    elif st=='loss': l+=1
    else: o+=1
    n+=1; tot += t['avg_buy']*t['buy_qty']*(g-FEE)/100
print(f"기계적 진입(피벗 돌파가 = max(피벗, 시가)) + 20/-10: {n}건 승{w}·패{l}·미청산{o} 승률 {100*w/(w+l) if w+l else 0:.1f}%  손익 {tot:,.0f}원")
