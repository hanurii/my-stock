# -*- coding: utf-8 -*-
r"""253a - **매도 규칙 「첫 위반일」 «작은» 표 «떨구기**  (조사 세션 2026-09-09)

  🚨 **까닭** — `253` 이 **MemoryError** 로 죽었다. warm2 는 **4.6 GB**(최대 해 **237 MB**)라
     **«통째»로 «못** 올린다. ⇒ **두뇌 ㉠** : **해마다 «읽고» «버리고» — «작은» 표«만** 남긴다.
     ★ **`242` 선례**(`flag` 하나로 줄임)와 «같은» 얼개다.

  산출 `253-violate.json` = **{"코드|진입일": 「첫 위반일」}**  ＋ 양성 대조 «셈**

실행(측정): PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python .../253a-violation-index.py --year 2007
실행(전체): PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python .../253a-violation-index.py
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
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import sell_rules as SR                       # noqa: E402

WARM = Path("D:/stock-data/uspath-warm2")
OUTF = HERE.parent / "results" / "253-violate.json"
YEARS = tuple(range(1999, 2027))
STRICT = "--strict" in sys.argv
RULES5 = ("heavy_volume_pullback", "consecutive_lower_lows", "close_below_ma",
          "weak_days_dominant", "breakout_failure")


def rss_mb():
    """🔎 `psapi` 가 «0»을 돌려줘 — `tracemalloc`(파이썬 «몫»)으로 «갈음**한다.
       ⛔ **프로세스 «전체»가 «아니다** — **파이썬이 «잡은» 것**만이다."""
    import tracemalloc
    if not tracemalloc.is_tracing():
        tracemalloc.start()
        return 0.0, 0.0
    cur, pk = tracemalloc.get_traced_memory()
    return cur / 1e6, pk / 1e6


def rolling_avgv(v, window=50, min_days=5):
    """`SR.avg_volume` 와 «같은» 것을 «한» 번에 — 판정일 «제외** · 거짓값 «거른다**.

    ⚠️🚨 **«확인된» 결함 — 이 함수를 «다시» «쓰는» 판은 «먼저» 이 줄을 «읽었다»고 «적어라**
       **`>=` «경계»에서 «진짜» 함수(`SR.avg_volume`)와 «갈린다**.
       까닭: 누적합 차(`ps[i]-ps[lo]`)와 직접 합산이 **«마지막» 비트**에서 다르고 —
       거래량이 **거의 «상수»**인 계열(예 `RSLS1`: 0.0 이 78 · 0.01 이 50)에서는
       **평균이 «정확»히 그 값과 «같아져»** `v >= avg` 가 **경계 «등호»**가 된다.
       실측 **2 / 151,999**(`253c-find-two.py` · `results/253c-two.json`) · 상대오차 9.637e-16.
       ⛔ **「2/152k」를 «다른» 판으로 «옮기지» 말 것**(유형 68) —
          **저유동·거래정지 «근처» 종목이 «많은» 표본에선 «그» 수가 «아니다**.
       ✅ **고치려면**: 창을 «직접» 합산(O(n×50)) ⇒ 색인 재빌드 어림 15~25분.
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


def first_violations(c, h, l, v, av, si, n, pivot):
    """다섯 규칙의 **«첫» 위반 자리** — `sell_rules` 논리 «그대로**."""
    out = {}
    r = None
    for i in range(si + 1, n):
        if av[i] is not None and c[i] < c[i - 1] and v[i] and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
            r = i
            break
    out["heavy_volume_pullback"] = r

    r, qrun = None, 0
    for i in range(si + 1, n):
        is_ll = l[i] < l[i - 1]
        qrun = qrun + 1 if (is_ll and av[i] is not None and v[i] is not None
                            and v[i] >= av[i]) else 0
        if qrun >= SR.LOWER_LOW_RUN:
            r = i
            break
    out["consecutive_lower_lows"] = r

    r = None
    for i in range(si + 1, n):
        if i + 1 < 20:
            continue
        if c[i] < sum(c[i - 19:i + 1]) / 20:
            r = i
            break
        if i + 1 >= 50 and c[i] < sum(c[i - 49:i + 1]) / 50 and av[i] and v[i] \
                and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
            r = i
            break
    out["close_below_ma"] = r

    r, dn, up, bad, good = None, 0, 0, 0, 0
    for j in range(si + 1, n):
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
        if (j - si) >= SR.MIN_TREND_DAYS and (dn > up or bad > good):
            r = j
            break
    out["weak_days_dominant"] = r

    r, bv, seen = None, v[si], False
    for j in range(si, n):
        if c[j] < pivot:
            seen = True
            if bv and v[j] and v[j] > bv:
                r = j
                break
        if seen and c[j] < pivot and (j - si) > SR.SQUAT_GRACE_DAYS:
            r = j
            break
    out["breakout_failure"] = r
    return out


def real_status(d, c, h, l, v, si, pivot, upto):
    m = upto + 1
    t = {"dates": d[:m], "closes": c[:m], "highs": h[:m], "lows": l[:m], "volumes": v[:m]}
    return {
        "heavy_volume_pullback": SR.rule_heavy_volume_pullback(t, si)["status"],
        "consecutive_lower_lows": SR.rule_consecutive_lower_lows(t, si)["status"],
        "close_below_ma": SR.rule_close_below_ma(t, si)["status"],
        "weak_days_dominant": SR.rule_weak_days_dominant(t, si)["status"],
        "breakout_failure": SR.rule_breakout_failure(t, si, pivot, breakout_confirmed=True,
                                                     start=si)["status"],
    }


def do_year(y, table, agree, bnd, stat):
    f = WARM / ("uspath_%d.json" % y)
    if not f.exists():
        return 0.0
    t0 = time.time()
    d = json.loads(io.open(f, encoding="utf-8").read())
    rows = d.get("trigger_paths") or []
    for r in rows:
        pn = r.get("pre_n") or 0
        piv = r.get("pivot")
        if not pn or not r.get("v") or not piv:
            stat["skip"] += 1
            continue
        dd = r["pre_d"] + r["d"]
        cc = r["pre_c"] + r["c"]
        hh = r["pre_h"] + r["h"]
        ll = r["pre_l"] + r["l"]
        vv = r["pre_v"] + r["v"]
        n = len(cc)
        av = rolling_avgv(vv)
        fv = first_violations(cc, hh, ll, vv, av, pn, n, piv)
        rs = real_status(dd, cc, hh, ll, vv, pn, piv, n - 1)
        for k in RULES5:
            agree[k][1] += 1
            if ("violation" if fv[k] is not None else "no") == \
               ("violation" if rs[k] == "violation" else "no"):
                agree[k][0] += 1
        js = [x for x in fv.values() if x is not None]
        key = "%s|%s" % (r["code"], r["entry_date"])
        j0 = min(js) if js else None
        if STRICT:
            # ★★ **«날마다»** 진짜 함수를 «부른다** — **«그것»이 «매도» 규칙의 «뜻**이다
            #    (전 구간 «한» 번 비교는 ㉤·㉥ 처럼 «되돌아오는» 규칙엔 «틀린» 자다)
            jr = None
            for j in range(pn + 1, n):
                a = real_status(dd, cc, hh, ll, vv, pn, piv, j)
                if any(a[k] == "violation" for k in RULES5):
                    jr = j
                    break
            bnd[1] += 1
            bnd[0] += 1 if jr == j0 else 0
        elif j0 is not None:
            a1 = real_status(dd, cc, hh, ll, vv, pn, piv, j0)
            on = any(a1[k] == "violation" for k in RULES5)
            off = True
            if j0 - 1 > pn:
                a0 = real_status(dd, cc, hh, ll, vv, pn, piv, j0 - 1)
                off = not any(a0[k] == "violation" for k in RULES5)
            bnd[1] += 1
            bnd[0] += 1 if (on and off) else 0
        if j0 is not None:
            table[key] = dd[j0]
            stat["viol"] += 1
        else:
            table[key] = None
            stat["clean"] += 1
    del d, rows
    gc.collect()
    return time.time() - t0


def main():
    import tracemalloc
    tracemalloc.start()
    one = None
    if "--year" in sys.argv:
        one = int(sys.argv[sys.argv.index("--year") + 1])
    years = (one,) if one else YEARS
    table, stat = {}, {"skip": 0, "viol": 0, "clean": 0}
    agree = {k: [0, 0] for k in RULES5}
    bnd = [0, 0]
    t0 = time.time()
    for y in years:
        el = do_year(y, table, agree, bnd, stat)
        ws, pk = rss_mb()
        P("  %d — 키 %s · %.1f분 · 메모리 %.0f MB(최고 %.0f MB)"
          % (y, format(len(table), ","), el / 60.0, ws, pk), flush=True)
    ws, pk = rss_mb()
    P("")
    P("합 %.1f분 · 키 %s · 위반 %s · 깨끗 %s · 건너뜀 %s · **최고 메모리 %.0f MB**"
      % ((time.time() - t0) / 60.0, format(len(table), ","), format(stat["viol"], ","),
         format(stat["clean"], ","), format(stat["skip"], ","), pk))
    for k in RULES5:
        ok, tot = agree[k]
        P("  일치 %-26s %s / %s = %.3f%%" % (k, format(ok, ","), format(tot, ","),
                                             100.0 * ok / max(1, tot)))
    P("  경계 %s / %s = %.3f%%" % (format(bnd[0], ","), format(bnd[1], ","),
                                   100.0 * bnd[0] / max(1, bnd[1])))
    if one:
        P("")
        P("⛔ **측정만** — 표를 «안» 썼다(`--year` 모드)")
        return 0
    OUTF.write_text(json.dumps({"table": table, "agree": agree, "bnd": bnd, "stat": stat}),
                    encoding="utf-8")
    P("")
    P("✅ 저장 %s (%.1f MB)" % (OUTF.name, OUTF.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
