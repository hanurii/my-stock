# -*- coding: utf-8 -*-
from engine import *
base = run_rule()
bs = stats(base)
print("기준 현행 +20/-10 :", bs)
print()
print("── (가) 조기 익절: +X% 최초 도달 즉시 매도 (손절 -10 유지) ──")
print(f"{'X':>4} {'평균%':>7} {'승률':>6} {'평균익':>7} {'평균손':>7} {'PF':>5} {'평균일':>6} {'일당%':>7} {'vs기준':>7} {'p':>7} {'전반':>7} {'후반':>7}")
rowsX={}
for X in (3,5,7,8,10,12,15):
    r = run_rule(tp=float(X)); rowsX[X]=r
    s = stats(r)
    d,p = paired_perm(r, base)
    print(f"{X:>4} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_win']:>7.2f} {s['avg_loss']:>7.2f} {str(s['pf']):>5} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {d:>7.2f} {p:>7.4f} {stats(half(r,True))['avg']:>7.2f} {stats(half(r,False))['avg']:>7.2f}")
print(f"기준 {bs['avg']:>7.2f} {bs['win_rate']:>6.1f} {bs['avg_win']:>7.2f} {bs['avg_loss']:>7.2f} {str(bs['pf']):>5} {bs['avg_days']:>6.1f} {bs['ret_per_day']:>7.4f}      -       - {stats(half(base,True))['avg']:>7.2f} {stats(half(base,False))['avg']:>7.2f}")
print()
print("── (나) N일차 점검형: N일차 종가에 +X% 이상이면 매도 ──")
print(f"{'N':>3} {'X':>3} {'평균%':>7} {'승률':>6} {'평균일':>6} {'일당%':>7} {'vs기준':>7} {'p':>7} {'조기청산건':>7}")
for N in (3,5,7,10,15):
    for X in (3,5,8,10,15):
        r = run_rule(checkpoint=(N,float(X)))
        s = stats(r); d,p = paired_perm(r, base)
        ncp = sum(1 for x in r if x["why"]=="checkpoint")
        print(f"{N:>3} {X:>3} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {d:>7.2f} {p:>7.4f} {ncp:>7}")
import json
json.dump({str(k):[{'code':x['code'],'entry_date':x['entry_date'],'ret':x['ret'],'days':x['days'],'why':x['why']} for x in v] for k,v in rowsX.items()}, open("tp_rows.json","w"))
