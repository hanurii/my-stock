# -*- coding: utf-8 -*-
"""전 종목 메모리 상주 + 하루치 파이프라인(RS 포함) 비용 측정."""
import json, sys, time, gc, os
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))
SER = ROOT / ".cache" / "ohlcv" / "series"

def rss_mb():
    try:
        import ctypes, ctypes.wintypes
        class PMC(ctypes.Structure):
            _fields_=[("cb",ctypes.c_ulong),("PageFaultCount",ctypes.c_ulong),
                      ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
                      ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),("QuotaNonPagedPoolUsage",ctypes.c_size_t),
                      ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
        c=PMC(); c.cb=ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.WorkingSetSize/1024/1024
    except Exception as e:
        return -1

print("base RSS", round(rss_mb(),1), "MB")
t0=time.time()
files=sorted(SER.glob("*.json"))
store={}
for f in files:
    try:
        s=json.loads(f.read_text(encoding="utf-8"))
    except Exception: continue
    store[f.stem]=s
t_load=time.time()-t0
print(f"[전종목 로드] {len(store)}개 {t_load:.1f}s, RSS {rss_mb():.0f} MB")

# ---- 하루치 RS 산출 비용 ----
sys.path.insert(0, str(ROOT/"scripts"))
from bisect import bisect_right
def rs_one_day(asof):
    # 각 종목: asof 까지 자른 closes 로 252일 수익률 → 백분위
    rets=[]
    idxmap={}
    for code,s in store.items():
        d=s["dates"]; c=s["closes"]
        k=bisect_right(d,asof)
        if k<253: continue
        r=c[k-1]/c[k-1-252]-1.0
        rets.append((code,r))
    vals=sorted(x[1] for x in rets)
    n=len(vals)
    import bisect as B
    out={}
    for code,r in rets:
        out[code]=max(1,min(99,round(B.bisect_left(vals,r)/n*100)))
    return out

t0=time.time()
for asof in ["2026-08-21","2026-08-20","2026-08-19","2026-08-18","2026-08-17"]:
    rs=rs_one_day(asof)
t=(time.time()-t0)/5
print(f"[RS 하루치] 전종목 대상 {t*1000:.0f} ms/일 (표본 {len(rs)}종목)")

# ---- 하루치 트렌드템플레이트 전종목 ----
from canslim_lib.trend_template import evaluate_trend_template, compute_gate_margin
asof="2026-08-21"
t0=time.time(); npass=0; nev=0
for code,s in store.items():
    d=s["dates"]; c=s["closes"]
    k=bisect_right(d,asof)
    if k<200: continue
    sub=c[:k]
    r=evaluate_trend_template(sub, rs.get(code), 80)
    compute_gate_margin(r, sub[-1], rs.get(code), 80)
    nev+=1
    if r["pass"]: npass+=1
t=time.time()-t0
print(f"[TT+gate 하루치] {nev}종목 {t:.2f}s → 통과 {npass}종목")
print(f"→ 299일 환산: RS {0.0:.0f} + TT = {(t)*299/60:.1f}분 (TT만, 1코어)")
print("RSS", round(rss_mb(),0), "MB")
