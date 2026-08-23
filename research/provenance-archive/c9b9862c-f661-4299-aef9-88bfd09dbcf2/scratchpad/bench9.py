# -*- coding: utf-8 -*-
"""passmatrix.npz 로 검출기를 돌릴 수 있는지 등가성 검증 + 속도 측정."""
import json, sys, time
import numpy as np
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
PM = Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad/passmatrix.npz")
sys.path.insert(0, str(ROOT/"scripts"))
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play

z=np.load(PM, allow_pickle=True)
dates=list(z['dates']); codes=list(z['codes'])
idx=z['idx']; op=z['open_r']; hi=z['hi_r']; lo=z['lo_r']; vol=z['vol']; pres=z['present']; ap=z['all_pass']; el=z['eligible']
ci={c:j for j,c in enumerate(codes)}
ti={d:i for i,d in enumerate(dates)}
ASOF='2026-08-13'; T=ti[ASOF]

def series_from_pm(code, upto):
    j=ci[code]
    m=pres[:upto+1, j]
    ii=np.where(m)[0]
    c=idx[ii,j]
    return {"dates":[dates[k] for k in ii],
            "closes":list(map(float,c)),
            "opens":list(map(float,c*op[ii,j])),
            "highs":list(map(float,c*hi[ii,j])),
            "lows":list(map(float,c*lo[ii,j])),
            "volumes":[float(v) for v in vol[ii,j]],
            "timestamps":[0]*len(ii)}

SER=ROOT/".cache"/"ohlcv"/"series"
def series_from_cache(code, asof):
    s=json.loads((SER/f"{code}.json").read_text(encoding="utf-8"))
    from bisect import bisect_right
    k=bisect_right(s["dates"],asof)
    return {kk:(s.get(kk) or [])[:k] for kk in ("dates","closes","opens","highs","lows","volumes","timestamps") if s.get(kk) is not None}

sel=[codes[j] for j in np.where(ap[T]&el[T])[0]][:60]
print("검증 대상", len(sel), "종목 @", ASOF)
same={"VCP":0,"3C":0,"PP":0}; tot=0; diffs=[]
for c in sel:
    if not (SER/f"{c}.json").exists(): continue
    a=series_from_pm(c,T); b=series_from_cache(c,ASOF)
    tot+=1
    for nm,fn,dk in (("VCP",evaluate_vcp,"vcp_detected"),("3C",evaluate_cheat,"pattern_detected"),("PP",evaluate_power_play,"pattern_detected")):
        ra,rb=fn(a),fn(b)
        ok = (ra["status"]==rb["status"]) and (bool(ra.get(dk))==bool(rb.get(dk)))
        if ok: same[nm]+=1
        else: diffs.append((c,nm,ra["status"],rb["status"],ra.get(dk),rb.get(dk),len(a['closes']),len(b['closes'])))
print("일치율:", {k: f"{v}/{tot}" for k,v in same.items()})
for d in diffs[:8]: print("  차이:", d)

# 속도: passmatrix 에서 series 만들기 + 검출 3종
t0=time.time(); n=0
for c in sel:
    a=series_from_pm(c,T)
    evaluate_vcp(a); evaluate_cheat(a); evaluate_power_play(a); n+=1
dt=time.time()-t0
print(f"[pm 경로] {n}종목 1일 {dt*1000:.0f}ms → {dt/n*1000:.2f} ms/종목일 (봉수 {len(a['closes'])})")
