# -*- coding: utf-8 -*-
import sys, json, random, statistics as st
from collections import defaultdict
sys.path.insert(0, r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
import sim

C = [e for e in sim.EV if e['result'] in ('win', 'loss')]
SD = sorted({e['scan_date'] for e in C})
byd = defaultdict(list)
for e in C:
    byd[e['scan_date']].append(e)
UP = {d: sim.MYF[20][d] for d in SD}
n_up_days = sum(1 for d in SD if UP[d])

def m(evs):
    return sum(e['net'] for e in evs) / len(evs) * 100 if evs else 0.0

up_ev = [e for e in C if UP[e['scan_date']]]
dn_ev = [e for e in C if not UP[e['scan_date']]]
diff = m(up_ev) - m(dn_ev)
print(f"[거래단위] 상승 n={len(up_ev)} 평균순 {m(up_ev):+.2f}% / 조정 n={len(dn_ev)} 평균순 {m(dn_ev):+.2f}% / 차 {diff:+.2f}%p")

# ── (1) 일자 클러스터 부트스트랩: 날짜를 복원추출
rnd = random.Random(7)
ds = []
for _ in range(5000):
    days = [rnd.choice(SD) for _ in SD]
    u, d_ = [], []
    for day in days:
        (u if UP[day] else d_).extend(byd[day])
    if u and d_:
        ds.append(m(u) - m(d_))
ds.sort()
p_boot = sum(1 for x in ds if x <= 0) / len(ds)
print(f"  일자 부트스트랩 5000회: 차이 중앙 {st.median(ds):+.2f}%p, 95%CI [{ds[int(.025*len(ds))]:+.2f}, {ds[int(.975*len(ds))]:+.2f}], P(차<=0)={p_boot:.4f}")

# ── (2) 원형 이동 순열검정 (자기상관 보존)
shifts = []
for k in range(1, len(SD)):
    lab = {SD[i]: UP[SD[(i - k) % len(SD)]] for i in range(len(SD))}
    u = [e for e in C if lab[e['scan_date']]]
    d_ = [e for e in C if not lab[e['scan_date']]]
    if u and d_:
        shifts.append(m(u) - m(d_))
shifts.sort()
p_shift = sum(1 for x in shifts if x >= diff) / len(shifts)
print(f"  원형이동 순열 {len(shifts)}회: 실제 {diff:+.2f}%p, 널 중앙 {st.median(shifts):+.2f}, 널 P95 {shifts[int(.95*len(shifts))]:+.2f}, p={p_shift:.4f}")

# ── (3) 일자 라벨 무작위(상승일수 고정) 순열검정
rnd2 = random.Random(11)
perm = []
for _ in range(5000):
    days = SD[:]
    rnd2.shuffle(days)
    lab = set(days[:n_up_days])
    u = [e for e in C if e['scan_date'] in lab]
    d_ = [e for e in C if e['scan_date'] not in lab]
    perm.append(m(u) - m(d_))
perm.sort()
p_perm = sum(1 for x in perm if x >= diff) / len(perm)
print(f"  일자라벨 무작위 5000회: p={p_perm:.4f} (널 중앙 {st.median(perm):+.2f}, P95 {perm[int(.95*len(perm))]:+.2f})")
