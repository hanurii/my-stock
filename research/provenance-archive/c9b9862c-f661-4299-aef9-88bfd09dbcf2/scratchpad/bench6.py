# -*- coding: utf-8 -*-
"""캐시 백필(재피벗) 비용 추정 — .cache 는 읽기만, 쓰기는 scratchpad."""
import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
SCRATCH = Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad")
sys.path.insert(0, str(ROOT/"scripts"))
PD = ROOT/".cache"/"pdata"
KST = timezone(timedelta(hours=9))

days = sorted(f.stem[6:] for f in PD.glob("price_*.json") if f.stem[6:] >= "20231001")
N = 100
sub = days[:N]
print(f"측정: {N}일 피벗 ({sub[0]}~{sub[-1]}), 전체 대상 {len(days)}일")

t0=time.time()
series={}
for bd in sub:
    rows=json.loads((PD/f"price_{bd}.json").read_text(encoding="utf-8"))
    iso=f"{bd[:4]}-{bd[4:6]}-{bd[6:8]}"
    ts=int(datetime.strptime(bd+" 16:00","%Y%m%d %H:%M").replace(tzinfo=KST).timestamp())
    for code,row in rows.items():
        cp=row.get("clpr")
        if cp is None: continue
        s=series.get(code)
        if s is None:
            s=series[code]={"dates":[],"timestamps":[],"closes":[],"opens":[],"highs":[],"lows":[],"volumes":[],"_flt":[]}
        s["dates"].append(iso); s["timestamps"].append(ts)
        s["closes"].append(float(cp)); s["opens"].append(float(row.get("mkp") or cp))
        s["highs"].append(float(row.get("hipr") or cp)); s["lows"].append(float(row.get("lopr") or cp))
        try: s["volumes"].append(int(row.get("trqu") or 0))
        except Exception: s["volumes"].append(0)
        s["_flt"].append(row.get("fltRt"))
dt=time.time()-t0
print(f"[피벗] {N}일 {dt:.1f}s → {dt/N*1000:.0f} ms/일 · 종목수 {len(series)}")
print(f"  → {len(days)}일 전체 추정 피벗: {dt/N*len(days):.0f}초")

from canslim_lib.ohlcv_matrix import _apply_adjustment
t0=time.time(); k=0
out=SCRATCH/"series_test"; out.mkdir(exist_ok=True)
for code,s in list(series.items())[:300]:
    _apply_adjustment(s); s.pop("_flt",None)
    (out/f"{code}.json").write_text(json.dumps(s,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    k+=1
dt2=time.time()-t0
print(f"[복원+저장] {k}종목({N}봉) {dt2:.1f}s → {dt2/k*1000:.1f} ms/종목")
print(f"  → 3,039종목 × 701봉 추정: {dt2/k*3039*(len(days)/N):.0f}초")
import shutil; shutil.rmtree(out, ignore_errors=True)
