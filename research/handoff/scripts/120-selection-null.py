# -*- coding: utf-8 -*-
"""120 — **「고르는 것까지」 동전에도 시킨다** (㉠) **+ 격자 «전체»가 이기는가** (㉢)
사전등록 · 값 보기 «전»

# 🚨 겨냥하는 한계 (119 §3)
```
「고른 칸이 동전을 이긴다」는 확인됐다.
**그런데 「그 칸을 고른 것」 자체가 12칸 훑기였다.**
지금 비교는 «우리가 고른 칸» vs «동전 한 판»이라 **동전에게 «고르기»가 없다**
```

# ㉠ 해법 — **동전에게도 «12칸 훑고 최선 고르기»를 시킨다**
```
진짜   12칸을 훑어 «최선»을 고른다
동전   **12칸짜리 동전 격자**를 만들고 그중 «최선»을 고른다  ← 20세트
→ 「12칸 훑어서 최선을 골랐을 때 우연히 나오는 크기」의 «분포»가 나온다
→ 진짜의 최선이 그 분포의 95백분위를 넘으면 **선택 오염이 «흡수»된다**
```

# ㉢ 같은 계산으로 덤 — **12칸 «전부»가 각자의 동전을 이기는가**
```
대다수가 이기면 → 「고른 칸」이 아니라 **«축 자체»가 값을 한다**
한 칸만 이기면  → 「고른 것」이다
```

# 매수 수 맞추기 — 118·119 와 «같은» 방식
```
칸마다 이분 탐색으로 «그 칸의» 매수 수에 맞는 무작위 비율을 찾고,
20세트는 그 비율에 «다른 씨앗»만 준다 (탐색을 240번 하지 않기 위해)
🚨 관문: 매수 수 어긋남 1% 안
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **L**★ | 진짜 격자의 «최선»이 **동전 20세트의 «최선» 분포**의 95백분위를 넘는다 (㉠) |
| **M**★ | 12칸 중 **과반(7칸 이상)**이 각자의 동전을 이긴다 (㉢) |
| **N** | 12칸 전부 + 백분위를 적는다 |
| **O** | 🚨 관문 — 매수 수가 맞았는가 |

**L★ 을 넘으면 「고른 것」이 더 이상 흠이 아니다.**
**M★ 을 넘으면 「칸이 아니라 축」이다.** 둘은 «다른 것»이고 둘 다 값어치가 있다.

# ★ 방향을 «먼저» 적는다
```
㉮ 🚨 **L★ 는 «간당간당»할 것으로 본다** — 동전에게 12번 고를 기회를 주면 세진다.
   103 에서 동전 격자 최대가 +83.43%p 였다(그때는 매수 수가 안 맞았지만)
㉯ **M★ 는 넘을 것으로 본다** — 103 에서 「자료 없으면 그냥 삼」 6칸이 전부 좋았다
㉰ 창은 **전체 27.4년 · 2002~2017** 둘만 본다 (닷컴은 2.75년이라 동전 분산이 크고,
   2018~2026 은 이미 «못 넘는다»가 확인됐다) — **창을 줄이는 것도 다중비교를 줄인다**
```
🚨 **③(지수 숏)은 «안» 넣는다.** 선택은 ① 에서 일어났으므로 ① 만으로 재는 게 깨끗하다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_t)
_t.loader.exec_module(r102)
_v = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_v)
_v.loader.exec_module(r103)
_x = _u.spec_from_file_location("r118", HERE / "118-matched-placebo.py")
r118 = _u.module_from_spec(_x)
_x.loader.exec_module(r118)
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66))
GRID = [(q, n, u) for q in (1, 2, 3) for n in (2, 3) for u in ("안삼", "그냥삼")]
N_SET, N_SEED = 20, 40


def main() -> int:
    quick = "--quick" in sys.argv
    n_set, n_seed = (3, 8) if quick else (N_SET, N_SEED)
    print("=" * 104, flush=True)
    print("120 — **고르는 것까지 동전에** (㉠) + **격자 전체** (㉢) · 동전 %d세트 × 12칸"
          % n_set, flush=True)
    print("=" * 104, flush=True)
    print("🚨 방향 먼저: **L★ 는 간당간당할 것** · **M★ 는 넘을 것**\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    # ── 후보마다 판정 미리 (6가지) ──────────────────────────────────
    ver = {}
    for y in sorted(by2):
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
                ver[id(p)] = {c: None for c in [(q, n) for q in (1, 2, 3) for n in (2, 3)]}
            else:
                j = arq.index(a)
                ver[id(p)] = {(q, n): r103.judge(arq, j, ix, q, n)
                              for q in (1, 2, 3) for n in (2, 3)}

    def build(q, n, u):
        out = {}
        for y in sorted(by2):
            out[y] = [p for p in by2[y]
                      if (lambda v: v is True or (v is None and u == "그냥삼"))(
                          ver[id(p)][(q, n)])]
        return out

    def cagr_of(by, lab, a0, b0, yrs, seeds):
        _n, ev = r118.fills_of(by)
        e = [t for t in ev if a0 <= t["entry_date"] <= b0]
        if len(e) < 20:
            return None
        rs = r91.sim(e, seeds)
        m = st.median(x["equity_pct"] for x in rs)
        return ((1 + m / 100.0) ** (1 / yrs) - 1) * 100

    # ── 진짜 12칸 + 칸마다 «비율» 찾기 ──────────────────────────────
    # 🚨 118 의 find_rate 는 탐색 범위가 0.30~1.0 이라 «엄한 칸»(매수 46건)을 못 찾는다.
    #    첫 실행에서 관문이 그걸 잡았다(어긋남 10,415%). 범위를 넓힌 판을 여기 둔다.
    def find_rate_wide(target, seed, lo=0.0005, hi=1.0, tol=0.01, it=26):
        for _ in range(it):
            mid = (lo + hi) / 2
            nn, _e = r118.fills_of(r118.random_by(by2, mid, seed))
            if target > 0 and abs(nn - target) / target < tol:
                return mid, nn
            if nn < target:
                lo = mid
            else:
                hi = mid
        m = (lo + hi) / 2
        nn, _e = r118.fills_of(r118.random_by(by2, m, seed))
        return m, nn

    print("관문 O — 칸마다 «매수 수»에 맞는 무작위 비율을 찾는다", flush=True)
    cells, rates, gaps, bad = [], [], [], []
    for (q, n, u) in GRID:
        by = build(q, n, u)
        nf, _e = r118.fills_of(by)
        r_, n_ = find_rate_wide(nf, 60000 + len(cells))
        g = abs(n_ - nf) / max(1, nf) * 100
        nm = "%d분기·%s·%s" % (q, "둘" if n == 2 else "셋", u)
        cells.append({"key": (q, n, u), "by": by, "n": nf, "nm": nm, "gap": g})
        rates.append(r_)
        gaps.append(g)
        if g >= 1.0 or nf < 300:
            bad.append(nm)
        print("   %-24s 매수 %6s · 비율 %.4f · 어긋남 %6.2f%%%s"
              % (nm, "{:,}".format(nf), r_, g,
                 "  🚨 못 맞춤/표본부족" if (g >= 1.0 or nf < 300) else ""), flush=True)
    print("", flush=True)
    print("   🚨 **판정에서 «빼는» 칸: %s**" % (", ".join(bad) if bad else "없음"), flush=True)
    print("      (매수 수를 못 맞추거나 표본이 300건 미만이면 «비교가 성립 안 한다»)", flush=True)
    use = [c for c in cells if c["nm"] not in bad]
    use_r = [rates[i] for i, c in enumerate(cells) if c["nm"] not in bad]
    if len(use) < 4:
        print("   → 쓸 수 있는 칸이 %d 개뿐이다. 멈춘다." % len(use), flush=True)
        return 3
    print("      → **쓸 수 있는 칸 %d / 12**" % len(use), flush=True)
    print("", flush=True)
    cells, rates = use, use_r

    # ── 값 ──────────────────────────────────────────────────────────
    print("  %-22s %8s %11s %11s"
          % ("칸", "매수", "전체", "2002~2017"), flush=True)
    print("  " + "-" * 58, flush=True)
    real = {}
    for c in cells:
        nm = c["nm"]
        v = {}
        for lab, a0, b0, yrs in WIN:
            v[lab] = cagr_of(c["by"], lab, a0, b0, yrs, n_seed)
        real[nm] = v
        print("  %-22s %8s %+10.2f%% %+10.2f%%"
              % (nm, "{:,}".format(c["n"]), v["전체"], v["2002~2017"]), flush=True)

    print("\n동전 %d세트 × 12칸을 돌린다 …" % n_set, flush=True)
    sets = []
    for s in range(n_set):
        row = {}
        for i, c in enumerate(cells):
            byf = r118.random_by(by2, rates[i], 90000 + s * 101 + i)
            row[c["nm"]] = {lab: cagr_of(byf, lab, a0, b0, yrs, n_seed)
                            for lab, a0, b0, yrs in WIN}
        sets.append(row)
        if (s + 1) % max(1, n_set // 4) == 0:
            print("   %2d/%d …" % (s + 1, n_set), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 104, flush=True)
    out = {"real": real, "L": {}, "M": {}}
    for lab, _a, _b, _y in WIN:
        rbest = max(real[c["nm"]][lab] for c in cells)
        rname = max(cells, key=lambda c: real[c["nm"]][lab])["nm"]
        fbest = sorted(max(sets[s][c["nm"]][lab] for c in cells) for s in range(n_set))
        p95 = fbest[int(n_set * 0.95)] if n_set > 1 else fbest[-1]
        rank = 100.0 * sum(1 for v in fbest if v < rbest) / n_set
        okL = rbest > p95
        out["L"][lab] = {"real_best": rbest, "name": rname, "fake_best_med": st.median(fbest),
                         "p95": p95, "rank": rank, "ok": okL}
        print("  **L★ %s** — 진짜 최선 **%+.2f%%** (%s)" % (lab, rbest, rname), flush=True)
        print("        동전 «격자 최선» %d세트 — 중앙 %+.2f%% · 95백분위 %+.2f%% · 최대 %+.2f%%"
              % (n_set, st.median(fbest), p95, fbest[-1]), flush=True)
        print("        → 진짜가 **백분위 %.1f%%**  ·  **%s**\n"
              % (rank, "통과" if okL else "미통과"), flush=True)

    (r91.OUT / "120-selection-null.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")   # 🚨 M★ «전»에 먼저 저장 — 찍기 버그로 자료를 잃지 않게

    print("  **M★** 12칸 중 «몇 칸»이 각자의 동전을 이기는가 (동전 %d세트 «중앙» 기준)" % n_set,
          flush=True)
    for lab, _a, _b, _y in WIN:
        w = []
        for c in cells:
            fv = st.median(sets[s][c["nm"]][lab] for s in range(n_set))
            if real[c["nm"]][lab] > fv:
                w.append(c["nm"])
        out["M"][lab] = {"n_win": len(w), "cells": w, "ok": len(w) > len(cells) / 2}
        print("        %-10s **%d / %d칸**  %s" % (lab, len(w), len(cells),
                                                   "✅" if len(w) > len(cells) / 2 else "❌"), flush=True)

    L = all(out["L"][l]["ok"] for l in out["L"])
    M = all(out["M"][l]["ok"] for l in out["M"])
    print("\n  → **L★ %s · M★ %s**" % ("통과" if L else "미통과", "통과" if M else "미통과"),
          flush=True)
    print("     L★ 통과 = 「고른 것」이 더 이상 흠이 아니다", flush=True)
    print("     M★ 통과 = 「칸」이 아니라 «축»이 값을 한다", flush=True)
    (r91.OUT / "120-selection-null.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 120-selection-null.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
