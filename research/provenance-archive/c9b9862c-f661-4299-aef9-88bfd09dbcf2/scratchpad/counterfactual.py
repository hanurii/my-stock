# -*- coding: utf-8 -*-
import sys, json, os, collections, statistics
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load, series, simulate
rows = json.load(open(os.path.join(SCR,"rows.json"), encoding="utf-8"))
sc = load("scorecard.json"); trades={ (t['code'],t['open_date']):t for t in sc['trades'] }
FEE = 0.14+0.20   # 왕복 비용 근사 (%) — 실제 정산표 net-gross 차이와 유사

def run(sel, target, stop, label, mark_open=True):
    out=[]
    for r in sel:
        t = trades[(r['code'], r['d'])]
        notional = t['avg_buy']*t['buy_qty']
        res = simulate(r['code'], r['d'], t['avg_buy'], target, stop, last_date='2026-08-21')
        if res is None: continue
        g = res['gain']
        st = res['result']
        if st=='ambiguous': g = stop; st='loss'
        if st=='unresolved':
            if not mark_open: continue
            st = 'open'
        gn = g - FEE
        out.append(dict(code=r['code'], name=r['name'], d=r['d'], st=st, g=g, gn=gn,
                        won=notional*gn/100.0, notional=notional, real=t['net_won'], realpct=t['net_pct']))
    n=len(out); w=sum(1 for o in out if o['st']=='win'); l=sum(1 for o in out if o['st']=='loss')
    op=sum(1 for o in out if o['st']=='open')
    tot=sum(o['won'] for o in out)
    dec=w+l
    print(f"{label}: {n}건 (확정 {dec}: 승{w}·패{l}, 미청산 {op})  승률={100*w/dec if dec else 0:.1f}%  "
          f"평균={statistics.mean([o['gn'] for o in out]) if out else 0:+.2f}%  손익합={tot:>12,.0f}원")
    return out

print("실제 성적: 63건 승21 승률 33.3% 손익합 -5,029,999원 (평균 -1.83%)")
print()
print("=== 반사실 1: 실제 매수가·매수일 그대로, 청산만 백테스트 규칙(+20/-10) ===")
a=run(rows, 20, -10, "63건 전부")
print()
print("=== 반사실 2: 진입 필터도 백테스트 규칙 (entry_ready 종목만) + 청산 +20/-10 ===")
b=run([r for r in rows if r['entry_ready']], 20, -10, "entry_ready 44건만")
print()
print("=== 반사실 3: entry_ready + 상승국면만 + 청산 +20/-10 ===")
c=run([r for r in rows if r['entry_ready'] and r['up']], 20, -10, "entry_ready & 상승국면")
print()
print("=== 참고: 규칙 밖 진입(a+b1) 11건을 안 샀다면 (나머지는 실제 성적 그대로) ===")
keep=[r for r in rows if r['listed'] and r['detected']]
n=len(keep); w=sum(1 for r in keep if r['outcome']=='win'); tot=sum(r['net_won'] for r in keep)
print(f"  {n}건 승={w} 승률={100*w/n:.1f}% 손익합={tot:,.0f}원 (실제 -5,029,999원)")
print()
print("=== 참고: 조정국면(7월~8/3) 매수를 안 했다면 ===")
keep2=[r for r in rows if r['up']]
n=len(keep2); w=sum(1 for r in keep2 if r['outcome']=='win'); tot=sum(r['net_won'] for r in keep2)
print(f"  상승국면 매수만 {n}건 승={w} 승률={100*w/n:.1f}% 손익합={tot:,.0f}원")
keep3=[r for r in rows if r['up'] and r['detected']]
n=len(keep3); w=sum(1 for r in keep3 if r['outcome']=='win'); tot=sum(r['net_won'] for r in keep3)
print(f"  상승국면 & 패턴검출 {n}건 승={w} 승률={100*w/n:.1f}% 손익합={tot:,.0f}원")
keep4=[r for r in rows if r['up'] and r['entry_ready']]
n=len(keep4); w=sum(1 for r in keep4 if r['outcome']=='win'); tot=sum(r['net_won'] for r in keep4)
print(f"  상승국면 & entry_ready {n}건 승={w} 승률={100*w/n:.1f}% 손익합={tot:,.0f}원")
json.dump(a, open(os.path.join(SCR,"cf1.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
