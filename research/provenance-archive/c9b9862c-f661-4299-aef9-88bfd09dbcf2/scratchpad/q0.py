# -*- coding: utf-8 -*-
from engine import *
base = run_rule()
print("=== 기준(현행 +20/-10) ===")
print(stats(base))
from collections import Counter
print(Counter(r["why"] for r in base))
print("전반", stats(half(base,True)))
print("후반", stats(half(base,False)))
# 낙관 버전(동시일 목표 우선) 민감도
def sim_opt(p):
    pa=p["path"]
    for k,b in enumerate(pa):
        if b["h"]>=20.0: 
            o=b["o"]; f=o if (k>0 and o is not None and o>=20.0) else 20.0
            return f
        if b["l"]<=-10.0:
            o=b["o"]; f=o if (k>0 and o is not None and o<=-10.0) else -10.0
            return f
    return pa[-1]["c"]
opt=[sim_opt(p) for p in PATHS]
print("낙관(동시일 목표우선) 평균", round(mean(opt),3))
print("종목수", len(set(p["code"] for p in PATHS)))
