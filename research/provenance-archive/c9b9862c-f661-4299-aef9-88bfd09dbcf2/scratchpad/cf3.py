# -*- coding: utf-8 -*-
import sys, json, os, statistics
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load, simulate, series
rows = sorted(json.load(open(os.path.join(SCR,"rows.json"), encoding="utf-8")), key=lambda r:(r['d'], r['code']))
sc = load("scorecard.json"); T={(t['code'],t['open_date']):t for t in sc['trades']}
FEE=0.34

def run(target, stop, slots=None, label=""):
    open_pos={}   # code -> resolve_date
    taken=[]; skipped=[]
    for r in rows:
        d=r['d']
        # 만료 정리
        for c in list(open_pos):
            if open_pos[c] is not None and open_pos[c] < d: del open_pos[c]
        if r['code'] in open_pos:
            skipped.append(r); continue
        if slots and len(open_pos)>=slots:
            skipped.append(r); continue
        t=T[(r['code'],d)]
        s=simulate(r['code'], d, t['avg_buy'], target, stop, last_date='2026-08-21')
        if s is None: continue
        g=s['gain']; st=s['result']
        if st=='ambiguous': g=stop; st='loss'
        won=t['avg_buy']*t['buy_qty']*(g-FEE)/100
        taken.append(dict(r=r, st=st, g=g, won=won))
        open_pos[r['code']] = s['resolve'] if st in ('win','loss') else None
    w=sum(1 for x in taken if x['st']=='win'); l=sum(1 for x in taken if x['st']=='loss')
    o=len(taken)-w-l
    tot=sum(x['won'] for x in taken)
    print(f"{label}: 진입 {len(taken)}건(중복차단 {len(skipped)}건) 승{w}·패{l}·미청산{o} 승률 {100*w/(w+l) if w+l else 0:.1f}% 손익 {tot:,.0f}원 평균 {statistics.mean([x['g']-FEE for x in taken]):+.2f}%")
    return taken, skipped

print("실제: 63건 승21 33.3% -5,029,999원")
run(20,-10,None,"반사실 +20/-10 (같은 종목 중복 매수 차단)")
run(20,-10,5,"반사실 +20/-10 + 슬롯5 제한        ")
run(10,-5,None,"참고: +10/-5 유지                  ")
run(20,-5,None,"참고: +20/-5                       ")
run(15,-7.5,None,"참고: +15/-7.5                     ")
run(30,-10,None,"참고: +30/-10                      ")
