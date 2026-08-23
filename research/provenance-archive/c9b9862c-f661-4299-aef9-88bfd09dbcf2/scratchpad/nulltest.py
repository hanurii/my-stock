# -*- coding: utf-8 -*-
"""국면필터 우위가 '선택' 때문인지 '덜 사서'인지 분리 — 널 분포 3종."""
import sys, random, statistics as st
from collections import defaultdict
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim

C = [e for e in sim.EV if e['result'] in ('win', 'loss')]
SD = sorted({e['scan_date'] for e in C})
UP = {d: sim.MYF[20][d] for d in SD}
N_UP = sum(1 for d in SD if UP[d])
ALLD = sorted({e['entry_date'] for e in C} | {e['resolve_date'] for e in C})

BY = defaultdict(list)
for e in C:
    BY[e['entry_date']].append(e)


def run_prior(events, seed, slots=5):
    """선행 에이전트 방식 재현: 현금 제약 없음, 결착<=당일 먼저 처리."""
    byday = defaultdict(list)
    for e in events:
        byday[e['entry_date']].append(e)
    rnd = random.Random(seed)
    eq, held, n, w = 1.0, [], 0, 0
    for d in ALLD:
        done = [h for h in held if h[0] <= d]
        for rd, e, wgt in done:
            eq += wgt * e['net']; n += 1; w += (e['result'] == 'win')
        held = [h for h in held if h[0] > d]
        free = slots - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c)
            for e in c[:free]:
                held.append((e['resolve_date'], e, eq / slots))
    return (eq - 1) * 100, n, w


def med_final(events, seeds=40, start=0):
    rs = [run_prior(events, s)[0] for s in range(start, start + seeds)]
    return st.median(rs)


# 검증: 선행 결과 재현
allf = [run_prior(C, s) for s in range(300)]
upev = [e for e in C if UP[e['scan_date']]]
upf = [run_prior(upev, s) for s in range(300)]
print(f"재현 · 전부매수 자산중앙 {st.median([x[0] for x in allf]):+.1f}% (체결 {st.median([x[1] for x in allf]):.0f}건)")
print(f"재현 · 상승국면만 자산중앙 {st.median([x[0] for x in upf]):+.1f}% (체결 {st.median([x[1] for x in upf]):.0f}건)")
real = st.median([x[0] for x in upf])
real_n = st.median([x[1] for x in upf])

# ── 널 A: 무작위 날짜 89일 허용 (거래일수 동일, 국면 무관)
rnd = random.Random(3)
nullA = []
for _ in range(400):
    days = SD[:]; rnd.shuffle(days)
    lab = set(days[:N_UP])
    ev = [e for e in C if e['scan_date'] in lab]
    nullA.append(med_final(ev, seeds=25))
nullA.sort()
pA = sum(1 for x in nullA if x >= real) / len(nullA)
print(f"\n[널A 무작위 날짜 {N_UP}/{len(SD)}일] 중앙 {st.median(nullA):+.1f}% · P90 {nullA[int(.9*len(nullA))]:+.1f}% · P95 {nullA[int(.95*len(nullA))]:+.1f}% · 실제 {real:+.1f}% → p={pA:.3f}")

# ── 널 B: 무작위 거래 표집 (건수만 맞춤, 날짜 구조 무시)
rnd2 = random.Random(5)
k = len(upev)
nullB = []
for _ in range(400):
    ev = rnd2.sample(C, k)
    nullB.append(med_final(ev, seeds=25))
nullB.sort()
pB = sum(1 for x in nullB if x >= real) / len(nullB)
print(f"[널B 무작위 거래 {k}/{len(C)}건] 중앙 {st.median(nullB):+.1f}% · P95 {nullB[int(.95*len(nullB))]:+.1f}% · 실제 {real:+.1f}% → p={pB:.3f}")

# ── 널C: 체결건수 69건에 맞춘 무작위 축소 (덜 사기 그 자체)
targets = []
for frac in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
    rnd3 = random.Random(int(frac * 100))
    outs, ns = [], []
    for _ in range(60):
        ev = rnd3.sample(C, max(1, int(len(C) * frac)))
        f, n, w = run_prior(ev, rnd3.randrange(10000))
        outs.append(f); ns.append(n)
    print(f"  후보 {frac*100:>3.0f}% 무작위 축소 → 체결중앙 {st.median(ns):>4.0f}건 · 자산중앙 {st.median(outs):+7.1f}%")

# ── 널 D: 원형이동 국면 라벨
nullD = []
for kk in range(1, len(SD)):
    lab = {SD[i]: UP[SD[(i - kk) % len(SD)]] for i in range(len(SD))}
    ev = [e for e in C if lab[e['scan_date']]]
    nullD.append(med_final(ev, seeds=25))
nullD.sort()
pD = sum(1 for x in nullD if x >= real) / len(nullD)
print(f"\n[널D 국면라벨 원형이동 {len(nullD)}회] 중앙 {st.median(nullD):+.1f}% · P95 {nullD[int(.95*len(nullD))]:+.1f}% · 실제 {real:+.1f}% → p={pD:.3f}")
