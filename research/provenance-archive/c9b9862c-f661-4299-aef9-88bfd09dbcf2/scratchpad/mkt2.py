import sys, os, json, glob
os.chdir(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
from collections import defaultdict
files = glob.glob('.cache/ohlcv/series/*.json')
shvol=defaultdict(float); low52c=defaultdict(int); low52_all=defaultdict(int); cnt=defaultdict(int)
start='2026-07-28'
for f in files:
    code=os.path.basename(f).split('.')[0]
    try: s=ohlcv_matrix.get_series(code)
    except Exception: continue
    if not s: continue
    d=s['dates']; c=s['closes']; v=s['volumes']; lo=s['lows']
    if not d or d[-1] < '2026-08-01': continue
    for i in range(len(d)):
        if d[i]<start: continue
        cnt[d[i]]+=1
        if v[i]: shvol[d[i]]+=v[i]
        if i>=250:
            w=c[i-250:i+1]
            if all(x is not None for x in w) and c[i]<=min(w): 
                low52c[d[i]]+=1
            wl=lo[i-250:i+1]
            if all(x is not None for x in wl) and lo[i]<=min(wl):
                low52_all[d[i]]+=1   # includes halted (v=0)
print("date n shvol(억주) low52close low52low_inclHalted")
for dt in sorted(cnt):
    print(dt, cnt[dt], f"{shvol[dt]/1e8:.2f}", low52c[dt], low52_all[dt])
