# -*- coding: utf-8 -*-
"""119 — **문턱을 «제대로» 걸고 다시 잰다: 동전 40판 · 백분위** (사전등록 · 값 보기 «전»)

118 에서 매수 수를 맞췄고 2002~2017 이득이 «남는» 걸 봤다.
**그런데 내가 건 문턱이 잘못됐다** — 「동전 8판 중 «가장 운 좋은» 판을 이겨라」였고,
그건 «엄한» 게 아니라 **통계적으로 이상하다**(진짜에게 8배 불리 · p 바닥 1/9 = 0.11).

# 이 판이 고치는 것 — **문턱만 고친다. 가설은 그대로다**
```
동전    8판  →  **40판**  (p 바닥 1/41 = **0.024** < 0.05)
문턱    「최선을 이겨라」  →  **「동전 분포의 95백분위를 넘어라」**
자      진짜·동전 «둘 다» 운의 번호 **40판**으로 맞춘다 (118 은 100 vs 100 이었으나
        40판씩이면 동전 수를 늘릴 수 있고, «같은 자»로 재는 게 더 중요하다)
매수 수  118 과 «같은 방식»으로 이분 탐색해 맞춘다 (관문 1% 안)
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **H**★ | **네 구간 모두** 진짜 연평균이 동전 40판의 **95백분위**를 넘는다 |
| **I**★ | **네 구간 모두** 진짜 낙폭이 동전 40판의 **95백분위**보다 얕다 |
| **J** | 진짜가 동전 분포의 «몇 백분위»인지 네 구간 전부 적는다 |
| **K** | 🚨 관문 — 매수 수가 «실제로» 맞았는가 (1% 안) |

**H★ 하나만 넘어도 「수익 이득이 진짜」**다. I★ 까지 넘으면 「낙폭도」다.
🚨 **「네 구간 모두」를 그대로 둔다** — 118 에서 닷컴·2018~2026 이 걸렸고, 그게 «진짜 벽»인지 본다.

# ★ 방향을 «먼저» 적는다
```
㉮ **2002~2017 은 넘을 것이다** — 118 에서 동전 «최선»도 넘었다(+8.73 vs +5.13)
㉯ **전체 27.4년도 넘을 가능성이 높다** (+10.95 vs +8.92)
㉰ 🚨 **닷컴은 못 넘을 것이다** — 2.75년뿐이고 동전 «최선»이 +26.96% 로 튀었다
㉱ 🚨 **2018~2026 도 못 넘을 것이다** — 여덟 번 같은 자리였다
→ **그래서 H★(네 구간 모두)는 «미통과»로 예상한다. 그런데 «어느 구간이 왜»가 이 판의 소득이다**
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
_x = _u.spec_from_file_location("r118", HERE / "118-matched-placebo.py")
r118 = _u.module_from_spec(_x)
_x.loader.exec_module(r118)
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
N_FAKE, N_SEED = 40, 40
SHORT_SIZE, BORROW = 0.20, 2.0


def main() -> int:
    quick = "--quick" in sys.argv
    n_fake, n_seed = (4, 8) if quick else (N_FAKE, N_SEED)
    print("=" * 104, flush=True)
    print("119 — **문턱을 제대로: 동전 %d판 · 95백분위** · 사전등록 · 운의번호 %d판"
          % (n_fake, n_seed), flush=True)
    print("=" * 104, flush=True)
    print("🚨 118 의 문턱(「8판 중 최선을 이겨라」)이 «잘못 엄했다». **문턱만 고친다**", flush=True)
    print("🚨 방향 먼저: 2002~2017·전체는 넘고 **닷컴·2018~2026 은 못 넘을 것**\n", flush=True)

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
    n_real, ev_real = r118.fills_of(by_f)
    print("① 진짜 매수 %s\n" % "{:,}".format(n_real), flush=True)

    print("관문 K — 동전 %d판의 «매수 수»를 맞춘다 …" % n_fake, flush=True)
    fakes, gaps = [], []
    for j in range(n_fake):
        r_, n_ = r118.find_rate(by2, n_real, 41000 + j)
        fakes.append(r118.random_by(by2, r_, 41000 + j))
        gaps.append(abs(n_ - n_real) / n_real * 100)
        if (j + 1) % max(1, n_fake // 4) == 0:
            print("   %2d/%d … (어긋남 최대 %.2f%%)" % (j + 1, n_fake, max(gaps)), flush=True)
    ok = max(gaps) < 1.0
    print("   → 최대 어긋남 **%.2f%%** · **%s**\n"
          % (max(gaps), "통과" if ok else "🚨 미통과 — 무효"), flush=True)
    if not ok:
        return 3

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    rnd = random.Random(51515)
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
        _n, ev = r118.fills_of(by)
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
            out[lab] = ((st.median(eq) ** (1 / yrs) - 1) * 100, st.median(md))
        return out

    print("진짜 · 동전 %d판을 돌린다 …" % n_fake, flush=True)
    R = measure(by_f, on)
    F = []
    for j in range(n_fake):
        F.append(measure(fakes[j], fake_on[j]))
        if (j + 1) % max(1, n_fake // 4) == 0:
            print("   %2d/%d …" % (j + 1, n_fake), flush=True)

    print("\n  %-12s %10s %10s %10s %10s %9s"
          % ("구간", "진짜", "동전 중앙", "동전 95%", "백분위", "판정"), flush=True)
    print("  " + "-" * 70, flush=True)
    res, H, I = {}, True, True
    for lab, a0, b0, yrs in WIN:
        fe = sorted(F[j][lab][0] for j in range(n_fake))
        p95 = fe[int(n_fake * 0.95)] if n_fake > 1 else fe[-1]
        rank = 100.0 * sum(1 for v in fe if v < R[lab][0]) / n_fake
        okH = R[lab][0] > p95
        H = H and okH
        fm = sorted(F[j][lab][1] for j in range(n_fake))
        m95 = fm[int(n_fake * 0.95)]
        okI = R[lab][1] > m95        # 낙폭은 «덜 음수»가 좋다
        I = I and okI
        res[lab] = {"real": R[lab][0], "fake_med": st.median(fe), "p95": p95,
                    "rank": rank, "okH": okH, "real_mdd": R[lab][1],
                    "mdd_p95": m95, "okI": okI}
        print("  %-12s %+9.2f%% %+9.2f%% %+9.2f%% %8.1f%% %s"
              % (lab, R[lab][0], st.median(fe), p95, rank,
                 ("✅" if okH else "❌") + ("✅" if okI else "❌")), flush=True)
    print("  (판정 두 글자 = 수익 · 낙폭)", flush=True)

    print("\n" + "=" * 104, flush=True)
    print("  **H★** 네 구간 모두 «수익»이 동전 95백분위를 넘는가 → **%s**"
          % ("통과" if H else "미통과"), flush=True)
    print("  **I★** 네 구간 모두 «낙폭»이 동전 95백분위보다 얕은가 → **%s**"
          % ("통과" if I else "미통과"), flush=True)
    print("\n  ★ 넘은 구간 — 수익: %s"
          % (", ".join(l for l in res if res[l]["okH"]) or "없음"), flush=True)
    print("            낙폭: %s"
          % (", ".join(l for l in res if res[l]["okI"]) or "없음"), flush=True)
    (r91.OUT / "119-percentile-test.json").write_text(
        json.dumps({"res": res, "H": H, "I": I, "n_fake": n_fake, "n_seed": n_seed,
                    "n_real": n_real, "gap_max": max(gaps)},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 119-percentile-test.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
