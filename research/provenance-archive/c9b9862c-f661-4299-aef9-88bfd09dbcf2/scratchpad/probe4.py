# DRY: pdata 읽기+피벗 비용만 측정. 아무것도 쓰지 않음.
import json, glob, os, time, sys
ROOT=r"C:\Users\hanul\playground\my-stock"
files=sorted(glob.glob(os.path.join(ROOT,".cache","pdata","price_*.json")))
print("pdata files:", len(files), files[0][-18:], files[-1][-18:])
sub=[f for f in files if "2023" <= os.path.basename(f)[6:10] ]
print("2023+ files:", len(sub))
N=100
t=time.time()
series={}
for f in sub[-N:]:
    d=json.load(open(f,encoding="utf-8"))
    bd=os.path.basename(f)[6:14]
    for code,row in d.items():
        cp=row.get("clpr")
        if cp is None: continue
        s=series.setdefault(code, {"dates":[], "closes":[], "opens":[], "highs":[], "lows":[], "volumes":[], "_flt":[]})
        s["dates"].append(bd); s["closes"].append(float(cp))
        s["opens"].append(float(row.get("mkp") or cp)); s["highs"].append(float(row.get("hipr") or cp))
        s["lows"].append(float(row.get("lopr") or cp)); s["volumes"].append(int(row.get("trqu") or 0))
        s["_flt"].append(row.get("fltRt"))
el=time.time()-t
print("pivot %d days: %.2fs  (%.1f ms/day)  codes=%d  RAMest" % (N, el, el/N*1000, len(series)))
print("→ 700 days est: %.0fs ; 1628 days est: %.0fs" % (el/N*700, el/N*1628))
# adjustment cost
sys.path.insert(0, os.path.join(ROOT,"scripts"))
from canslim_lib.ohlcv_matrix import _apply_adjustment
t=time.time()
import copy
k=0
for code,s in series.items():
    _apply_adjustment(s); k+=1
    if k>=500: break
el2=time.time()-t
print("adjust 500 codes: %.2fs → 3039 codes est %.1fs" % (el2, el2/500*3039))
