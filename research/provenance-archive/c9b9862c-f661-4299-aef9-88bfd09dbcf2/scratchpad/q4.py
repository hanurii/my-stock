# -*- coding: utf-8 -*-
from engine import *
from statistics import mean, median
base = {(r["code"],r["entry_date"]): r for r in run_rule()}
def ft(p,l):
    for k,b in enumerate(p["path"]):
        if b["h"]>=l: return k
    return None
def fs(p,l=-10.0):
    for k,b in enumerate(p["path"]):
        if b["l"]<=l: return k
    return None
print("── +X% 에 도달한 시점에서 '계속 들었을 때' 의 조건부 결과 (손절 -10 유지) ──")
print(f"{'X':>4} {'도달건':>6} {'전체%':>6} {'→+20':>7} {'→-10':>7} {'미결':>5} {'남은수익%':>9} {'남은일수':>7} {'즉시익절%':>9} {'차이%p':>7} {'p':>7}")
for X in (3,5,8,10,12,15):
    hit=[]
    for p in PATHS:
        t=ft(p,float(X)); s=fs(p)
        if t is None or (s is not None and s<t): continue
        hit.append((p,t))
    nw=nl=no=0; rem=[]; rd=[]; final=[]
    for p,t in hit:
        r=base[(p["code"],p["entry_date"])]
        fin=r["ret"]; final.append(fin)
        rem.append(((1+fin/100)/(1+X/100)-1)*100)
        rd.append(max(r["days"]-t,0))
        if r["why"]=="target": nw+=1
        elif r["why"].startswith("stop"): nl+=1
        else: no+=1
    # 즉시 익절 = X 확정 후 새 거래 1회(전체 평균) — 같은 일수 안에서 비교는 아래 별도
    print(f"{X:>4} {len(hit):>6} {len(hit)/614*100:>5.0f}% {nw:>6} {nl:>7} {no:>5} {mean(rem):>9.2f} {mean(rd):>7.1f} {X:>9.1f} {mean(rem):>7.2f}")
print("\n※ '남은수익%' = 그 자리에서 팔지 않고 규칙대로 끝까지 들었을 때 그 시점 대비 추가 손익(복리)")
print("   즉시 팔면 이 값은 0%. 즉, 남은수익이 양수면 '들고 있는 게 이득'.")

print("\n── 갈아타기 비교: 남은 보유 vs 새 거래 (같은 날짜 안에서) ──")
# 각 X 도달 시점 날짜 d 에서, 그날 이후 새로 진입한 거래들의 평균 수익과 비교
from collections import defaultdict
byentry=defaultdict(list)
for p in PATHS: byentry[p["entry_date"]].append(base[(p["code"],p["entry_date"])]["ret"])
dates=sorted(byentry)
import bisect
def fresh_avg(d, win=5):
    """날짜 d 이후 win 거래일 안에 새로 진입한 거래들의 평균 수익(같은 국면 대조군)"""
    i=bisect.bisect_left(dates,d)
    vals=[v for dd in dates[i:i+win] for v in byentry[dd]]
    return (mean(vals), len(vals)) if vals else (None,0)
for X in (5,8,10,12,15):
    hit=[]
    for p in PATHS:
        t=ft(p,float(X)); s=fs(p)
        if t is None or (s is not None and s<t): continue
        hit.append((p,t))
    diffs=[]; blocks=defaultdict(list)
    for p,t in hit:
        r=base[(p["code"],p["entry_date"])]
        rem=((1+r["ret"]/100)/(1+X/100)-1)*100
        d=p["path"][t]["d"]
        fa,n=fresh_avg(d)
        if fa is None: continue
        diffs.append(rem-fa); blocks[p["code"]].append(rem-fa)
    obs=mean(diffs)
    import random
    rnd=random.Random(11); keys=list(blocks); N=len(diffs); cnt=0
    for _ in range(4000):
        s2=sum((1 if rnd.random()<.5 else -1)*sum(blocks[k]) for k in keys)
        if abs(s2/N)>=abs(obs)-1e-12: cnt+=1
    print(f"  +{X:>2}% 시점: 계속보유 남은수익 평균 {mean([((1+base[(p['code'],p['entry_date'])]['ret']/100)/(1+X/100)-1)*100 for p,t in hit]):>6.2f}%  vs  같은 시점 새 진입 평균 {mean([fresh_avg(p['path'][t]['d'])[0] for p,t in hit if fresh_avg(p['path'][t]['d'])[0] is not None]):>5.2f}%   차이 {obs:>6.2f}%p  p={(cnt+1)/4001:.4f}  (n={len(diffs)}, 종목 {len(keys)})")
