# -*- coding: utf-8 -*-
from engine import *
from statistics import mean
base={(r["code"],r["entry_date"]):r for r in run_rule()}
def alive(p,N):
    if N>=len(p["path"]): return False
    for k in range(N+1):
        b=p["path"][k]
        if b["h"]>=20.0 or b["l"]<=-10.0: return False
    return True
for N in (3,5,7):
  for C in (-5.0,-3.0):
    sub=[p for p in PATHS if alive(p,N) and p["path"][N]["c"]>C]
    nw=sum(1 for p in sub if base[(p["code"],p["entry_date"])]["why"]=="target")
    rem=[((1+base[(p['code'],p['entry_date'])]['ret']/100)/(1+p["path"][N]["c"]/100)-1)*100 for p in sub]
    print(f"{N}일차 생존 & 종가>{C:.0f}%: n={len(sub):>3}  이후 +20% 도달 {nw/len(sub)*100:>4.1f}%  그 시점 대비 남은수익 평균 {mean(rem):>5.2f}%  최종 평균 {mean([base[(p['code'],p['entry_date'])]['ret'] for p in sub]):>5.2f}%")
print()
print("최종 권장 규칙 = 현행 +20/-10 + '5일차 종가 -5% 이하면 정리'")
def rule(p):
    pa=p["path"]
    for k,b in enumerate(pa):
        o,h,l,c=b["o"],b["h"],b["l"],b["c"]
        if h>=20.0 and l<=-10.0: return (o if(k>0 and o is not None and o<=-10)else -10.0,k,"stop")
        if l<=-10.0: return (o if(k>0 and o is not None and o<=-10)else -10.0,k,"stop")
        if h>=20.0: return (o if(k>0 and o is not None and o>=20)else 20.0,k,"target")
        if k==5 and c<=-5.0: return (c,k,"timecut")
    return (pa[-1]["c"],len(pa)-1,"open")
rows=[]
for p in PATHS:
    r,k,w=rule(p); rows.append({"code":p["code"],"entry_date":p["entry_date"],"ret":r,"days":k,"why":w,"res":p["result"]})
print(" ", stats(rows))
print("  전반", stats(half(rows,True))["avg"], "후반", stats(half(rows,False))["avg"])
b=run_rule(); print("  vs 현행", paired_perm(rows,b,iters=5000))
print("  vs 사용자행동근사", paired_perm(rows, run_rule(tp=7.83,stop=-6.64), iters=5000))
