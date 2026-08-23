# -*- coding: utf-8 -*-
from engine import *
from statistics import mean, median
from collections import defaultdict
import bisect, random
base={(r["code"],r["entry_date"]):r for r in run_rule()}
def open_at(p,N):
    """N일차 종가 시점에 아직 살아있나? (그때까지 +20/-10 미도달) → (살아있음, 그날 손익%, 날짜)"""
    pa=p["path"]
    if N>=len(pa): return None
    for k in range(N+1):
        b=pa[k]
        if b["h"]>=20.0 or b["l"]<=-10.0:
            if k<N or (k==N): return None
    return (pa[N]["c"], pa[N]["d"])

byentry=defaultdict(list)
for p in PATHS: byentry[p["entry_date"]].append(base[(p["code"],p["entry_date"])]["ret"])
dates=sorted(byentry)
def fresh_avg(d,win=5):
    i=bisect.bisect_left(dates,d)
    v=[x for dd in dates[i:i+win] for x in byentry[dd]]
    return mean(v) if v else None

print("── 'N일차까지 살아있는' 포지션의 이후 운명 (손절 -10·목표 +20 유지) ──")
print(f"{'N일차':>5} {'생존':>5} {'그날손익중앙':>10} {'→+20':>6} {'→-10':>6} {'미결':>4} {'승률':>6} {'남은수익%':>9} {'남은일수':>7} {'같은시점 새거래%':>13} {'차이%p':>7} {'p':>7}")
for N in (1,2,3,5,7,10,15,20):
    rows=[]
    for p in PATHS:
        r=open_at(p,N)
        if r is None: continue
        cur,d=r; rr=base[(p["code"],p["entry_date"])]
        rem=((1+rr["ret"]/100)/(1+cur/100)-1)*100
        rows.append((p,cur,d,rr,rem))
    if not rows: continue
    nw=sum(1 for x in rows if x[3]["why"]=="target"); nl=sum(1 for x in rows if x[3]["why"].startswith("stop"))
    no=len(rows)-nw-nl
    diffs=[]; blocks=defaultdict(list); fr=[]
    for p,cur,d,rr,rem in rows:
        fa=fresh_avg(d)
        if fa is None: continue
        fr.append(fa); diffs.append(rem-fa); blocks[p["code"]].append(rem-fa)
    obs=mean(diffs); rnd=random.Random(3); keys=list(blocks); Nn=len(diffs); cnt=0
    for _ in range(4000):
        s=sum((1 if rnd.random()<.5 else -1)*sum(blocks[k]) for k in keys)
        if abs(s/Nn)>=abs(obs)-1e-12: cnt+=1
    print(f"{N:>5} {len(rows):>5} {median([x[1] for x in rows]):>10.1f} {nw:>6} {nl:>6} {no:>4} {nw/(nw+nl)*100 if nw+nl else 0:>5.1f}% "
          f"{mean([x[4] for x in rows]):>9.2f} {mean([max(x[3]['days']-N,0) for x in rows]):>7.1f} {mean(fr):>13.2f} {obs:>7.2f} {(cnt+1)/4001:>7.4f}")

print("\n── 5일차 시점 손익 구간별: 계속 보유 vs 그날 팔고 새 거래 (같은 날짜 대조) ──")
for N in (3,5,7,10):
    print(f"  [{N}일차]")
    rows=[]
    for p in PATHS:
        r=open_at(p,N)
        if r is None: continue
        cur,d=r; rr=base[(p["code"],p["entry_date"])]
        rows.append((p,cur,d,rr,((1+rr["ret"]/100)/(1+cur/100)-1)*100))
    buckets=[("-10~-5",-99,-5),("-5~0",-5,0),("0~+5",0,5),("+5~+10",5,10),("+10~+20",10,99)]
    for lbl,lo,hi in buckets:
        sub=[x for x in rows if lo<=x[1]<hi]
        if len(sub)<15: 
            print(f"    {lbl:>8}: n={len(sub)} 표본부족"); continue
        rem=[x[4] for x in sub]
        diffs=[]; blocks=defaultdict(list)
        for p,cur,d,rr,rm in sub:
            fa=fresh_avg(d)
            if fa is None: continue
            diffs.append(rm-fa); blocks[p["code"]].append(rm-fa)
        obs=mean(diffs); rnd=random.Random(5); keys=list(blocks); Nn=len(diffs); cnt=0
        for _ in range(4000):
            s=sum((1 if rnd.random()<.5 else -1)*sum(blocks[k]) for k in keys)
            if abs(s/Nn)>=abs(obs)-1e-12: cnt+=1
        nw=sum(1 for x in sub if x[3]["why"]=="target")
        print(f"    {lbl:>8}: n={len(sub):>3} 이후 +20도달 {nw/len(sub)*100:>4.0f}%  남은수익 {mean(rem):>6.2f}%  새거래 {mean([fresh_avg(x[2]) for x in sub if fresh_avg(x[2]) is not None]):>5.2f}%  차이 {obs:>6.2f}%p p={(cnt+1)/4001:.3f}")
