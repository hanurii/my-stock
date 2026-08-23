# -*- coding: utf-8 -*-
import sys, statistics as st
from collections import defaultdict
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim
from nulltest import C, SD

cal = sim.MY['dates']; idx = {d: i for i, d in enumerate(cal)}
fl = sim.regime_flags(cal, sim.MY['ew_all'], 20)

# 1) 검증구간 국면 에피소드 수 (독립 관측 개수)
win = [d for d in cal if '2025-11-26' <= d <= '2026-08-20']
runs = []
cur = None
for d in win:
    v = fl.get(d)
    if cur is None or v != cur[0]:
        runs.append([v, d, d]); cur = runs[-1]
    else:
        cur[2] = d
print(f"[국면 에피소드] 총 {len(runs)}구간 (상승 {sum(1 for r in runs if r[0])} · 조정 {sum(1 for r in runs if not r[0])})")
for v, a, b in runs:
    nd = idx[b] - idx[a] + 1
    ev = [e for e in C if a <= e['scan_date'] <= b]
    mm = sum(x['net'] for x in ev)/len(ev)*100 if ev else None
    print(f"  {'상승' if v else '조정'} {a}~{b} ({nd:>3}일) 거래 {len(ev):>3}건 평균순 {('%+.2f%%' % mm) if mm is not None else '-'}")

# 2) 월내 층화 비교 (달력 교란 제거)
print("\n[월내 층화: 같은 달 안에서 상승일 vs 조정일]")
by = defaultdict(lambda: ([], []))
for e in C:
    (by[e['scan_date'][:7]][0] if fl.get(e['scan_date']) else by[e['scan_date'][:7]][1]).append(e)
ds, ws = [], []
for m in sorted(by):
    u, d = by[m]
    if u and d:
        mu = sum(x['net'] for x in u)/len(u)*100; md = sum(x['net'] for x in d)/len(d)*100
        w = min(len(u), len(d))
        ds.append((mu-md)*w); ws.append(w)
        print(f"  {m} 상승 n={len(u):>3} {mu:>+6.2f}% · 조정 n={len(d):>3} {md:>+6.2f}% · 차 {mu-md:>+6.2f}%p")
print(f"  가중평균 차이 {sum(ds)/sum(ws):+.2f}%p (대조 가능한 달 {len(ws)}개)")

# 3) 국면이 '시장 앞날'을 예측했나 (10거래일 선행 등가중 수익)
print("\n[국면상태 → 이후 10거래일 등가중지수 수익]")
lv = sim.MY['ew_all']
up_f, dn_f = [], []
for i, d in enumerate(cal):
    if not ('2025-11-26' <= d <= '2026-08-20') or i + 10 >= len(cal):
        continue
    r = (lv[i+10]/lv[i]-1)*100
    (up_f if fl.get(d) else dn_f).append(r)
print(f"  상승국면일 n={len(up_f)} 평균 {sum(up_f)/len(up_f):+.2f}% · 조정국면일 n={len(dn_f)} 평균 {sum(dn_f)/len(dn_f):+.2f}%")
