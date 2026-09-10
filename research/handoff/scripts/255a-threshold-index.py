# -*- coding: utf-8 -*-
r"""255a - **문턱 k=1..5 「«첫» 절단일」 색인 ＋ «절단률» 곡선**  (조사 세션 2026-09-09)

  🚨 **왜 «새» 코드인가** — `253` 의 검출기는 **「다섯 중 «하나»라도」(k=1)의 «첫» 날**만 냈다.
     **k ≥ 2 는 «날마다» 다섯의 «상태»를 «다시» 세야** 한다 — **㉤·㉥ 이 «되돌아오»기** 때문이다
     (㉤ `sell_rules.py:190` «마지막» 시점 누계 · ㉥ `:236` 피벗 «복귀» ⇒ pass).
     ⇒ ⛔ **「각 규칙 «첫» 위반일의 k번째」는 «틀린» 자**다.

  🚨 **그리고 `253` 을 «믿게» 한 관문(빠른 검출기 vs 진짜)은 «k=1 하나»만 덮는다**
     ⇒ ✅ **k=2..5 를 «세 해»(2007·2008·2021)에서 «먼저» 맞댄다**(두뇌 지시)

  ⛔ **k★ 는 «코드»가 «고른다** — **절단률 ≥ %s 의 «제일 높은» k**(⛔ 결과 «보기» 전에 «박음**)

실행(대조): PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python .../255a-threshold-index.py --verify 2008
실행(곡선): PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python .../255a-threshold-index.py
"""
from __future__ import annotations

import gc
import io
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "scripts"))

from canslim_lib import sell_rules as SR                       # noqa: E402

WARM = Path("D:/stock-data/uspath-warm2")
OUTF = HERE.parent / "results" / "255-kdays.json"
YEARS = tuple(range(1999, 2027))
VERIFY_YEARS = (2007, 2008, 2021)     # `253` 조건 ② 와 «같은» 셋
CUT_MIN = 0.10                        # ⛔ **k★ 문턱 — 결과 «보기» 전에 박음**
RULES5 = ("heavy_volume_pullback", "consecutive_lower_lows", "close_below_ma",
          "weak_days_dominant", "breakout_failure")
__doc__ = __doc__ % ("10%",)


def rolling_avgv(v, window=50, min_days=5):
    """`SR.avg_volume` 와 «같은» 것을 «한» 번에.

    ⚠️🚨 **«확인된» 결함 — 이 함수를 «다시» «쓰는» 판은 «먼저» 이 줄을 «읽었다»고 «적어라**
       **`>=` «경계»에서 «진짜» 함수와 «갈린다**(누적합 차 vs 직접 합산의 «마지막» 비트).
       거래량이 거의 «상수»인 계열에서 **평균이 «정확»히 그 값과 «같아져» 경계 «등호»**가 된다.
       실측 **2 / 151,999**(`253c`) · 상대오차 9.637e-16.
       ⛔ **「2/152k」를 «다른» 판으로 «옮기지» 말 것**(유형 68).
       ✅ **읽었다** — `255a` 는 **«같은» 결함을 «안고» 간다**(고치면 `253` 과 «달라진다»).
    """
    n = len(v)
    ps, pc = [0.0] * (n + 1), [0] * (n + 1)
    for i, x in enumerate(v):
        ok = 1 if x else 0
        ps[i + 1] = ps[i] + (x if ok else 0.0)
        pc[i + 1] = pc[i] + ok
    out = [None] * n
    for i in range(n):
        lo = max(0, i - window)
        cnt = pc[i] - pc[lo]
        if cnt >= min_days:
            out[i] = (ps[i] - ps[lo]) / cnt
    return out


def kdays(c, h, l, v, av, si, n, pivot):
    """**날마다** 다섯의 «상태»를 세어 — **k=1..5 의 «첫» 절단일**(자리)을 낸다."""
    # ── 되돌아오지 «않는» 셋: «첫» 날만 있으면 «이후» 계속 참 ──
    f2 = f3 = f4 = None
    qrun = 0
    for i in range(si + 1, n):
        if f2 is None and av[i] is not None and c[i] < c[i - 1] and v[i] \
                and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
            f2 = i
        is_ll = l[i] < l[i - 1]
        qrun = qrun + 1 if (is_ll and av[i] is not None and v[i] is not None
                            and v[i] >= av[i]) else 0
        if f3 is None and qrun >= SR.LOWER_LOW_RUN:
            f3 = i
        if f4 is None and i + 1 >= 20:
            if c[i] < sum(c[i - 19:i + 1]) / 20:
                f4 = i
            elif i + 1 >= 50 and c[i] < sum(c[i - 49:i + 1]) / 50 and av[i] and v[i] \
                    and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
                f4 = i
        if f2 is not None and f3 is not None and f4 is not None:
            break
    # ── «날마다» 세기 ──
    out = {k: None for k in range(1, 6)}
    dn = up = bad = good = 0
    volbreak = False
    bv = v[si]
    if c[si] < pivot and bv and v[si] and v[si] > bv:
        volbreak = True
    for j in range(si + 1, n):
        # ㉤ 하락일·나쁜 마감 (되돌아옴)
        if c[j] < c[j - 1]:
            dn += 1
        elif c[j] > c[j - 1]:
            up += 1
        if h[j] > l[j]:
            mid = (h[j] + l[j]) / 2
            if c[j] < mid:
                bad += 1
            elif c[j] > mid:
                good += 1
        w5 = ((j - si) >= SR.MIN_TREND_DAYS) and (dn > up or bad > good)
        # ㉥ 돌파 실패 (되돌아옴)
        if c[j] < pivot and bv and v[j] and v[j] > bv:
            volbreak = True
        w6 = volbreak or (c[j] < pivot and (j - si) > SR.SQUAT_GRACE_DAYS)
        cnt = ((f2 is not None and j >= f2) + (f3 is not None and j >= f3)
               + (f4 is not None and j >= f4) + w5 + w6)
        for k in range(1, 6):
            if out[k] is None and cnt >= k:
                out[k] = j
        if out[5] is not None:
            break
    return out


def real_count(d, c, h, l, v, si, pivot, upto):
    m = upto + 1
    t = {"dates": d[:m], "closes": c[:m], "highs": h[:m], "lows": l[:m], "volumes": v[:m]}
    st = [
        SR.rule_heavy_volume_pullback(t, si)["status"],
        SR.rule_consecutive_lower_lows(t, si)["status"],
        SR.rule_close_below_ma(t, si)["status"],
        SR.rule_weak_days_dominant(t, si)["status"],
        SR.rule_breakout_failure(t, si, pivot, breakout_confirmed=True, start=si)["status"],
    ]
    return sum(1 for x in st if x == "violation")


def rows_of(y):
    f = WARM / ("uspath_%d.json" % y)
    if not f.exists():
        return []
    return (json.loads(io.open(f, encoding="utf-8").read()).get("trigger_paths") or [])


def prep(r):
    pn = r.get("pre_n") or 0
    piv = r.get("pivot")
    if not pn or not r.get("v") or not piv:
        return None
    dd, cc = r["pre_d"] + r["d"], r["pre_c"] + r["c"]
    hh, ll = r["pre_h"] + r["h"], r["pre_l"] + r["l"]
    vv = r["pre_v"] + r["v"]
    return dd, cc, hh, ll, vv, pn, piv, len(cc)


def verify(years):
    P("# 255a - **k=2..5 «양성» 대조**(세 해)")
    P("")
    P("```")
    P("   ⛔ **자**: «내» 빠른 검출기의 「k별 «첫» 절단일」 vs **«진짜» `SR.rule_*` 다섯을 «그» 날에 «세어»** 본 값")
    P("      ⇒ 「그 날엔 count ≥ k」 **이고** 「«전»날엔 count < k」 — **«둘» 다** 맞아야 «맞음»")
    P("   ⛔ **`253` 관문은 k=1 «하나»만 덮었다** — **이것이 k=2..5 를 덮는다**")
    P("```")
    P("")
    t0 = time.time()
    ok = {k: [0, 0] for k in range(1, 6)}
    for y in years:
        rows = rows_of(y)
        for r in rows:
            pr = prep(r)
            if pr is None:
                continue
            dd, cc, hh, ll, vv, si, piv, n = pr
            av = rolling_avgv(vv)
            kd = kdays(cc, hh, ll, vv, av, si, n, piv)
            for k in range(1, 6):
                j = kd[k]
                ok[k][1] += 1
                if j is None:
                    # «끝»까지 count < k 여야 한다 — «마지막» 날에서 확인
                    good = real_count(dd, cc, hh, ll, vv, si, piv, n - 1) < k
                else:
                    a = real_count(dd, cc, hh, ll, vv, si, piv, j) >= k
                    b = True if j - 1 <= si else \
                        real_count(dd, cc, hh, ll, vv, si, piv, j - 1) < k
                    good = a and b
                ok[k][0] += 1 if good else 0
        P("  %d 끝 — %.1f분" % (y, (time.time() - t0) / 60.0), flush=True)
        del rows
        gc.collect()
    P("")
    P("| k | 맞음 / 전체 | 일치율 |")
    P("|---|---:|---:|")
    worst = 100.0
    for k in range(1, 6):
        a, b = ok[k]
        pct = 100.0 * a / max(1, b)
        worst = min(worst, pct)
        P("| **%d** | %s / %s | **%.3f%%** |" % (k, format(a, ","), format(b, ","), pct))
    P("")
    P("```")
    P("   **제일 낮은 일치율 %.3f%%** ⇒ %s" % (worst, "✅ **통과**" if worst >= 100.0
                                               else "🔴🔴 **«미통과** — ⛔ **멈춘다**"))
    P("   ⛔ **28해가 «이» 세 해를 «품는다** — **«독립»된 셋이 «아니다**(`253` 때와 «같은» 단서)")
    P("   💰 **실측 %.1f분**" % ((time.time() - t0) / 60.0))
    P("```")
    return worst >= 100.0


def curve():
    P("# 255a - **«절단률» 곡선 (k=1..5 · 전수)**")
    P("")
    t0 = time.time()
    tab, cnt = {}, {k: 0 for k in range(1, 6)}
    tot = 0
    for y in YEARS:
        rows = rows_of(y)
        for r in rows:
            pr = prep(r)
            if pr is None:
                continue
            dd, cc, hh, ll, vv, si, piv, n = pr
            av = rolling_avgv(vv)
            kd = kdays(cc, hh, ll, vv, av, si, n, piv)
            tot += 1
            key = "%s|%s" % (r["code"], r["entry_date"])
            tab[key] = {str(k): (dd[kd[k]] if kd[k] is not None else None)
                        for k in range(1, 6)}
            for k in range(1, 6):
                if kd[k] is not None:
                    cnt[k] += 1
        P("  %d 끝 — 누적 %s (%.1f분)" % (y, format(tot, ","), (time.time() - t0) / 60.0),
          flush=True)
        del rows
        gc.collect()
    P("")
    P("| k | «걸린» 거래 | «절단률» | k★ 후보(≥ %.0f%%) |" % (CUT_MIN * 100))
    P("|---|---:|---:|:--|")
    kstar = None
    for k in range(1, 6):
        rate = cnt[k] / max(1, tot)
        if rate >= CUT_MIN:
            kstar = k
        P("| **%d** | %s | **%.2f%%** | %s |"
          % (k, format(cnt[k], ","), 100.0 * rate,
             "✅" if rate >= CUT_MIN else "⛔ **«미만»**"))
    P("")
    P("```")
    P("   ⛔ **k★ 는 «코드»가 «골랐다** — `CUT_MIN = %.2f` 는 **결과 «보기» 전에 박은 값**"
      % CUT_MIN)
    P("   ⇒ **k★ = %s**" % ("**%d**" % kstar if kstar else "🔴 **«없다** — 어느 k 도 문턱 «미만»"))
    P("   거래 **%s**" % format(tot, ","))
    P("   💰 **실측 %.1f분**" % ((time.time() - t0) / 60.0))
    P("```")
    OUTF.write_text(json.dumps({"table": tab, "count": cnt, "total": tot,
                                "cut_min": CUT_MIN, "kstar": kstar}), encoding="utf-8")
    P("")
    P("✅ 저장 `255-kdays.json` (%.1f MB)" % (OUTF.stat().st_size / 1e6))
    return 0


def main():
    if "--verify" in sys.argv:
        i = sys.argv.index("--verify")
        ys = (int(sys.argv[i + 1]),) if len(sys.argv) > i + 1 \
            and sys.argv[i + 1].isdigit() else VERIFY_YEARS
        return 0 if verify(ys) else 3
    return curve()


if __name__ == "__main__":
    raise SystemExit(main())
