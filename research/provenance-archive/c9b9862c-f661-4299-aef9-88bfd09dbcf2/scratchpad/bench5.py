# -*- coding: utf-8 -*-
"""프로덕션 충실 1일 파이프라인 × 5일 — 실제 비용/일 측정 (읽기전용)."""
import json, sys, time
from bisect import bisect_right, bisect_left
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))
SER = ROOT / ".cache" / "ohlcv" / "series"

from canslim_lib.trend_template import evaluate_trend_template, compute_gate_margin
from canslim_lib.minervini_filter import classify_non_minervini
from canslim_lib.liveness import is_halted, load_excluded_codes
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play

t0=time.time()
store={}
for f in sorted(SER.glob("*.json")):
    try: store[f.stem]=json.loads(f.read_text(encoding="utf-8"))
    except Exception: pass
print(f"로드 {len(store)}종목 {time.time()-t0:.1f}s")
excl=load_excluded_codes()
print("수동 제외", len(excl))

KEYS=("dates","closes","opens","highs","lows","volumes","timestamps")

def one_day(asof, verbose=False):
    tA=time.time()
    # 1) 절단 인덱스
    ks={c: bisect_right(s["dates"], asof) for c,s in store.items()}
    # 2) RS (전 종목, 252일)
    rets=[]
    for c,s in store.items():
        k=ks[c]
        if k<253: continue
        base=s["closes"][k-253]
        if not base: continue
        rets.append((c, s["closes"][k-1]/base-1.0))
    vals=sorted(x[1] for x in rets); n=len(vals)
    rs={c: max(1,min(99,round(bisect_left(vals,r)/n*100))) for c,r in rets}
    tRS=time.time()-tA
    # 3) 유니버스 정화(정지/제외/미너비니)
    tB=time.time()
    keep=[]
    for c,s in store.items():
        k=ks[c]
        if k<200: continue
        if c in excl: continue
        if all((v or 0)==0 for v in s["volumes"][max(0,k-5):k]): continue
        if classify_non_minervini({"code":c}, s, asof=asof): continue
        keep.append(c)
    tFilt=time.time()-tB
    # 4) 8조건 + 관문여유
    tC=time.time()
    passers=[]
    for c in keep:
        s=store[c]; k=ks[c]
        sub=s["closes"][:k]
        r=evaluate_trend_template(sub, rs.get(c), 80)
        compute_gate_margin(r, sub[-1], rs.get(c), 80)
        if r["pass"]: passers.append(c)
    tTT=time.time()-tC
    # 5) 검출기 3종 (통과 종목만)
    tD=time.time()
    det=0
    for c in passers:
        s=store[c]; k=ks[c]
        sub={kk:(s.get(kk) or [])[:k] for kk in KEYS if s.get(kk) is not None}
        evaluate_vcp(sub); evaluate_cheat(sub); evaluate_power_play(sub)
        det+=1
    tDet=time.time()-tD
    tot=time.time()-tA
    if verbose:
        print(f"{asof}: 유니버스 {len(keep)} · 8조건통과 {len(passers)} | "
              f"RS {tRS*1000:.0f}ms 필터 {tFilt*1000:.0f}ms TT {tTT*1000:.0f}ms 검출 {tDet*1000:.0f}ms = {tot*1000:.0f}ms")
    return tot, len(keep), len(passers)

days=["2026-08-21","2026-06-30","2026-04-15","2026-02-10","2025-12-05"]
tots=[]
for d in days:
    t,nk,np_=one_day(d, True); tots.append(t)
avg=sum(tots)/len(tots)
print(f"\n평균 {avg*1000:.0f} ms/일 → 299일 = {avg*299:.0f}초 ({avg*299/60:.1f}분, 1코어)")
