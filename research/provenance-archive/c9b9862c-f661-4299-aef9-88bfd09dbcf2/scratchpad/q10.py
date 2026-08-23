# -*- coding: utf-8 -*-
from engine import *
from statistics import mean, median
base={(r["code"],r["entry_date"]):r for r in run_rule()}
def ft(p,l):
    for k,b in enumerate(p["path"]):
        if b["h"]>=l: return k
    return None
def fs(p,l=-10.0):
    for k,b in enumerate(p["path"]):
        if b["l"]<=l: return k
    return None
winners=[]
for p in PATHS:
    t=ft(p,20.0); s=fs(p)
    if t is None or (s is not None and s<=t): continue
    winners.append((p,t))
print("── 승자가 N일차에 보이는 모습(그날 종가, 진입가 대비) ──")
print(f"{'N':>3} {'아직 미도달 승자':>10} {'중앙':>7} {'P25':>7} {'P10':>7} {'최악':>7}  |  {'같은날 살아있는 패자 중앙':>10}")
for N in (1,2,3,5,7,10,15):
    w=[p["path"][N]["c"] for p,t in winners if t>N and N<len(p["path"])]
    l=[]
    for p in PATHS:
        t=ft(p,20.0); s=fs(p)
        if N>=len(p["path"]): continue
        if s is None or s<=N: continue
        if t is not None and t<=N: continue
        r=base[(p["code"],p["entry_date"])]
        if r["why"].startswith("stop"): l.append(p["path"][N]["c"])
    if not w: continue
    print(f"{N:>3} {len(w):>10} {median(w):>7.1f} {q(w,.25):>7.1f} {q(w,.10):>7.1f} {min(w):>7.1f}  |  {median(l) if l else 0:>10.1f} (n={len(l)})")
print("\n※ 두 분포가 겹친다 = N일차 손익만으로 승패를 가릴 수 없다")

print("\n── '5일차 종가 -5% 이하면 정리' 규칙이 실제로 자른 것 ──")
cut=[]
for p in PATHS:
    if 5>=len(p["path"]): continue
    t=ft(p,20.0); s=fs(p)
    if (s is not None and s<=5) or (t is not None and t<=5): continue
    if p["path"][5]["c"]<=-5.0: cut.append(p)
nw=sum(1 for p in cut if base[(p["code"],p["entry_date"])]["why"]=="target")
print(f"  발동 {len(cut)}건 중 나중에 +20% 갔을 종목 {nw}건 ({nw/len(cut)*100:.0f}%), 어차피 손절났을 종목 {len(cut)-nw}건")
print(f"  자른 자리 평균 {mean([p['path'][5]['c'] for p in cut]):.2f}% vs 그냥 뒀을 때 평균 {mean([base[(p['code'],p['entry_date'])]['ret'] for p in cut]):.2f}%")

print("\n── 승자 도달시점 요약(재확인) ──")
dts=[t for _,t in winners]
for c in (3,5,7,10,15,20):
    n=sum(1 for t in dts if t>c)
    print(f"  {c}거래일 넘겨서야 +20% 도달한 승자: {n}/{len(dts)} ({n/len(dts)*100:.0f}%)")
