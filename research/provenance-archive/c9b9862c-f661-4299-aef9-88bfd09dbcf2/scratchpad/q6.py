# -*- coding: utf-8 -*-
from engine import *
from statistics import mean
base=run_rule()
bs=stats(base)
def sim_cut(p, N, C, target=20.0, stop=-10.0):
    pa=p["path"]
    for k,b in enumerate(pa):
        o,h,l,c=b["o"],b["h"],b["l"],b["c"]
        if h>=target and l<=stop:
            return (o if (k>0 and o is not None and o<=stop) else stop, k, "stop_amb")
        if l<=stop: return (o if (k>0 and o is not None and o<=stop) else stop, k, "stop")
        if h>=target: return (o if (k>0 and o is not None and o>=target) else target, k, "target")
        if k==N and c<=C: return (c,k,"timecut")
    return (pa[-1]["c"], len(pa)-1, "open")
print("── (라) 손실 쪽 조기청산: N일차 종가가 C% 이하면 정리 ──")
print(f"{'N':>3} {'C':>5} {'평균%':>7} {'승률':>6} {'평균일':>6} {'일당%':>7} {'vs현행':>7} {'p':>7} {'발동':>5} {'전반차':>7} {'후반차':>7}")
res=[]
for N in (2,3,5,7,10):
    for C in (-2.0,-3.0,-5.0,-7.0,0.0):
        rows=[]
        for p in PATHS:
            r,k,w=sim_cut(p,N,C)
            rows.append({"code":p["code"],"entry_date":p["entry_date"],"ret":r,"days":k,"why":w,"res":p["result"]})
        s=stats(rows); d,pv=paired_perm(rows,base)
        nf=sum(1 for x in rows if x["why"]=="timecut")
        a1=[x for x in rows if x["entry_date"]<SPLIT]; b1=[x for x in base if x["entry_date"]<SPLIT]
        a2=[x for x in rows if x["entry_date"]>=SPLIT]; b2=[x for x in base if x["entry_date"]>=SPLIT]
        d1,_=paired_perm(a1,b1,iters=1500); d2,_=paired_perm(a2,b2,iters=1500)
        print(f"{N:>3} {C:>5.0f} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {d:>7.2f} {pv:>7.4f} {nf:>5} {d1:>7.2f} {d2:>7.2f}")
        res.append((N,C,d,pv))
print(f"기준 {bs['avg']:>13.2f} {bs['win_rate']:>6.1f} {bs['avg_days']:>6.1f} {bs['ret_per_day']:>7.4f}")
print(f"\n다중검정: 25개 조합 훑음 → Bonferroni 문턱 p<{0.05/25:.4f}. 통과: {[ (n,c,round(d,2),pv) for n,c,d,pv in res if pv<0.002]}")
