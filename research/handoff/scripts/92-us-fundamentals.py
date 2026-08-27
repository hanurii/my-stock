# -*- coding: utf-8 -*-
r"""92 — **실적이 진입 결과를 가르는가.** 사전등록 `tasks/92-us-fundamentals.md`.

사용자 지시(2026-08-28): **「적게 시작해서 유의미하면 그때 전체를 돌린다」**

```
--pilot   1단계 — **고르기 창(1999-04~2011-12)만** 본다. 문턱 없음 · 판정 없음.
          🚨 이 창은 «답을 찾는 용도»라 봐도 판정 창을 안 태운다.
          여기서 아무 신호도 없으면 **2단계를 안 한다.**
(기본)    2단계 — 판정 두 창(2012-01~2017-08 · 2017-09~2026-08)에서 «시험»한다.
          🚨 두 창은 «한 번만» 쓴다.
```

규약(90번에서 확인)
  ① 실적은 **공시일(`date`) < 진입일** 인 것만 — `calendardate`/`reportperiod` 로 붙이면 룩어헤드
  ② **ARQ 만** — MRQ/MRT 는 «나중에 수정된» 값이라 미래를 안다
  ③ **신선도 상한 180일** — 넘으면 «좀비»(공시를 멈춘 회사)로 보고 **제외**하고 «세어서» 찍는다
"""
from __future__ import annotations

import bisect
import datetime as _dt
import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402

_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"
FUND = Path(r"D:\stock-data\derived\92-fund-pit.json")

# ── 사전등록 §2 창 ────────────────────────────────────────────────────────
PICK = ("1999-04-01", "2011-12-31")
TEST1 = ("2012-01-01", "2017-08-31")
TEST2 = ("2017-09-01", "2026-08-21")

STALE_MAX = 180        # §7 ①′ 신선도 상한(일) — 값 보기 «전»에 정했다
NQ = 5                 # 5분위
TARGET = 20.0          # ㉮ MFE ≥ +20%
DOUBLE = 100.0         # ㉯ MFE ≥ +100%

# 92a 의 열 차례
FLD = ("date", "reportperiod", "calendardate", "eps", "epsdil", "revenue",
       "netmargin", "grossmargin", "roe", "shareswadil", "de", "ncfo", "opinc")
IX = {f: i for i, f in enumerate(FLD)}

# ── 사전등록 §4 축 여덟 — 나중에 «추가하지 않는다» ────────────────────────
AXES = ("eps_yoy", "rev_yoy", "eps_accel", "code33",
        "rev_accel", "margin_exp", "roe", "dilution")
CAT = ("code33",)      # 범주형


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def _nan(v):
    return v is None or (isinstance(v, float) and v != v)


NAN = float("nan")


# ═════════════════════════════════════════════════════════════════════════
# 1. 실적을 «공시일 기준»으로 붙인다
# ═════════════════════════════════════════════════════════════════════════
def _yoy(cur, prev):
    """전년 동기 대비. 🚨 분모가 0 이하면 «성장률»이 뜻을 잃는다 → NaN 으로 두고 «센다»."""
    if _nan(cur) or _nan(prev) or prev is None or prev <= 0:
        return NAN
    return cur / prev - 1.0


def feats_at(rows, j):
    """`rows[j]` 가 진입 직전 공시일 때의 축 여덟."""
    def g(k, f):
        return rows[k][IX[f]] if 0 <= k < len(rows) else None

    e0, e4, e5 = g(j, "eps"), g(j - 4, "eps"), g(j - 5, "eps")
    r0, r4, r5 = g(j, "revenue"), g(j - 4, "revenue"), g(j - 5, "revenue")
    e1, r1 = g(j - 1, "eps"), g(j - 1, "revenue")
    eps_yoy = _yoy(e0, e4)
    rev_yoy = _yoy(r0, r4)
    eps_yoy_p = _yoy(e1, e5)
    rev_yoy_p = _yoy(r1, r5)
    m0, m4 = g(j, "netmargin"), g(j - 4, "netmargin")
    s0, s4 = g(j, "shareswadil"), g(j - 4, "shareswadil")

    # ④ code33 — EPS·매출 «둘 다» +30% 인 분기가 2연속인가 (미너비니가 이름 붙인 조건)
    def hit(a, b):
        return (not _nan(a)) and (not _nan(b)) and a >= 0.30 and b >= 0.30
    c33 = "예" if (hit(eps_yoy, rev_yoy) and hit(eps_yoy_p, rev_yoy_p)) else "아니오"

    return {
        "eps_yoy": eps_yoy,
        "rev_yoy": rev_yoy,
        "eps_accel": (eps_yoy - eps_yoy_p) if not (_nan(eps_yoy) or _nan(eps_yoy_p)) else NAN,
        "code33": c33,
        "rev_accel": (rev_yoy - rev_yoy_p) if not (_nan(rev_yoy) or _nan(rev_yoy_p)) else NAN,
        "margin_exp": (m0 - m4) if not (_nan(m0) or _nan(m4)) else NAN,
        # ⑦ roe 는 여기서 안 채운다 — ARQ 에 값이 «0.0%» 다(Sharadar 는 분기 ROE 를 안 낸다).
        #    ART(최근 4분기 합산)에서 따로 붙인다. 사전등록이 「ARQ/ART 만」이라 «범위 안»이고,
        #    🚨 **결과가 나빠서가 아니라 «빈 칸»을 보고** 고쳤다. 그대로 적는다.
        "roe": NAN,
        "dilution": _yoy(s0, s4) if not _nan(s4) else NAN,
    }


def asof_idx(rows, day):
    """공시일 < 진입일 인 것 중 «가장 늦은» 것의 자리. 🚨 `<=` 아님(장중·장후 공시)."""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < day:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


# ═════════════════════════════════════════════════════════════════════════
# 2. 진입 하나 = (축 여덟, 결과 둘)
# ═════════════════════════════════════════════════════════════════════════
def build(years, d0, d1, fund):
    """사다리 «0»(선별 없이) 으로 만든다 — 사전등록 §3 에서 값 보기 «전»에 고정."""
    by0 = {}
    for y in years:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        by0[y] = [p for p in ps if d0 <= p["entry_date"] <= d1]

    rows, miss = [], Counter()
    for y in sorted(by0):
        open_until = {}
        for p in by0[y]:
            c = p["code"]
            # 🚨 91·74 와 «같은» 중복 제거 — 안 하면 같은 종목이 여러 번 센다
            if c in open_until and p["entry_date"] <= open_until[c]:
                miss["같은 종목 겹침"] += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                                 target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]

            epx = p.get("entry_price") or p.get("entry_px")
            hs = p.get("h") or []
            if not epx or not hs:
                miss["시세 없음"] += 1
                continue
            mfe = (max(hs) / epx - 1.0) * 100.0

            rec = fund.get(c)
            if not rec:
                miss["실적표에 종목 없음"] += 1
                continue
            arq = rec["ARQ"]
            j = asof_idx(arq, p["entry_date"])
            if j < 0:
                miss["진입 전 공시 없음"] += 1
                continue
            lag = _ord(p["entry_date"]) - _ord(arq[j][0])
            if lag > STALE_MAX:
                miss["공시가 %d일 넘게 묵음(좀비)" % STALE_MAX] += 1
                continue
            if j < 5:
                miss["과거 분기 부족(<5)"] += 1
                continue
            f8 = feats_at(arq, j)
            # ⑦ roe — ART 에서 «같은 규약»(공시일 < 진입일)으로 붙인다
            art = rec.get("ART") or []
            k = asof_idx(art, p["entry_date"]) if art else -1
            if k >= 0 and _ord(p["entry_date"]) - _ord(art[k][0]) <= STALE_MAX:
                v = art[k][IX["roe"]]
                f8["roe"] = NAN if _nan(v) else v
            f8["_lag"] = lag
            rows.append((f8, 1.0 if mfe >= TARGET else 0.0,
                         1.0 if mfe >= DOUBLE else 0.0, mfe))
    return rows, miss, sum(len(v) for v in by0.values())


# ═════════════════════════════════════════════════════════════════════════
# 3. 5분위 훑기 — **1단계는 여기까지. 문턱 없음**
# ═════════════════════════════════════════════════════════════════════════
def sweep(rows, axis, yi, name):
    ys = [r[yi] for r in rows]
    base = st.mean(ys)
    if axis in CAT:
        vals = sorted({r[0][axis] for r in rows})
        grp = {v: [r[yi] for r in rows if r[0][axis] == v] for v in vals}
        grp = {v: g for v, g in grp.items() if len(g) >= 30}
        if len(grp) < 2:
            return None
        cells = [(v, st.mean(g), len(g)) for v, g in sorted(grp.items())]
    else:
        xs = sorted(r[0][axis] for r in rows if not _nan(r[0][axis]))
        if len(xs) < NQ * 30:
            return None
        cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
        qi = {i: [] for i in range(NQ)}
        for r in rows:
            v = r[0][axis]
            if _nan(v):
                continue
            qi[bisect.bisect_right(cuts, v)].append(r[yi])
        qi = {i: g for i, g in qi.items() if len(g) >= 30}
        if len(qi) < 2:
            return None
        cells = [("%d분위" % (i + 1), st.mean(g), len(g)) for i, g in sorted(qi.items())]
    n_nan = sum(1 for r in rows if _nan(r[0][axis])) if axis not in CAT else 0
    hi = max(cells, key=lambda c: c[1])
    lo = min(cells, key=lambda c: c[1])
    return {"cells": cells, "base": base, "hi": hi, "lo": lo,
            "spread": (hi[1] - lo[1]) * 100, "lift": (hi[1] - base) * 100,
            "n_nan": n_nan}


def main() -> int:
    pilot = "--pilot" in sys.argv
    print("=" * 100, flush=True)
    print("92 — 실적이 진입 결과를 가르는가 · **%s**"
          % ("1단계 «고르기 창만» (문턱 없음 · 판정 없음)" if pilot else "2단계 판정"), flush=True)
    print("=" * 100, flush=True)
    if not pilot:
        print("🚨 2단계는 판정 창을 «한 번만» 쓴다. 1단계 결과 없이 돌리지 않는다.", flush=True)
        return 2

    print("실적표 적재 …", flush=True)
    fund = json.loads(FUND.read_text(encoding="utf-8"))["by"]
    print("   종목 %d개" % len(fund), flush=True)

    d0, d1 = PICK
    years = tuple(range(1999, 2013))
    rows, miss, n_path = build(years, d0, d1, fund)
    print("\n고르기 창 %s ~ %s" % (d0, d1), flush=True)
    print("   경로 %s → **쓸 수 있는 진입 %s**" % ("{:,}".format(n_path), "{:,}".format(len(rows))),
          flush=True)
    for k, v in miss.most_common():
        print("     제외 %-28s %s" % (k, "{:,}".format(v)), flush=True)
    if not rows:
        print("🚨 쓸 수 있는 진입이 0 — 멈춘다", flush=True)
        return 2
    lags = sorted(r[0]["_lag"] for r in rows)
    print("   공시 후 며칠 만에 샀나 — 중앙 %d일 · P90 %d일 · 최대 %d일"
          % (lags[len(lags) // 2], lags[int(len(lags) * .9)], lags[-1]), flush=True)

    for yi, nm in ((1, "㉮ MFE ≥ +20%% 도달"), (2, "㉯ MFE ≥ +100%% (더블)")):
        base = st.mean(r[yi] for r in rows) * 100
        print("\n" + "─" * 100, flush=True)
        print("### %s   —   전체 기준율 **%.2f%%**  (n=%s)"
              % (nm, base, "{:,}".format(len(rows))), flush=True)
        print("  %-12s %-40s %9s %9s %8s"
              % ("축", "분위별 도달률", "최고", "최저", "**폭**"), flush=True)
        print("  " + "-" * 96, flush=True)
        out = []
        for ax in AXES:
            r = sweep(rows, ax, yi, nm)
            if r is None:
                print("  %-12s (셀이 모자라 못 잰다)" % ax, flush=True)
                continue
            cs = " ".join("%.1f" % (c[1] * 100) for c in r["cells"])
            print("  %-12s %-40s %6s %5.1f%% %6s %5.1f%% %+7.2f%%p"
                  % (ax, cs, r["hi"][0], r["hi"][1] * 100,
                     r["lo"][0], r["lo"][1] * 100, r["spread"]), flush=True)
            out.append((ax, r))
        out.sort(key=lambda x: -x[1]["spread"])
        print("\n  폭이 큰 순: %s"
              % " · ".join("**%s %+.2f%%p**" % (a, r["spread"]) for a, r in out[:4]), flush=True)
        print("  결측(NaN) 건수: %s"
              % " · ".join("%s %s" % (a, "{:,}".format(r["n_nan"])) for a, r in out), flush=True)

    print("\n" + "=" * 100, flush=True)
    print("🚨 **1단계는 여기까지다.** 문턱을 안 걸었고 판정 창을 «안» 썼다.", flush=True)
    print("   여기 보이는 폭은 «고르기 창 안»의 것이고, 우연으로도 이만큼 나올 수 있다.", flush=True)
    print("   **2단계로 갈지는 사용자가 정한다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
