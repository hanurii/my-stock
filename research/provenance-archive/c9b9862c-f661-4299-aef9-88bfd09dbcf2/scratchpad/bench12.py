# -*- coding: utf-8 -*-
"""기존 러너(pivot_backtest_nextday_multi) 방식 그대로의 1스캔일 비용."""
import json, sys, time
from pathlib import Path
ROOT=Path(r"C:/Users/hanul/playground/my-stock"); sys.path.insert(0,str(ROOT/"scripts"))
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib.trend_template import evaluate_trend_template
from screen_trend_template import _compute_rs_for_all
SER=ROOT/".cache"/"ohlcv"/"series"
full={}
for f in sorted(SER.glob("*.json")):
    try: full[f.stem]=json.loads(f.read_text(encoding="utf-8"))
    except Exception: pass
print("시계열",len(full))
D="2026-06-30"
t0=time.time()
stD={}
for c,s in full.items():
    t=truncate_series(s,D)
    if len(t["closes"])>=200: stD[c]=t
t1=time.time(); print(f"truncate_series 전종목: {t1-t0:.2f}s  ({len(stD)}종목)")
rs=_compute_rs_for_all([{"code":c,"closes":t["closes"],"ok":True} for c,t in stD.items()])
t2=time.time(); print(f"_compute_rs_for_all: {t2-t1:.2f}s")
n=0
for c,t in stD.items():
    rsv=(rs.get(c) or {}).get("rs")
    if evaluate_trend_template(t["closes"],rs=rsv,rs_min=80)["pass"]: n+=1
t3=time.time(); print(f"트렌드 8조건 전종목: {t3-t2:.2f}s  통과 {n}")
print(f"→ 1 스캔일 합계 {t3-t0:.2f}s · 299스캔일(step=1) 추정 {(t3-t0)*299/60:.1f}분")
