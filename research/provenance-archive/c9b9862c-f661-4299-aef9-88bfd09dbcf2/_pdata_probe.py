import json, time
from pathlib import Path
PD = Path(r'C:\Users\hanul\playground\my-stock\.cache\pdata')
files = sorted(PD.glob('price_*.json'))
files = [f for f in files if f.stem[6:14] >= '20240101']
print('files from 2024:', len(files), files[0].stem, files[-1].stem)
t0 = time.perf_counter()
codes_by_day = {}
CHK = ['005930', '000660', '204610']
ser = {c: {'d': [], 'c': [], 'f': []} for c in CHK}
for f in files:
    bd = f.stem[6:14]
    iso = f'{bd[:4]}-{bd[4:6]}-{bd[6:]}'
    d = json.loads(f.read_text(encoding='utf-8'))
    codes_by_day[iso] = set(d.keys())
    for c in CHK:
        r = d.get(c)
        if r:
            ser[c]['d'].append(iso); ser[c]['c'].append(r['clpr']); ser[c]['f'].append(r.get('fltRt'))
print('load', round(time.perf_counter()-t0,1), 's')

# survivorship: codes present on 2025-06-02 that are gone by last day
last = max(codes_by_day)
for day in ['2025-06-02', '2025-01-02', '2024-06-03']:
    if day in codes_by_day:
        a = codes_by_day[day]; b = codes_by_day[last]
        print(f'{day}: listed {len(a)} | gone by {last}: {len(a-b)} ({100*len(a-b)/len(a):.1f}%) | new since: {len(b-a)}')

# reconstruct adjusted closes (same chain as ohlcv_matrix._apply_adjustment) and compare with cache
import sys
sys.path.insert(0, r'C:\Users\hanul\playground\my-stock\scripts')
from canslim_lib import ohlcv_matrix as om
for c in CHK:
    d, cl, fl = ser[c]['d'], ser[c]['c'], ser[c]['f']
    n = len(cl)
    adj = [0.0]*n; adj[-1] = cl[-1]
    for i in range(n-2, -1, -1):
        f = fl[i+1]
        ratio = 1.0 + float(f)/100.0 if f is not None else (cl[i+1]/cl[i] if cl[i] else 1.0)
        adj[i] = adj[i+1]/ratio if ratio else adj[i+1]
    cache = om.get_series(c)
    if not cache:
        print(c, 'no cache'); continue
    m = {dt: v for dt, v in zip(cache['dates'], cache['closes'])}
    diffs = [abs(adj[i]/m[d[i]]-1) for i in range(n) if d[i] in m and m[d[i]]]
    print(f'{c}: pdata bars {n} ({d[0]}~{d[-1]}) | overlap {len(diffs)} | max rel diff {max(diffs):.5f} | mean {sum(diffs)/len(diffs):.6f}')
