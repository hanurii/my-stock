# -*- coding: utf-8 -*-
"""회의적 재검증: 청산 규칙 시뮬레이터 (독립 구현 + 원안 재현 스위치)."""
import json, sys, statistics, random
from collections import defaultdict
sys.path.insert(0, r'C:\Users\hanul\playground\my-stock\scripts')
from canslim_lib import ohlcv_matrix

MAIN = r'C:\Users\hanul\playground\my-stock'
D = json.load(open(MAIN + r'\public\data\backtest-volatility-pilot.json', encoding='utf-8'))
EV = []
for e in D['events']:
    s = ohlcv_matrix.get_series(e['code'])
    if not s: continue
    try: b = s['dates'].index(e['entry_date'])
    except ValueError: continue
    e = dict(e); e['_s'] = s; e['_b'] = b
    EV.append(e)
LASTDATE = EV[0]['_s']['dates'][-1]

def sim(e, target=20.0, stop=10.0, trail=None, maxh=120,
        basis='pivot', gapfill=False, cost=0.0, time_stop=None):
    """basis: 손절/익절 기준가(pivot=원안, entry=진입가).
    gapfill: True면 갭 하락 시 시가 체결(현실), False면 스톱 레벨 그대로(원안).
    cost: 왕복 비용 %p 차감."""
    s = e['_s']; b = e['_b']; ep = e['entry_price']
    ref = e['pivot'] if basis == 'pivot' else ep
    H, L, C, O, Dt = s['highs'], s['lows'], s['closes'], s['opens'], s['dates']
    n = len(C)
    T = ref * (1 + target / 100.0)
    S = ref * (1 - stop / 100.0)
    peak = None
    end = min(n, b + maxh + 1)
    for i in range(b, end):
        k = i - b
        hi, lo, cl, op = H[i], L[i], C[i], (O[i] if O else None)
        if hi is None or lo is None:
            continue
        ht = hi >= T; hs = lo <= S
        def fill(level):
            if gapfill and op is not None and op < level:
                return op
            return level
        if ht and hs: return (fill(S)/ep-1)*100 - cost, 'amb', k, Dt[i]
        if ht:
            px = max(op, T) if (gapfill and op is not None and op > T) else T
            return (px/ep-1)*100 - cost, 'win', k, Dt[i]
        if hs: return (fill(S)/ep-1)*100 - cost, 'loss', k, Dt[i]
        if time_stop and k >= time_stop[0] and (cl/ep-1)*100 < time_stop[1]:
            return (cl/ep-1)*100 - cost, 'timestop', k, Dt[i]
        if trail:
            peak = cl if peak is None else max(peak, cl)
            S = max(S, peak * (1 - trail/100.0))
    i = end - 1
    return (C[i]/ep-1)*100 - cost, 'open', i-b, Dt[i]

def run(evs=None, **kw):
    evs = EV if evs is None else evs
    return [(e, sim(e, **kw)) for e in evs]

def stat(rows):
    rs = [r[1][0] for r in rows]
    g = [x for x in rs if x > 0]; l = [x for x in rs if x <= 0]
    return dict(n=len(rs), mean=statistics.mean(rs), med=statistics.median(rs),
                winpct=100*len(g)/len(rs),
                avgW=statistics.mean(g) if g else 0, avgL=statistics.mean(l) if l else 0,
                days=statistics.mean(r[1][2] for r in rows),
                open=sum(1 for r in rows if r[1][1]=='open'))

def show(rows, label):
    d = stat(rows)
    print(f"{label:34s} n={d['n']:4d} 평균={d['mean']:+6.2f}% 중앙={d['med']:+6.2f} "
          f"승률={d['winpct']:5.1f}% 평균익={d['avgW']:+6.2f} 평균손={d['avgL']:+6.2f} "
          f"보유={d['days']:5.1f}일 미결={d['open']:3d}")
    return d['mean']
