# -*- coding: utf-8 -*-
import sys, json, os, statistics, collections, math
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load, simulate
snap = json.load(open(os.path.join(SCR,"cand_hist.json"), encoding="utf-8"))
rows = json.load(open(os.path.join(SCR,"rows.json"), encoding="utf-8"))
sc = load("scorecard.json"); T={(t['code'],t['open_date']):t for t in sc['trades']}
asofs=sorted(snap)

def sameday_detect(code, d):
    """매수 당일 저녁 스냅샷에서 검출/entry_ready 여부"""
    if d not in snap: return None
    det=False; er=False
    for pat in ("VCP","3C","PP"):
        r=snap[d].get(pat,{}).get(code)
        if r:
            det = det or bool(r.get("detected"))
            er = er or bool(r.get("entry_ready"))
    return dict(det=det, er=er)

for r in rows:
    sd = sameday_detect(r['code'], r['d'])
    r['sd_det'] = sd['det'] if sd else None
    r['sd_er']  = sd['er'] if sd else None

def agg(sel,label):
    if not sel: print(f"{label}: 0건"); return
    n=len(sel); w=sum(1 for x in sel if x['outcome']=='win'); s=sum(x['net_won'] for x in sel)
    print(f"{label}: {n}건 승{w} ({100*w/n:.1f}%) 손익 {s:>12,.0f}원 평균 {statistics.mean([x['net_pct'] for x in sel]):+.2f}%")

print("=== 진입 시점 신호 상태 (전일 스냅샷 = 매수 아침에 볼 수 있던 것) ===")
g1=[r for r in rows if r['entry_ready']]
g2=[r for r in rows if not r['entry_ready'] and r['detected']]
g3=[r for r in rows if not r['detected'] and r['sd_det']]      # 전일 미검출인데 당일 저녁 검출 = 돌파 당일 매수
g4=[r for r in rows if not r['detected'] and not r['sd_det']]  # 전일도 당일도 미검출 = 완전 규칙 밖
agg(g1,"①전일 entry_ready (규칙대로)         ")
agg(g2,"②전일 검출됐지만 피벗 전(forming)     ")
agg(g3,"③전일 미검출·당일 저녁 검출(돌파당일) ")
agg(g4,"④전일·당일 모두 미검출(완전 규칙밖)   ")
print()
for r in g4: print(f"   ④ {r['d']} {r['name']} net={r['net_pct']:+.2f}% {r['net_won']:,.0f}원 | {r['note'][:60]}")
print()
for r in g3: print(f"   ③ {r['d']} {r['name']} net={r['net_pct']:+.2f}% {r['net_won']:,.0f}원")
print()
print("=== ④를 안 샀다면 ===")
keep=[r for r in rows if not (not r['detected'] and not r['sd_det'])]
w=sum(1 for r in keep if r['outcome']=='win')
print(f"   {len(keep)}건 승{w} ({100*w/len(keep):.1f}%) 손익 {sum(r['net_won'] for r in keep):,.0f}원 (실제 -5,029,999원)")
print("=== ③+④를 안 샀다면 (신호 확정 다음날 진입 원칙) ===")
keep2=[r for r in rows if r['detected']]
w=sum(1 for r in keep2 if r['outcome']=='win')
print(f"   {len(keep2)}건 승{w} ({100*w/len(keep2):.1f}%) 손익 {sum(r['net_won'] for r in keep2):,.0f}원")
print()
print("=== ③ 종목을 '익일 피벗 돌파 진입'으로 미뤘다면 (백테 규칙) ===")
tot=0; det=[]
for r in g3:
    t=T[(r['code'],r['d'])]
    # 당일 저녁 스냅샷의 피벗
    piv=None
    for pat in ("VCP","3C","PP"):
        rec=snap[r['d']].get(pat,{}).get(r['code'])
        if rec and rec.get('detected') and rec.get('pivot'): piv=rec['pivot']; break
    from lib import series
    s=series(r['code']); i=s['dates'].index(r['d'])
    if i+1>=len(s['dates']): continue
    nd=s['dates'][i+1]
    if piv is None or s['highs'][i+1] < piv:
        det.append((r['name'],'익일 피벗 미돌파 → 미진입',0)); continue
    ep=max(piv, s['opens'][i+1])
    sim=simulate(r['code'], nd, ep, 20, -10, last_date='2026-08-21')
    g=sim['gain'] if sim['result']!='ambiguous' else -10
    won=t['avg_buy']*t['buy_qty']*(g-0.34)/100
    tot+=won; det.append((r['name'], sim['result'], round(won)))
for x in det: print("   ",x)
print(f"   합계 {tot:,.0f}원 (실제 ③ 합계 {sum(r['net_won'] for r in g3):,.0f}원)")
