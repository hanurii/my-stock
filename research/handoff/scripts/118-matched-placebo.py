# -*- coding: utf-8 -*-
"""118 — **①+③ 에 «매수 수를 맞춘» 동전 짝을 붙인다** (사전등록 · 값 보기 «전»)

117 에서 ①+③(성장 둔화 필터 + 지수 숏)이 27.4년 전체로 SPY 를 «수익·낙폭 둘 다» 이겼다.
**그런데 동전 짝이 «없었다».** 그리고 107 이 밝힌 문제가 여기 걸린다:

```
🚨 107 의 발견 — **후보 수를 맞춰도 «매수 수»가 안 맞는다**
   같은 종목이 겹치면 하나로 지우는데,
   진짜 조건은 잘 나가는 종목에 «몰려» 많이 겹치고 무작위는 흩어져 «덜 겹친다»
   → 103 의 동전이 진짜보다 **21~149% 더 샀다** → M★ 통과가 흔들렸다
```

# ★ 이 판의 해법 — **«매수 수»를 맞출 때까지 비율을 찾아 들어간다**
```
진짜 ① 이 남긴 «매수 수»를 목표로 두고,
무작위 제거 비율을 **이분 탐색**해서 매수 수가 맞는 지점을 찾는다
🚨 관문: 맞춘 뒤 매수 수 차이가 **1% 안**이어야 한다. 아니면 이 판은 무효다
```

# 팔
```
진짜   ① 성장 둔화 필터 + ③ 200일선 숏 20%
동전   «매수 수를 맞춘» 무작위 필터 + «같은 날 수»의 무작위 숏   × **8판**
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **E**★ | **네 구간 모두** 수익이 동전보다 나은 판 > 55% (동전 8판 «전부»에 대해) |
| **F**★ | **네 구간 모두** 낙폭도 동전보다 나은 판 > 55% |
| **G** | 🚨 관문 — 매수 수가 «실제로» 맞았는가 (1% 안) |

**E★·F★ 를 둘 다** 넘어야 「①+③ 이 «진짜»다」.

# ★ 방향을 «먼저» 적는다
```
㉮ **매수 수를 맞추면 동전이 «세진다»** — 103 에서 동전이 21% 더 사서 «약했던» 것과 반대다
㉯ 🚨 **그래서 E★ 는 못 넘을 수도 있다.** 117 의 «이겼다»가 매수 수 차이였을 수 있다
㉰ 낙폭(F★)은 넘을 가능성이 더 높다 — ③ 이 구조적으로 낙폭을 줄인다
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
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_t)
_t.loader.exec_module(r102)
_v = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_v)
_v.loader.exec_module(r103)
_w = _u.spec_from_file_location("r108", HERE / "108-short-index.py")
r108 = _u.module_from_spec(_w)
_w.loader.exec_module(r108)
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
N_FAKE = 8
SHORT_SIZE, BORROW = 0.20, 2.0
A_PASS = 55.0


def fills_of(by):
    ev, _x, _y = r91.replay(by)
    return len(ev), ev


def random_by(by0, rate, seed):
    rnd = random.Random(seed)
    out = {}
    for y in sorted(by0):
        out[y] = [p for p in by0[y] if rnd.random() < rate]
    return out


def find_rate(by0, target, seed, lo=0.30, hi=1.0, tol=0.004):
    """🚨 «매수 수»가 target 이 되는 무작위 비율을 이분 탐색한다."""
    for _ in range(18):
        mid = (lo + hi) / 2
        n, _e = fills_of(random_by(by0, mid, seed))
        if abs(n - target) / target < tol:
            return mid, n
        if n < target:
            lo = mid
        else:
            hi = mid
    n, _e = fills_of(random_by(by0, (lo + hi) / 2, seed))
    return (lo + hi) / 2, n


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 100
    n_fake = 3 if "--quick" in sys.argv else N_FAKE
    print("=" * 108, flush=True)
    print("118 — **①+③ 에 «매수 수를 맞춘» 동전 짝** · 사전등록 · 동전 %d판 · 운의번호 %d판"
          % (n_fake, n_seed), flush=True)
    print("=" * 108, flush=True)
    print("🚨 방향 먼저: **매수 수를 맞추면 동전이 «세진다»** → **E★ 를 못 넘을 수도 있다**\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    by_f = {}
    for y in sorted(by2):
        keep = []
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep.append(p)
        by_f[y] = keep
    n_real, ev_real = fills_of(by_f)
    n_base, _e = fills_of(by2)
    print("바탕 매수 %s · ① 진짜 매수 **%s**"
          % ("{:,}".format(n_base), "{:,}".format(n_real)), flush=True)

    # ── 🚨 관문 G — 매수 수를 «맞춘다» ───────────────────────────────
    print("\n관문 G — «매수 수»를 맞출 때까지 비율을 찾아 들어간다", flush=True)
    fakes, gaps = [], []
    for j in range(n_fake):
        r_, n_ = find_rate(by2, n_real, 7000 + j)
        fakes.append((random_by(by2, r_, 7000 + j), r_, n_))
        gaps.append(abs(n_ - n_real) / n_real * 100)
        print("   동전 %d — 비율 %.4f · 매수 %s (어긋남 %.2f%%)"
              % (j + 1, r_, "{:,}".format(n_), gaps[-1]), flush=True)
    ok = max(gaps) < 1.0
    print("   → 최대 어긋남 **%.2f%%** · **%s**"
          % (max(gaps), "통과" if ok else "🚨 미통과 — 이 판은 무효다"), flush=True)
    if not ok:
        return 3

    # ── ③ 숏 준비 ───────────────────────────────────────────────────
    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    rnd = random.Random(31337)
    fake_on = []
    for j in range(n_fake):
        m = {}
        for lab, a0, b0, _y in WIN[1:]:
            dd = [d for d in ds if a0 <= d <= b0]
            k = sum(1 for d in dd if on.get(d))
            pick = set(rnd.sample(dd, k))
            for d in dd:
                m[d] = d in pick
        fake_on.append(m)

    def measure(by, omap):
        _n, ev = fills_of(by)
        out = {}
        for lab, a0, b0, yrs in WIN:
            e = [t for t in ev if a0 <= t["entry_date"] <= b0]
            rs = r91.sim(e, n_seed)
            eq, md = [], []
            for x in rs:
                o = r108.overlay(x["curve"], x["equity_pct"], None, spy_ret, omap,
                                 SHORT_SIZE, BORROW, a0, b0)
                if o:
                    eq.append(o[0])
                    md.append(o[1] * 100)
            out[lab] = {"eq": eq, "md": md}
        return out

    print("\n진짜 · 동전 %d판을 돌린다 …" % n_fake, flush=True)
    R = measure(by_f, on)
    F = [measure(fakes[j][0], fake_on[j]) for j in range(n_fake)]

    print("\n  %-12s %s" % ("구간", "[진짜 연평균 · 동전 중앙] · 수익 이긴판 · 낙폭 이긴판"),
          flush=True)
    print("  " + "-" * 88, flush=True)
    res = {}
    for lab, a0, b0, yrs in WIN:
        re_ = st.median(R[lab]["eq"])
        cg = (re_ ** (1 / yrs) - 1) * 100
        fes = [st.median(F[j][lab]["eq"]) for j in range(n_fake)]
        fcg = [(v ** (1 / yrs) - 1) * 100 for v in fes]
        # 🚨 동전 «판마다» 짝비교 이긴 비율 → 그 최솟값을 쓴다(가장 엄한 동전)
        we = min(100.0 * sum(1 for x, y in zip(R[lab]["eq"], F[j][lab]["eq"]) if x > y) / n_seed
                 for j in range(n_fake))
        wm = min(100.0 * sum(1 for x, y in zip(R[lab]["md"], F[j][lab]["md"]) if x > y) / n_seed
                 for j in range(n_fake))
        res[lab] = {"cagr": cg, "fake_cagr_med": st.median(fcg),
                    "fake_cagr_max": max(fcg), "win_eq": we, "win_md": wm,
                    "mdd": st.median(R[lab]["md"])}
        print("  %-12s %+7.2f%% vs 동전 %+7.2f%% (최선 %+7.2f%%) · %5.1f%%%s · %5.1f%%%s"
              % (lab, cg, st.median(fcg), max(fcg), we, "✅" if we > A_PASS else "❌",
                 wm, "✅" if wm > A_PASS else "❌"), flush=True)

    print("\n" + "=" * 108, flush=True)
    E = all(res[l]["win_eq"] > A_PASS for l in res)
    Fq = all(res[l]["win_md"] > A_PASS for l in res)
    print("  **E★** 네 구간 모두 수익이 «가장 엄한 동전»보다 나은 판 > 55%% → **%s**"
          % ("통과" if E else "미통과"), flush=True)
    print("  **F★** 네 구간 모두 낙폭도 나은 판 > 55%% → **%s**"
          % ("통과" if Fq else "미통과"), flush=True)
    print("\n  → **①+③ 이 «진짜»인가: %s**" % ("예" if (E and Fq) else "**아니오**"), flush=True)
    (r91.OUT / "118-matched-placebo.json").write_text(
        json.dumps({"res": res, "n_real": n_real, "gaps": gaps, "E": E, "F": Fq},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 118-matched-placebo.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
