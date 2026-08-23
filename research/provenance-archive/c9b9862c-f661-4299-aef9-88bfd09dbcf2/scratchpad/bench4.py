# -*- coding: utf-8 -*-
import json, sys, time, tracemalloc
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
SER = ROOT / ".cache" / "ohlcv" / "series"
try:
    import psutil, os
    proc = psutil.Process(os.getpid())
    def rss(): return proc.memory_info().rss/1024/1024
    print("psutil OK, base", round(rss(),1))
except ImportError:
    tracemalloc.start()
    def rss(): return tracemalloc.get_traced_memory()[0]/1024/1024
    print("tracemalloc, base", round(rss(),1))

files=sorted(SER.glob("*.json"))
store={}
t0=time.time()
for f in files:
    try: store[f.stem]=json.loads(f.read_text(encoding="utf-8"))
    except Exception: pass
print(f"전종목 {len(store)}  로드 {time.time()-t0:.1f}s  메모리 {rss():.0f} MB")
# 필요한 배열만 (closes/highs/lows/volumes/dates) 유지 시
t0=time.time()
slim={}
for c,s in store.items():
    slim[c]={k:s[k] for k in ("dates","closes","highs","lows","volumes") if k in s}
print(f"slim 사본 추가 후 {rss():.0f} MB")
