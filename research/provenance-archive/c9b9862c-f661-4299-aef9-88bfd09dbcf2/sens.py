# -*- coding: utf-8 -*-
"""국면정의 민감도 · 기간분할 · 월별분포 — 선행 시뮬레이터(재현본) 기준."""
import sys, random, statistics as st
from collections import defaultdict, Counter
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim
from nulltest import run_prior, C, ALLD, SD

def med(events, seeds=300):
    rs = [run_prior(events, s) for s in range(seeds)]
    return (st.median([x[0] for x in rs]), st.median([x[1] for x in rs]),
            st.median([x[2] / max(x[1], 1) * 100 for x in rs]))

def show(lab, flags):
    ev = [e for e in C if flags.get(e['scan_date'])]
    if not ev:
        print(f"{lab:<28} 후보 0"); return
    f, n, w = med(ev)
    pt = sum(e['net'] for e in ev) / len(ev) * 100
    print(f"{lab:<28} 후보 {len(ev):>3} · 체결 {n:>3.0f} · 자산 {f:>+7.1f}% · 체결승률 {w:>4.1f}% · 후보건당순 {pt:>+5.2f}%")

print("── 기준선")
show("전부매수", {d: True for d in SD})
print("\n── 국면 정의 민감도(등가중 시점지수, 단순MA)")
MY = sim.MY
for w in (5, 10, 15, 20, 25, 30, 40, 50, 60):
    fl = sim.regime_flags(MY['dates'], MY['ew_all'], w)
    show(f"지수>MA{w}", fl)

print("\n── 대안 정의")
# MA20 상승(기울기) 조건
fl20 = sim.regime_flags(MY['dates'], MY['ew_all'], 20)
ma20 = {}
lv = MY['ew_all']; dts = MY['dates']
for i, d in enumerate(dts):
    ma20[d] = sum(lv[i-19:i+1])/20 if i >= 19 else None
slope = {d: (ma20[d] is not None and ma20[dts[i-1]] is not None and ma20[d] > ma20[dts[i-1]]) for i, d in enumerate(dts) if i >= 1}
show("MA20 기울기 상승만", slope)
show("지수>MA20 AND 기울기상승", {d: bool(fl20.get(d)) and bool(slope.get(d)) for d in dts})
flcw = sim.regime_flags(MY['dates'], MY['cw'], 20)
show("시총가중지수>MA20", flcw)
show("조정국면만(지수<MA20)", {d: not fl20.get(d) for d in dts if fl20.get(d) is not None})

print("\n── 기간분할 (지수>MA20)")
for lab, s, e in (("전반 2025-11~2026-03", "2025-11-01", "2026-03-31"),
                  ("후반 2026-04~2026-08", "2026-04-01", "2026-08-31")):
    sub = [x for x in C if s <= x['entry_date'] <= e]
    ev_all = sub
    ev_up = [x for x in sub if fl20.get(x['scan_date'])]
    fa, na, wa = med(ev_all); fu, nu, wu = med(ev_up)
    pa = sum(x['net'] for x in ev_all)/len(ev_all)*100
    pu = sum(x['net'] for x in ev_up)/len(ev_up)*100
    print(f"{lab}: 전부 후보{len(ev_all):>3} 체결{na:>3.0f} 자산{fa:>+7.1f}% 건당{pa:+.2f}%  |  상승만 후보{len(ev_up):>3} 체결{nu:>3.0f} 자산{fu:>+7.1f}% 건당{pu:+.2f}%")

print("\n── 국면필터 체결 69건 월별 분포 (300회 평균)")
upev = [e for e in C if fl20.get(e['scan_date'])]
cnt = Counter(); tot = 0
byday = defaultdict(list)
for e in upev:
    byday[e['entry_date']].append(e)
for s in range(300):
    rnd = random.Random(s)
    eq, held = 1.0, []
    for d in ALLD:
        for rd, e, wgt in [h for h in held if h[0] <= d]:
            eq += wgt * e['net']
        held = [h for h in held if h[0] > d]
        free = 5 - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c)
            for e in c[:free]:
                held.append((e['resolve_date'], e, eq / 5))
                cnt[e['entry_date'][:7]] += 1; tot += 1
for mth in sorted(cnt):
    print(f"  {mth}  체결 {cnt[mth]/300:>5.1f}건  ({cnt[mth]/tot*100:>4.1f}%)")
print(f"  합계 {tot/300:.1f}건")
print("\n── 후보(체결 전) 월별 분포")
ca = Counter(e['entry_date'][:7] for e in C)
cu = Counter(e['entry_date'][:7] for e in upev)
for mth in sorted(ca):
    print(f"  {mth}  전체 {ca[mth]:>3}건 · 상승국면 {cu.get(mth,0):>3}건 · 월평균순 {sum(e['net'] for e in C if e['entry_date'][:7]==mth)/ca[mth]*100:>+6.2f}%")
