# -*- coding: utf-8 -*-
from engine import *
from collections import Counter
b2 = run_rule(gap_fill=False)
print("갭무시(정확 ±20/-10 체결)", stats(b2))
# 결착만(미결·모호 제외) — 원본 events 방식
ev=[p for p in PATHS if p["result"] in ("win","loss")]
r=[20.0 if p["result"]=="win" else -10.0 for p in ev]
print("결착 580건 단순 ±20/-10:", round(mean(r),3), len(ev))
allr=[20.0 if p["result"] in("win",) else (-10.0 if p["result"]=="loss" else None) for p in PATHS]
# ambiguous 를 +20 으로 보면
r2=[20.0 if p["result"] in("win","ambiguous") else (-10.0 if p["result"]=="loss" else 0.0) for p in PATHS]
print("모호=승 처리 614건:", round(mean(r2),3))
r3=[20.0 if p["result"]=="win" else (-10.0 if p["result"] in ("loss","ambiguous") else 0.0) for p in PATHS]
print("모호=패 처리 614건:", round(mean(r3),3))
