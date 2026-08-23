# -*- coding: utf-8 -*-
from engine import *
from statistics import mean
from collections import defaultdict
import bisect, random
base={(r["code"],r["entry_date"]):r for r in run_rule()}
def ft(p,l):
    for k,b in enumerate(p["path"]):
        if b["h"]>=l: return k
    return None
def fs(p,l=-10.0):
    for k,b in enumerate(p["path"]):
        if b["l"]<=l: return k
    return None
byentry=defaultdict(list)
for p in PATHS: byentry[p["entry_date"]].append(base[(p["code"],p["entry_date"])]["ret"])
dates=sorted(byentry)
def fresh(d,win):
    i=bisect.bisect_left(dates,d); v=[x for dd in dates[i:i+win] for x in byentry[dd]]
    return mean(v) if v else None
print("── Q4 대조군 창 민감도: +8% 시점 계속보유 vs 새 거래 ──")
hit=[]
for p in PATHS:
    t=ft(p,8.0); s=fs(p)
    if t is None or (s is not None and s<t): continue
    hit.append((p,t))
rem_all=[((1+base[(p['code'],p['entry_date'])]['ret']/100)/1.08-1)*100 for p,t in hit]
print(f"  계속보유 남은수익 평균 {mean(rem_all):.2f}%  (n={len(hit)})")
for win in (1,3,5,10,20):
    ds=[]; blocks=defaultdict(list)
    for p,t in hit:
        fa=fresh(p["path"][t]["d"],win)
        if fa is None: continue
        rm=((1+base[(p['code'],p['entry_date'])]['ret']/100)/1.08-1)*100
        ds.append(rm-fa); blocks[p["code"]].append(rm-fa)
    obs=mean(ds); rnd=random.Random(9); keys=list(blocks); N=len(ds); cnt=0
    for _ in range(4000):
        s=sum((1 if rnd.random()<.5 else -1)*sum(blocks[k]) for k in keys)
        if abs(s/N)>=abs(obs)-1e-12: cnt+=1
    print(f"  창 {win:>2}거래일: 새거래 평균 {mean(rem_all)-obs:>5.2f}%  차이 {obs:>5.2f}%p p={(cnt+1)/4001:.4f} n={N}")
print(f"  (참고) 전체 614건 무조건부 평균 {mean([v['ret'] for v in base.values()]):.2f}%  → 차이 {mean(rem_all)-mean([v['ret'] for v in base.values()]):.2f}%p")

print("\n── (마) 참고: 목표를 더 멀리 두면? (탐색적, 인샘플) ──")
print(f"{'목표':>5} {'손절':>5} {'평균%':>7} {'승률':>6} {'평균일':>6} {'일당%':>7} {'미결MTM':>6} {'전반':>7} {'후반':>7}")
for T in (15.0,20.0,25.0,30.0,40.0):
    for S in (-10.0,):
        rows=run_rule(target=T, stop=S)
        s=stats(rows); nopen=sum(1 for x in rows if x["why"]=="open_mtm")
        print(f"{T:>5.0f} {S:>5.0f} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {nopen:>6} {stats(half(rows,True))['avg']:>7.2f} {stats(half(rows,False))['avg']:>7.2f}")
print("\n── (바) 추적손절(고점 종가 대비 X%p 이탈 시 청산, 목표 상한 없음) ──")
def trail(p, X, stop=-10.0, minhold=0):
    pa=p["path"]; pk=-1e9
    for k,b in enumerate(pa):
        o,l,c,h=b["o"],b["l"],b["c"],b["h"]
        if l<=stop: return (o if (k>0 and o is not None and o<=stop) else stop,k,"stop")
        if k>=minhold and pk>-1e8 and c<=pk-X: return (c,k,"trail")
        pk=max(pk,c)
    return (pa[-1]["c"],len(pa)-1,"open")
print(f"{'X%p':>5} {'평균%':>7} {'승률':>6} {'평균일':>6} {'일당%':>7} {'전반':>7} {'후반':>7} {'미결':>5}")
for X in (5.0,8.0,10.0,12.0,15.0):
    rows=[]
    for p in PATHS:
        r,k,w=trail(p,X); rows.append({"code":p["code"],"entry_date":p["entry_date"],"ret":r,"days":k,"why":w,"res":p["result"]})
    s=stats(rows); print(f"{X:>5.0f} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {stats(half(rows,True))['avg']:>7.2f} {stats(half(rows,False))['avg']:>7.2f} {sum(1 for x in rows if x['why']=='open'):>5}")
