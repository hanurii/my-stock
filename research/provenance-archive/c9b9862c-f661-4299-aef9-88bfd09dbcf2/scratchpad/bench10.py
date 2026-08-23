# -*- coding: utf-8 -*-
import json, sys, time
import numpy as np
from pathlib import Path
from bisect import bisect_right
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
PM = Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad/passmatrix.npz")
sys.path.insert(0, str(ROOT/"scripts"))
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play
z=np.load(PM, allow_pickle=True)
dates=list(z['dates']); codes=list(z['codes'])
idx=z['idx']; op=z['open_r']; hi=z['hi_r']; lo=z['lo_r']; vol=z['vol']; pres=z['present']; ap=z['all_pass']; el=z['eligible']
ci={c:j for j,c in enumerate(codes)}; ti={d:i for i,d in enumerate(dates)}
ASOF='2026-08-13'; T=ti[ASOF]
SER=ROOT/".cache"/"ohlcv"/"series"

def series_from_pm(code, upto, tail=None):
    j=ci[code]; ii=np.where(pres[:upto+1,j])[0]
    if tail: ii=ii[-tail:]
    c=idx[ii,j]
    return {"dates":[dates[k] for k in ii],"closes":list(map(float,c)),
            "opens":list(map(float,c*op[ii,j])),"highs":list(map(float,c*hi[ii,j])),
            "lows":list(map(float,c*lo[ii,j])),"volumes":[float(v) for v in vol[ii,j]],
            "timestamps":[0]*len(ii)}
def series_from_cache(code, asof):
    s=json.loads((SER/f"{code}.json").read_text(encoding="utf-8"))
    k=bisect_right(s["dates"],asof)
    return {kk:(s.get(kk) or [])[:k] for kk in ("dates","closes","opens","highs","lows","volumes","timestamps") if s.get(kk) is not None}

sel=[codes[j] for j in np.where(ap[T]&el[T])[0]]
sel=[c for c in sel if (SER/f"{c}.json").exists()]
print("대상", len(sel))
for tail in (None, 400):
    same={"VCP":0,"3C":0,"PP":0}; tot=0
    t0=time.time()
    for c in sel:
        a=series_from_pm(c,T,tail); b=series_from_cache(c,ASOF); tot+=1
        for nm,fn,dk in (("VCP",evaluate_vcp,"vcp_detected"),("3C",evaluate_cheat,"pattern_detected"),("PP",evaluate_power_play,"pattern_detected")):
            ra,rb=fn(a),fn(b)
            if ra["status"]==rb["status"] and bool(ra.get(dk))==bool(rb.get(dk)): same[nm]+=1
    dt=time.time()-t0
    print(f"tail={tail}: 일치 {[(k,f'{v}/{tot}') for k,v in same.items()]}  총 {dt*1000:.0f}ms  {dt/tot*1000:.2f}ms/종목(검출3종+캐시비교 포함)")
# 순수 pm 경로 속도
for tail in (None,400):
    t0=time.time()
    for c in sel:
        a=series_from_pm(c,T,tail); evaluate_vcp(a); evaluate_cheat(a); evaluate_power_play(a)
    dt=time.time()-t0
    print(f"[pm only] tail={tail}: {dt/len(sel)*1000:.2f} ms/종목일")
