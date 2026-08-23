# -*- coding: utf-8 -*-
import sys, statistics as st
from collections import Counter, defaultdict
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim
from nulltest import run_prior, C, SD

fl = sim.regime_flags(sim.MY['dates'], sim.MY['ew_all'], 20)
UPEV = [e for e in C if fl.get(e['scan_date'])]

def med(ev, seeds=200):
    r = [run_prior(ev, s) for s in range(seeds)]
    return st.median([x[0] for x in r]), st.median([x[1] for x in r])

months = sorted({e['entry_date'][:7] for e in C})
base_up, n_up = med(UPEV); base_all, n_all = med(C)
print(f"기준 상승만 {base_up:+.1f}% ({n_up:.0f}건) · 전부 {base_all:+.1f}% ({n_all:.0f}건)")
print("\n[한 달씩 빼고 재계산]")
for m in months:
    u = [e for e in UPEV if e['entry_date'][:7] != m]
    a = [e for e in C if e['entry_date'][:7] != m]
    fu, nu = med(u); fa, na = med(a)
    print(f"  {m} 제외 → 상승만 {fu:>+7.1f}% ({nu:>3.0f}건) · 전부 {fa:>+7.1f}% ({na:>3.0f}건) · 차 {fu-fa:>+6.1f}%p")

print("\n[상승국면 체결거래 월별 평균 순수익]")
import random
cnt = Counter(); ssum = Counter()
byday = defaultdict(list)
for e in UPEV:
    byday[e['entry_date']].append(e)
from nulltest import ALLD
for s in range(300):
    rnd = random.Random(s); eq, held = 1.0, []
    for d in ALLD:
        for rd, e, wgt in [h for h in held if h[0] <= d]:
            eq += wgt * e['net']
        held = [h for h in held if h[0] > d]
        free = 5 - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c)
            for e in c[:free]:
                held.append((e['resolve_date'], e, eq/5))
                cnt[e['entry_date'][:7]] += 1; ssum[e['entry_date'][:7]] += e['net']*100
for m in sorted(cnt):
    print(f"  {m} 체결 {cnt[m]/300:>5.1f}건 · 평균순 {ssum[m]/cnt[m]:>+6.2f}% · 월기여(건수×평균) {cnt[m]/300*ssum[m]/cnt[m]/5:>+6.2f}%p")
