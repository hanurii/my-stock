# -*- coding: utf-8 -*-
"""등가중 시장지수 캐시(스크래치) — superperf RS선 계산용."""
import json, sys, glob
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
SER = MAIN/".cache"/"ohlcv"/"series"
ret_sum=defaultdict(float); ret_n=defaultdict(int)
for fp in glob.glob(str(SER/"*.json")):
    try: s=json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception: continue
    d,c=s.get("dates") or [], s.get("closes") or []
    for i in range(1,len(c)):
        if c[i] and c[i-1] and 0.5<c[i]/c[i-1]<2.0:
            ret_sum[d[i]]+=c[i]/c[i-1]-1; ret_n[d[i]]+=1
dates=sorted(k for k in ret_sum if ret_n[k]>=100)
v=100.0; out={}
for d in dates:
    v*=1+ret_sum[d]/ret_n[d]; out[d]=v
Path("idx.json").write_text(json.dumps(out), encoding="utf-8")
print("index days", len(out), dates[0], dates[-1])
