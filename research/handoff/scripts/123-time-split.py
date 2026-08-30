# -*- coding: utf-8 -*-
"""123 — **㉡ 앞에서 «고르고» 뒤에서 «검정한다»** (사전등록 · 값 보기 «전»)

사용자(2026-08-29): 「새 자료를 얻기 어렵습니다. **기존 자료를 가지고만** 분석해 볼 순 없겠습니까?
                  가장 큰 한계를 어떻게 해소할 수 있을지 고민해 줄래요?」

★ 가장 큰 한계는 **「우리가 «답을 본 뒤에» 칸을 골랐다」**는 것이다.
   120 이 「동전에게도 «고르기»를 줬을 때」로 한 번 막았지만, 그건 «같은 자료 안»이었다.
   **새 자료 없이 표본 밖을 만드는 «유일한» 길이 시간 분할이다.**

# 재는 법
```
앞 구간 (고르는 곳)   1999-04-01 ~ 2011-12-31   (12.75년)
뒤 구간 (검정하는 곳)  2012-01-01 ~ 2026-08-21   (14.64년)

① 앞 구간에서 **24칸**(12칸 × 지수숏 있음/없음)을 훑어 «연평균 최선»을 **기계적으로** 고른다
   🚨 뒤 구간은 **쳐다보지 않는다**
② 뒤 구간에서 **그 칸 하나만** 재고, «매수 수를 맞춘» 동전 40판과 견준다
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **V**★ | 뒤 구간에서 고른 칸이 동전 40판의 **95백분위**를 넘는다 |
| **W**★ | 뒤 구간에서 고른 칸이 **SPY 그냥 보유**를 이긴다 |
| **X** | 앞에서 고른 칸이 뒤 구간의 «실제 최선»과 **같은가** (다르면 「고르기가 안 옮겨간다」) |
| **Y** | 🚨 관문 — 동전 매수 수가 실제로 맞았는가 (2% 안) |

# ★ 방향을 «먼저» 적는다
```
㉮ 🚨 **V★ 는 못 넘을 것으로 본다.**
   119 에서 2018~2026 이 «여덟 번» 같은 자리였고, 뒤 구간의 절반이 바로 거기다
㉯ 🚨 **앞에서 고른 칸이 뒤의 «실제 최선»과 «다를» 것으로 본다** (X 미통과 예상)
   그러면 「칸 고르기는 시간에 안 옮겨간다」가 되고, 그건 **나쁜 소식이지만 «값어치 있는» 소식**이다
㉰ W★ 는 간당간당하다 — 뒤 구간은 지수가 아주 셌던 구간이다
→ **이 판은 «떨어질 것을 알면서» 거는 판이다. 그래서 «걸 값어치»가 있다**
```
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


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r109 = _load("r109", "109-index-stop.py")
r118 = _load("r118", "118-matched-placebo.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FRONT = ("앞 1999~2011", "1999-04-01", "2011-12-31", 12.75)
BACK = ("뒤 2012~2026", "2012-01-01", "2026-08-21", 14.64)
GRID = [(q, n, u, s) for q in (1, 2, 3) for n in (2, 3)
        for u in ("안삼", "그냥삼") for s in (True, False)]
N_FAKE, N_SEED = 40, 40
SHORT_SIZE, BORROW = 0.20, 2.0


def main() -> int:
    quick = "--quick" in sys.argv
    n_fake, n_seed = (4, 8) if quick else (N_FAKE, N_SEED)
    print("=" * 104, flush=True)
    print("123 — **㉡ 앞에서 고르고 뒤에서 검정한다** · 사전등록 · 동전 %d판" % n_fake, flush=True)
    print("=" * 104, flush=True)
    print("★ 가장 큰 한계 = 「**답을 본 뒤에** 칸을 골랐다」. 새 자료 없이 막는 «유일한» 길", flush=True)
    print("🚨 방향 먼저: **V★ 못 넘을 것** · **앞에서 고른 칸 ≠ 뒤의 최선일 것**\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

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
        return {y: [p for p in by2[y]
                    if (lambda v: v is True or (v is None and u == "그냥삼"))(ver[id(p)][(q, n)])]
                for y in sorted(by2)}

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}

    def cagr(by, omap, sz, win, seeds):
        _lab, a0, b0, yrs = win
        _n, ev = r118.fills_of(by)
        e = [t for t in ev if a0 <= t["entry_date"] <= b0]
        if len(e) < 20:
            return None, len(e)
        rs = r91.sim(e, seeds)
        eq = []
        for x in rs:
            o = r108.overlay(x["curve"], x["equity_pct"], None, spy_ret, omap,
                             sz, BORROW if sz else 0.0, a0, b0)
            if o:
                eq.append(o[0])
        if not eq:
            return None, len(e)
        return ((st.median(eq) ** (1 / yrs) - 1) * 100), len(e)

    # ── ① 앞 구간에서 «기계적으로» 고른다 ────────────────────────────
    print("① 앞 구간 %s ~ %s 에서 **24칸**을 훑는다 (뒤는 «안 본다»)"
          % (FRONT[1], FRONT[2]), flush=True)
    cache, front = {}, []
    for k, (q, n, u, s) in enumerate(GRID):
        by = cache.setdefault((q, n, u), build(q, n, u))
        cg, nf = cagr(by, on if s else {}, SHORT_SIZE if s else 0.0, FRONT, n_seed)
        front.append(((q, n, u, s), cg, nf))
        if (k + 1) % 6 == 0:
            print("   %2d/24 …" % (k + 1), flush=True)
    ok = [x for x in front if x[1] is not None]
    ok.sort(key=lambda x: -x[1])
    print("\n   앞 구간 상위 3칸:", flush=True)
    for cell, cg, nf in ok[:3]:
        print("     %d분기·%d조건·%s·숏%s  %+7.2f%%  (매수 %d)"
              % (cell[0], cell[1], cell[2], "O" if cell[3] else "X", cg, nf), flush=True)
    pick = ok[0][0]
    print("\n   → **고른 칸: %d분기·%d조건·%s·숏%s** (앞 구간 %+.2f%%)"
          % (pick[0], pick[1], pick[2], "O" if pick[3] else "X", ok[0][1]), flush=True)

    # ── ② 뒤 구간에서 «그 칸만» 검정 ─────────────────────────────────
    print("\n② 뒤 구간 %s ~ %s 에서 **그 칸만** 잰다" % (BACK[1], BACK[2]), flush=True)
    q, n, u, s = pick
    by_p = cache[(q, n, u)]
    omap = on if s else {}
    sz = SHORT_SIZE if s else 0.0
    _nc, ev_p = r118.fills_of(by_p)
    n_back = len([t for t in ev_p if BACK[1] <= t["entry_date"] <= BACK[2]])
    real_cg, _ = cagr(by_p, omap, sz, BACK, n_seed)
    print("   진짜 뒤 구간 연평균 **%+.2f%%** (매수 %s)"
          % (real_cg, "{:,}".format(n_back)), flush=True)

    def find_rate(target, seed, lo=0.0005, hi=1.0, tol=0.02, it=26):
        for _ in range(it):
            mid = (lo + hi) / 2
            bb = r118.random_by(by2, mid, seed)
            _x, e = r118.fills_of(bb)
            nn = len([t for t in e if BACK[1] <= t["entry_date"] <= BACK[2]])
            if target > 0 and abs(nn - target) / target < tol:
                return mid, nn
            if nn < target:
                lo = mid
            else:
                hi = mid
        m = (lo + hi) / 2
        _x, e = r118.fills_of(r118.random_by(by2, m, seed))
        return m, len([t for t in e if BACK[1] <= t["entry_date"] <= BACK[2]])

    print("\n   관문 Y — 동전 %d판의 «뒤 구간 매수 수»를 맞춘다 …" % n_fake, flush=True)
    rnd = random.Random(77777)
    dd = [d for d in ds if BACK[1] <= d <= BACK[2]]
    k_on = sum(1 for d in dd if on.get(d))
    fakes, gaps = [], []
    for j in range(n_fake):
        r_, nn = find_rate(n_back, 61000 + j)
        fo = {}
        if s:
            pk = set(rnd.sample(dd, k_on))
            for d in dd:
                fo[d] = d in pk
        fakes.append((r118.random_by(by2, r_, 61000 + j), fo))
        gaps.append(abs(nn - n_back) / max(1, n_back) * 100)
        if (j + 1) % max(1, n_fake // 4) == 0:
            print("      %2d/%d … (어긋남 최대 %.2f%%)" % (j + 1, n_fake, max(gaps)), flush=True)
    gate = max(gaps) < 2.0
    print("      → 최대 어긋남 **%.2f%%** · **%s**"
          % (max(gaps), "통과" if gate else "🚨 미통과 — 무효"), flush=True)
    if not gate:
        return 3

    print("\n   동전 %d판을 뒤 구간에서 돌린다 …" % n_fake, flush=True)
    fc = []
    for j, (bb, fo) in enumerate(fakes):
        v, _ = cagr(bb, fo, sz, BACK, n_seed)
        if v is not None:
            fc.append(v)
        if (j + 1) % max(1, n_fake // 4) == 0:
            print("      %2d/%d …" % (j + 1, n_fake), flush=True)
    fc.sort()
    p95 = fc[int(len(fc) * 0.95)] if len(fc) > 1 else fc[-1]
    rank = 100.0 * sum(1 for v in fc if v < real_cg) / len(fc)
    V = real_cg > p95

    # ── X — 뒤 구간의 «실제 최선»은 어느 칸인가 ──────────────────────
    print("\n③ **X** — 뒤 구간의 «실제 최선»을 (사후에) 찾아 견준다", flush=True)
    back_all = []
    for (q2, n2, u2, s2) in GRID:
        by = cache.setdefault((q2, n2, u2), build(q2, n2, u2))
        v, nf = cagr(by, on if s2 else {}, SHORT_SIZE if s2 else 0.0, BACK, n_seed)
        if v is not None:
            back_all.append(((q2, n2, u2, s2), v))
    back_all.sort(key=lambda x: -x[1])
    best_back = back_all[0]
    same = best_back[0] == pick
    my_rank = 1 + [x[0] for x in back_all].index(pick)
    print("   뒤 구간 실제 최선: %d분기·%d조건·%s·숏%s  %+.2f%%"
          % (best_back[0][0], best_back[0][1], best_back[0][2],
             "O" if best_back[0][3] else "X", best_back[1]), flush=True)
    print("   **앞에서 고른 칸은 뒤 구간에서 %d위 / %d칸**" % (my_rank, len(back_all)), flush=True)

    dsS, cS = r109.load("SPY")
    kk = [i for i, d in enumerate(dsS) if BACK[1] <= d <= BACK[2]]
    spy_cg = ((cS[kk[-1]] / cS[kk[0]]) ** (1 / BACK[3]) - 1) * 100
    W = real_cg > spy_cg

    print("\n" + "=" * 104, flush=True)
    print("  **V★** 뒤 구간에서 동전 95백분위를 넘는가 → **%s**" % ("통과" if V else "미통과"),
          flush=True)
    print("        진짜 %+.2f%% · 동전 중앙 %+.2f%% · 동전 95%% %+.2f%% · **백분위 %.1f%%**"
          % (real_cg, st.median(fc), p95, rank), flush=True)
    print("  **W★** 뒤 구간에서 SPY 그냥 보유를 이기는가 → **%s** (%+.2f%% vs %+.2f%%)"
          % ("통과" if W else "미통과", real_cg, spy_cg), flush=True)
    print("  **X**  앞에서 고른 칸 = 뒤의 실제 최선인가 → **%s** (뒤 구간 %d위/%d)"
          % ("같다" if same else "**다르다**", my_rank, len(back_all)), flush=True)
    print("\n  → **㉡ 시간 분할 판정: %s**"
          % ("**통과 — 표본 밖에서도 산다**" if (V and W) else "**미통과**"), flush=True)
    (r91.OUT / "123-time-split.json").write_text(
        json.dumps({"pick": list(pick), "front": ok[0][1], "back_real": real_cg,
                    "fake_med": st.median(fc), "p95": p95, "rank": rank,
                    "V": V, "W": W, "same": same, "my_rank": my_rank,
                    "spy": spy_cg, "n_back": n_back,
                    "back_all": [[list(k), v] for k, v in back_all]},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 123-time-split.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
