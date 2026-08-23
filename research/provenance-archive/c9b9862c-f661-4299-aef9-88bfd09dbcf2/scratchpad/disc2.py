# -*- coding: utf-8 -*-
import os, pickle, sys, random
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disc import cellfx, cell_dk, cell_d, ROWS, RIDS, KOR
random.seed(11)

def sub(rows, f): return [r for r in rows if f(r)]

X26 = lambda x: 1 if (x["v_heavy_volume_pullback"] and x["v_breakout_failure"]) else 0

print("=" * 100)
print("[4] ②+⑥ 조합 강건성 점검 (유일한 명목상 유의 항목)")
print("=" * 100)
for yk in ("rem", "fwd5", "fwd10", "fwd20"):
    r = cellfx(ROWS, X26, yk, cell_dk)
    print(f"  성과={yk:<6} 점등{r['n1']:>5} 셀내차 {r['eff']:+7.2f}%p  p={r['p']:.4f}"
          f" | 나이브 점등평균 {r['m1']:+6.2f} vs 미점등 {r['m0']:+6.2f}")
print("  ─ 셀 정의 바꿔보기 (성과=rem)")
for nm, cf in [("날짜만", cell_d), ("날짜+보유일차", cell_dk),
               ("진입일+보유일차", lambda r: (r["entry_date"], r["k"]))]:
    r = cellfx(ROWS, X26, "rem", cf)
    print(f"    셀={nm:<12} 셀내차 {r['eff']:+7.2f}%p p={r['p']:.4f} (셀 {r['n_cell']}, 관측 {r['n_used']})")
print("  ─ 전후반 분할 (2026-03-25, 성과=rem)")
for nm, f in [("전반(~03-24)", lambda r: r["date"] < "2026-03-25"),
              ("후반(03-25~)", lambda r: r["date"] >= "2026-03-25")]:
    rr = cellfx(sub(ROWS, f), X26, "rem", cell_dk)
    print(f"    {nm}: 점등{rr['n1']:>5} 셀내차 {rr['eff']:+7.2f}%p p={rr['p']:.4f}"
          f" | 나이브 {rr['m1']:+6.2f} vs {rr['m0']:+6.2f}")
print("  ─ 보유일차 구간별 (성과=rem)")
for lo, hi in [(1, 4), (5, 9), (10, 20)]:
    rr = cellfx(sub(ROWS, lambda r, lo=lo, hi=hi: lo <= r["k"] <= hi), X26, "rem", cell_dk)
    if rr:
        print(f"    k={lo}~{hi}: 점등{rr['n1']:>5} 셀내차 {rr['eff']:+7.2f}%p p={rr['p']:.4f}")

print()
print("=" * 100)
print("[5] 전후반 분할 — 개별 5규칙·위반개수 (성과=rem, 셀=날짜+보유일차)")
print("=" * 100)
print(f"{'항목':<20}{'전반 셀내차':>12}{'p':>8}{'후반 셀내차':>12}{'p':>8}{'부호일치':>9}")
items = [("위반개수(기울기)", lambda r: min(r["cnt"], 3))] + \
        [(KOR[rid], (lambda k: (lambda x: 1 if x["v_" + k] else 0))(rid)) for rid in RIDS] + \
        [("②+⑥", X26)]
for nm, f in items:
    a = cellfx(sub(ROWS, lambda r: r["date"] < "2026-03-25"), f, "rem", cell_dk, nperm=2000)
    b = cellfx(sub(ROWS, lambda r: r["date"] >= "2026-03-25"), f, "rem", cell_dk, nperm=2000)
    same = "O" if a and b and a["eff"] * b["eff"] > 0 else "X"
    print(f"{nm:<20}{a['eff']:>12.2f}{a['p']:>8.3f}{b['eff']:>12.2f}{b['p']:>8.3f}{same:>9}")
