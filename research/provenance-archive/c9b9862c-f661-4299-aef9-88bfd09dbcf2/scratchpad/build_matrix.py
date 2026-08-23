# -*- coding: utf-8 -*-
"""series 캐시 -> 날짜별 breadth 계열 지표 (200MA 위 비율, 52주 신고가 수)"""
import json, os, glob, pickle
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
SD = ROOT/".cache"/"ohlcv"/"series"
OUT = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")

files = sorted(SD.glob("*.json"))
print("files", len(files))

# 전체 날짜 축 (가장 긴 시계열 기준 합집합)
all_dates = set()
data = {}
for i,f in enumerate(files):
    code = f.stem
    try:
        s = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        continue
    if not s.get('closes'): continue
    data[code] = (s['dates'], s['closes'])
    all_dates.update(s['dates'])
    if (i+1)%500==0: print(i+1, flush=True)

dates = sorted(all_dates)
di = {d:i for i,d in enumerate(dates)}
N = len(dates)
print("dates", N, dates[0], dates[-1])

above200 = [0]*N; tot200 = [0]*N
nh52 = [0]*N; tot52 = [0]*N

for code,(ds,cs) in data.items():
    # 정렬 가정: 오름차순
    n = len(ds)
    # 누적합으로 MA200
    run = 0.0
    csum = [0.0]*(n+1)
    ok = [c for c in cs]
    for i,c in enumerate(cs):
        csum[i+1] = csum[i] + (c if c else 0.0)
    for i in range(n):
        c = cs[i]
        if not c: continue
        gi = di[ds[i]]
        if i >= 199:
            ma = (csum[i+1]-csum[i+1-200])/200.0
            tot200[gi]+=1
            if c > ma: above200[gi]+=1
        # 52주(250거래일) 신고가: 최근 250일 중 최고 종가와 같거나 초과
        lo = max(0, i-249)
        if i-lo+1 >= 200:   # 최소 200일 이력
            win = [x for x in cs[lo:i+1] if x]
            tot52[gi]+=1
            if win and c >= max(win)*0.999:
                nh52[gi]+=1

out = {'dates':dates,'above200':above200,'tot200':tot200,'nh52':nh52,'tot52':tot52}
(OUT/"breadth_series.json").write_text(json.dumps(out), encoding='utf-8')
print("saved")
for d in ['2026-08-20','2026-08-21','2026-03-25']:
    if d in di:
        g=di[d]; print(d, 'above200 %.1f%%'%(100*above200[g]/max(1,tot200[g])), 'nh52', nh52[g], '/', tot52[g])
