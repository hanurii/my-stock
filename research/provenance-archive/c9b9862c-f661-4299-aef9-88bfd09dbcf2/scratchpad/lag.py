# -*- coding: utf-8 -*-
import sys, statistics as st
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim
from nulltest import run_prior, C

def med(ev, seeds=300):
    r = [run_prior(ev, s) for s in range(seeds)]
    return st.median([x[0] for x in r]), st.median([x[1] for x in r]), \
           st.median([x[2]/max(x[1],1)*100 for x in r])

cal = sim.MY['dates']; idx = {d: i for i, d in enumerate(cal)}
fl = sim.regime_flags(cal, sim.MY['ew_all'], 20)
print("[국면 판정일을 며칠 더 늦추면? — 신호 지연 내성]")
for lag in (0, 1, 2, 3, 5):
    ev = [e for e in C if idx.get(e['scan_date'], 0) - lag >= 0 and fl.get(cal[idx[e['scan_date']] - lag])]
    f, n, w = med(ev)
    pt = sum(x['net'] for x in ev)/len(ev)*100
    print(f"  lag {lag}일 → 후보 {len(ev):>3} · 체결 {n:>3.0f} · 자산 {f:>+7.1f}% · 승률 {w:.1f}% · 건당순 {pt:+.2f}%")

print("\n[지수 소스별 (MA20)]")
srcs = {'등가중 시점지수(상폐포함, 내가재현)': sim.MY['ew_all'],
        '시총가중 시점지수': sim.MY['cw']}
for lab, lv in srcs.items():
    f2 = sim.regime_flags(cal, lv, 20)
    ev = [e for e in C if f2.get(e['scan_date'])]
    f, n, w = med(ev); pt = sum(x['net'] for x in ev)/len(ev)*100
    print(f"  {lab:<28} 후보 {len(ev):>3} 체결 {n:>3.0f} 자산 {f:>+7.1f}% 건당순 {pt:+.2f}%")
ev = [e for e in C if sim.PITUP.get(e['scan_date'])]
f, n, w = med(ev); pt = sum(x['net'] for x in ev)/len(ev)*100
print(f"  {'제공된 pit_index up[]':<28} 후보 {len(ev):>3} 체결 {n:>3.0f} 자산 {f:>+7.1f}% 건당순 {pt:+.2f}%")
lv = {r['date']: r['up'] for r in __import__('json').load(open(r'C:\Users\hanul\playground\my-stock\public\data\market-regime.json', encoding='utf-8'))['series']}
ev = [e for e in C if lv.get(e['scan_date'])]
f, n, w = med(ev); pt = sum(x['net'] for x in ev)/len(ev)*100
print(f"  {'라이브 market-regime(생존편향)':<28} 후보 {len(ev):>3} 체결 {n:>3.0f} 자산 {f:>+7.1f}% 건당순 {pt:+.2f}%")

print("\n[코스피/코스닥 지수 기준 국면 — 외부 벤치마크]")
import FinanceDataReader as fdr
try:
    for lab, tic in (("KOSPI", "KS11"), ("KOSDAQ", "KQ11")):
        df = fdr.DataReader(tic, '2025-06-01', '2026-08-21')
        dts = [d.strftime('%Y-%m-%d') for d in df.index]
        lvl = list(df['Close'])
        f3 = sim.regime_flags(dts, lvl, 20)
        ev = [e for e in C if f3.get(e['scan_date'])]
        if not ev: print(f"  {lab}: 후보 0"); continue
        f, n, w = med(ev); pt = sum(x['net'] for x in ev)/len(ev)*100
        print(f"  {lab}>MA20  후보 {len(ev):>3} 체결 {n:>3.0f} 자산 {f:>+7.1f}% 건당순 {pt:+.2f}%")
except Exception as ex:
    print("  FDR 실패:", ex)
