# -*- coding: utf-8 -*-
import os, sys, random, statistics
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as S
from sim2 import sim_one, exit_date, SAMPLE, H
random.seed(31)

a = {id(e): sim_one(e, H) for e in SAMPLE}
f = {id(e): sim_one(e, H, trail=0.10, trail_after=0.20) for e in SAMPLE}

print("=" * 96)
print("[12] (f) 이익의 출처 — +20% 도달분(현행 익절 대상)에 무슨 일이 생기나")
print("=" * 96)
winners = [e for e in SAMPLE if a[id(e)][2] == "target"]
print(f"현행에서 +20% 익절된 거래: {len(winners)}/{len(SAMPLE)} ({len(winners)/len(SAMPLE)*100:.1f}%)")
fa = [a[id(e)][0] for e in winners]; ff = [f[id(e)][0] for e in winners]
print(f"  현행 평균 {sum(fa)/len(fa):+.2f}%  →  (f) 전환 평균 {sum(ff)/len(ff):+.2f}%  (중앙 {statistics.median(fa):+.1f} → {statistics.median(ff):+.1f})")
worse = sum(1 for x, y in zip(fa, ff) if y < x - 0.01)
better = sum(1 for x, y in zip(fa, ff) if y > x + 0.01)
print(f"  전환해서 더 벌린 건 {better}건, 되뱉은 건 {worse}건, 동일 {len(fa)-better-worse}건")
print(f"  되뱉은 건들의 평균 손실 {sum(y-x for x,y in zip(fa,ff) if y<x-0.01)/max(worse,1):+.2f}%p,"
      f" 더 벌린 건들의 평균 이득 {sum(y-x for x,y in zip(fa,ff) if y>x+0.01)/max(better,1):+.2f}%p")
gains = sorted(((f[id(e)][0] - a[id(e)][0]), e["name"], e["entry_date"], a[id(e)][0], f[id(e)][0]) for e in SAMPLE)
print("  상위 기여 5건:", ", ".join(f"{g[1]}({g[2]}) {g[3]:.0f}→{g[4]:.0f}%" for g in gains[-5:][::-1]))
tot = sum(f[id(e)][0] - a[id(e)][0] for e in SAMPLE)
top10 = sum(g[0] for g in gains[-10:])
print(f"  (f)-(a) 총 개선 {tot:.0f}%p 중 상위 10건이 {top10:.0f}%p = {top10/tot*100:.0f}%")

print()
print("=" * 96)
print("[13] +20% 도달 후 처리 방식 비교 (사후 선택 격자 — 과적합 주의)")
print("=" * 96)
print(f"{'방식':<28}{'승률':>7}{'평균이익':>9}{'평균손실':>9}{'손익비':>7}{'기대값':>8}{'평균보유':>9}")
grid = [("현행 +20% 전량익절", dict()),
        ("+20%후 추적 -8%", dict(trail=0.08, trail_after=0.20)),
        ("+20%후 추적 -10%", dict(trail=0.10, trail_after=0.20)),
        ("+20%후 추적 -12%", dict(trail=0.12, trail_after=0.20)),
        ("+20%후 추적 -15%", dict(trail=0.15, trail_after=0.20)),
        ("+20%후 추적 -20%", dict(trail=0.20, trail_after=0.20)),
        ("+15%후 추적 -10%", dict(target=0.15, trail=0.10, trail_after=0.15)),
        ("+30%후 추적 -10%", dict(target=0.30, trail=0.10, trail_after=0.30)),
        ("+20%후 20일선 이탈까지", dict(trail=None, trail_after=None))]
for nm, kw in grid[:-1]:
    st = S.stats([sim_one(e, H, **kw) for e in SAMPLE])
    print(f"{nm:<28}{st['승률']:>7}{st['평균이익']:>9}{st['평균손실']:>9}{str(st['손익비']):>7}{st['기대값']:>8}{st['평균보유일']:>9}")

print()
print("=" * 96)
print("[14] 절반 익절 + 절반 추적 (실무형) — 현행/(f) 대비")
print("=" * 96)
def half(e):
    r_a = sim_one(e, H)
    if r_a[2] != "target":
        return r_a
    r_f = sim_one(e, H, trail=0.10, trail_after=0.20)
    return ((r_a[0] + r_f[0]) / 2, r_f[1], "half")
for nm, rows in [("(a) 현행", [a[id(e)] for e in SAMPLE]),
                 ("(h) 절반익절+절반추적-10%", [half(e) for e in SAMPLE]),
                 ("(f) 전량 추적-10%", [f[id(e)] for e in SAMPLE])]:
    st = S.stats(rows)
    print(f"{nm:<28}{st['승률']:>7}{st['평균이익']:>9}{st['평균손실']:>9}{str(st['손익비']):>7}{st['기대값']:>8}{st['평균보유일']:>9}")

print()
print("=" * 96)
print("[15] (f)-(a) 차이의 전후반 · 패턴별 · 블록 부트스트랩")
print("=" * 96)
bycode = defaultdict(list)
for e in SAMPLE: bycode[e["code"]].append(e)
codes = list(bycode)
def boot(sub):
    ids = set(id(e) for e in sub)
    cs = [c for c in codes if any(id(e) in ids for e in bycode[c])]
    ds = []
    for _ in range(4000):
        num = 0.0; n = 0
        for c in (random.choice(cs) for _ in cs):
            for e in bycode[c]:
                if id(e) in ids:
                    num += f[id(e)][0] - a[id(e)][0]; n += 1
        ds.append(num / n if n else 0.0)
    ds.sort()
    p = 2 * min(sum(1 for d in ds if d <= 0), sum(1 for d in ds if d >= 0)) / len(ds)
    return sum(f[id(e)][0] - a[id(e)][0] for e in sub) / len(sub), ds[100], ds[3899], min(p, 1.0)
for nm, sub in [("전체", SAMPLE),
                ("전반(~03-24 진입)", [e for e in SAMPLE if e["entry_date"] < "2026-03-25"]),
                ("후반(03-25~ 진입)", [e for e in SAMPLE if e["entry_date"] >= "2026-03-25"]),
                ("VCP", [e for e in SAMPLE if e["pattern"] == "VCP"]),
                ("3C", [e for e in SAMPLE if e["pattern"] == "3C"]),
                ("PP", [e for e in SAMPLE if e["pattern"] == "PP"])]:
    d, lo, hi, p = boot(sub)
    print(f"{nm:<20} n={len(sub):>4}  (f)-(a) 기대값차 {d:+.2f}%p  95%CI [{lo:+.2f}, {hi:+.2f}]  p={p:.3f}")
