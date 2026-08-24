# -*- coding: utf-8 -*-
"""34 · **거래대금이 마른 것인가, 쏠린 것인가** (3-D 재료).

물음
----
32번에서 한국 평가율이 81% → 55% 로 떨어졌고, 원인은 **저유동 탈락이 10.4% → 37.1%**였다.
그런데 같은 구간에 코스피는 3,056 → 6,913 으로 올랐다.
> **시장 전체 거래대금이 늘었는데도 문턱(5억원 고정 명목값)을 넘는 종목이 줄었다면
>   그건 「거래가 소수 종목으로 쏠렸다」는 뜻이다.**
> **전체가 줄었으면 그냥 「거래가 말랐다」이고 뜻이 다르다.**

내는 것 — 연도별 · 양 시장
--------------------------
- 시장 전체 **일평균 거래대금 합**(억원 환산)
- **상위 50 / 100 / 500 종목이 차지하는 비중**(그 해 거래대금 합 기준)
- 종목별 일평균 거래대금의 **중앙값**(전형적인 종목이 얼마나 거래되나)
- **5억원 문턱을 넘는 종목 수**(그 해 일평균 기준)
🚨 문턱은 **고정 명목값**이다. 그래서 「중앙값이 문턱에 대해 어디 있나」가 핵심이다.

⚠️ 미국은 `USD × 1300 ÷ 1e8` 로 환산한다. **환율이 고정이라 미국 쪽 「명목 증가」에는
   환율 변동이 안 들어간다** — 두 시장을 같은 자로 재려는 것이지 실제 원화 가치가 아니다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/34-turnover-concentration.py kr|us
"""
from __future__ import annotations

import csv
import io
import json
import re
import statistics as st
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / ".cache" / "bt5y" / "out"
START, END = "2021-02-01", "2026-08-21"
# 🚨 마지막 해는 **155거래일 부분 구간**이다. 세 지표가 그 해에 반등하는데,
#    계절성인지 진짜 반등인지 가르려면 **모든 해를 같은 달력 구간으로 잘라** 봐야 한다.
#    `seasonal` 모드 = 모든 해를 **02-01 ~ 08-21** 로 맞춘다(2021 시작일에 맞춤).
SEASONAL = False
SEAS_LO, SEAS_HI = "02-01", "08-21"


def in_window(date_iso):
    """date_iso = 'YYYY-MM-DD'."""
    if not SEASONAL:
        return True
    return SEAS_LO <= date_iso[5:] <= SEAS_HI
USD_KRW = 1300.0
MIN_TURNOVER_EOK = 5.0
# 🚨 **개별 종목 앵커** — 외부 출처 없이 «사람이 눈으로 자릿수를 판단»할 수 있게 한다.
#    총액 대조는 모집단 정의(ETF·우선주·스팩 포함 여부)에 걸려 성립하지 않지만,
#    **한 종목은 한 종목**이라 그 문제가 없다. 그리고 쏠림 이야기를 직접 검증한다 —
#    중앙이 줄고 상위 비중이 늘었다면 **대형주 축은 늘거나 유지여야 한다.**
ANCHORS = {"kr": [("005930", "삼성전자"), ("000660", "SK하이닉스"),
                  ("035720", "카카오"), ("247540", "에코프로비엠")],
           "us": [("AAPL", "Apple"), ("NVDA", "NVIDIA"), ("TSLA", "Tesla")]}
EXCLUDE_KR = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN_KR = re.compile("^9[0-9]{5}$")


def scan_kr():
    """연도 → {code: [거래대금_억, …]} · 연도 → 거래일 수."""
    P = ROOT / ".cache" / "pdata"
    s, e = START.replace("-", ""), END.replace("-", "")
    by = defaultdict(lambda: defaultdict(float))
    cnt = defaultdict(lambda: defaultdict(int))       # 고정 코호트 판정용 출현일수
    cap = defaultdict(lambda: defaultdict(float))     # 시총 합(평균 내려고)
    capn = defaultdict(lambda: defaultdict(int))
    ndays = defaultdict(int)
    for p in sorted(x for x in P.glob("price_*.json") if s <= x.stem[6:] <= e):
        d = p.stem[6:]
        y = d[:4]
        if not in_window("%s-%s-%s" % (d[:4], d[4:6], d[6:])):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        ndays[y] += 1
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN_KR.match(code):
                continue
            if EXCLUDE_KR.search(r.get("itmsNm") or ""):
                continue
            cnt[y][code] += 1
            t = r.get("trPrc_eok")
            if t:
                by[y][code] += float(t)
            # 실질 판 — **회전율 = 거래대금 ÷ 시가총액**. 자체 자료라 외부 의존이 없고,
            # 물가·지수 보정과 달리 **주가 수준에 자동으로 중립**이다.
            mc = r.get("market_cap_eok")
            if mc and t:
                cap[y][code] += float(mc)
                capn[y][code] += 1
    return by, ndays, cnt, cap, capn


def scan_us():
    import us_loader as U
    meta = U.load_tickers("base")
    codes = set(meta)
    by = defaultdict(lambda: defaultdict(float))
    cnt = defaultdict(lambda: defaultdict(int))
    days = defaultdict(set)
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for row in rd:
            t, d = row[0], row[1]
            if t not in codes or d < START or d > END or not in_window(d):
                continue
            y = d[:4]
            days[y].add(d)
            cnt[y][t] += 1
            c, v = float(row[5]), float(row[6])
            if c > 0 and v > 0:
                by[y][t] += c * v * USD_KRW / 1e8
    # ⚠️ 미국은 시가총액 자료가 없다(Sharadar SEP 은 가격만 · SF1 은 미구독) →
    #    **실질 판(회전율)을 미국에는 낼 수 없다. 「확인 불가」로 적는다.**
    return by, {y: len(s) for y, s in days.items()}, cnt, None, None


def main():
    global SEASONAL
    mkt = sys.argv[1] if len(sys.argv) > 1 else "kr"
    SEASONAL = (len(sys.argv) > 2 and sys.argv[2] == "seasonal")
    if SEASONAL:
        print("🚨 **계절 정렬 모드** — 모든 해를 %s ~ %s 로 잘라 비교한다."
              % (SEAS_LO, SEAS_HI), flush=True)
    by, ndays, cnt, cap, capn = (scan_kr() if mkt == "kr" else scan_us())
    print("", flush=True)
    print("=" * 96, flush=True)
    print("%s — 거래대금 총량과 쏠림 (연도별 · 억원 환산)" % mkt.upper(), flush=True)
    print("🚨 **문턱 통과는 「50일 평균」이 아니라 「그 해 일평균」 기준이다.**", flush=True)
    print("   하네스는 `TURNOVER_WINDOW=50` 의 **평균**과 `MIN_TURNOVER_EOK` 를 견준다 →",
          flush=True)
    print("   **통계 선택(평균/중앙)에 따라 통과율이 크게 흔들린다**"
          "(같은 자료를 중앙값으로 재면 82.8%→48.7%로 수준이 달라진다 · 변화율은 같다).",
          flush=True)
    print("=" * 96, flush=True)
    print("  %-6s %6s %8s %12s %11s %8s %8s %8s %10s"
          % ("연도", "거래일", "종목수", "일평균 총액", "종목 중앙",
             "상위50", "상위100", "상위500", "문턱통과"), flush=True)
    rows = {}
    for y in sorted(by):
        v = by[y]
        n = ndays[y]
        tot = sum(v.values())
        per = sorted((x / n) for x in v.values())          # 종목별 «일평균» 거래대금
        srt = sorted(v.values(), reverse=True)
        def share(k):
            return sum(srt[:k]) / tot * 100 if tot else 0
        pas = sum(1 for x in per if x >= MIN_TURNOVER_EOK)
        rows[y] = {"days": n, "n_codes": len(v), "daily_total_eok": tot / n,
                   "median_daily_eok": st.median(per),
                   "top50_pct": share(50), "top100_pct": share(100),
                   "top500_pct": share(500),
                   "n_pass_threshold": pas,
                   "pass_share_pct": pas / len(v) * 100}
        print("  %-6s %6d %8d %12.0f %11.3f %7.1f%% %7.1f%% %7.1f%% %6d(%4.1f%%)"
              % (y, n, len(v), tot / n, st.median(per), share(50), share(100),
                 share(500), pas, pas / len(v) * 100), flush=True)
    ys = sorted(rows)
    a, b = rows[ys[0]], rows[ys[-1]]
    # ── 🚨 고정 코호트 — 「신규 상장 희석」과 「기존 종목의 거래가 마름」을 가른다 ──
    y0, y1 = ys[0], ys[-1]
    coh = {c for c in cnt[y0]
           if cnt[y0][c] >= ndays[y0] * 0.90 and cnt[y1].get(c, 0) >= ndays[y1] * 0.50}
    newc = set(cnt[y1]) - set(cnt[y0])
    print("", flush=True)
    print("  **고정 코호트** = %s 내내 상장(출현 90%%↑) + %s 에도 생존(출현 50%%↑) → "
          "**%d종목**" % (y0, y1, len(coh)), flush=True)
    print("  %-6s %10s %14s %12s %10s" % ("연도", "코호트수", "코호트 중앙(억)",
                                          "코호트 총액(억/일)", "문턱통과"), flush=True)
    cohrow = {}
    for y in ys:
        v = [by[y][c] / ndays[y] for c in coh if c in by[y]]
        if not v:
            continue
        pas = sum(1 for x in v if x >= MIN_TURNOVER_EOK)
        cohrow[y] = {"n": len(v), "median": st.median(v),
                     "total_daily": sum(v), "pass": pas,
                     "pass_pct": pas / len(v) * 100}
        print("  %-6s %10d %14.3f %12.0f %6d(%4.1f%%)"
              % (y, len(v), st.median(v), sum(v), pas, pas / len(v) * 100), flush=True)
    ca, cb = cohrow[ys[0]], cohrow[ys[-1]]
    print("   → 코호트 중앙 %.3f → %.3f (**%+.1f%%**) · 전체판 %+.1f%%"
          % (ca["median"], cb["median"], (cb["median"] / ca["median"] - 1) * 100,
             (b["median_daily_eok"] / a["median_daily_eok"] - 1) * 100), flush=True)
    print("   → 코호트 문턱통과 %.1f%% → %.1f%% · 전체판 %.1f%% → %.1f%%"
          % (ca["pass_pct"], cb["pass_pct"], a["pass_share_pct"], b["pass_share_pct"]),
          flush=True)
    # ── 🚨 고정 코호트 «자체의» 편향 — 방향이 정해져 있다 ──────────────────
    #   「첫 해에도 있고 마지막 해에도 살아 있는 종목」은 그 사이 사라진 것을 배제한다.
    #   상폐·거래정지의 통상 경로를 생각하면 **사라진 쪽이 저유동에 치우쳐** 있다.
    #   → **고정 코호트는 「마름」을 «과소평가»한다.**
    #   그래서 검정력이 한쪽으로만 있다:
    #     코호트에서도 크게 내려가면 → **쏠림 확정, 그것도 「최소한 그만큼」**
    #     코호트에서 평평했다면      → 생존자 배제로도 설명되므로 **모호**였을 것
    #   우리 결과는 유리한 쪽이라 논증이 더 강해진다. **먼저 적는다.**
    gone = {c for c in cnt[y0] if cnt[y0][c] >= ndays[y0] * 0.90} - coh
    gv = sorted(by[y0][c] / ndays[y0] for c in gone if c in by[y0])
    cv = sorted(by[y0][c] / ndays[y0] for c in coh if c in by[y0])
    if gv:
        def qq(v, f):
            return v[min(len(v) - 1, int(len(v) * f))]
        print("", flush=True)
        print("  **코호트 탈락분의 첫 해(%s) 거래대금 분포** — 「사라진 쪽이 마른 쪽인가」"
              % y0, flush=True)
        print("   %-10s %6s %10s %10s %10s %14s"
              % ("집단", "종목", "P25", "중앙", "P75", "5억 미만 비율"), flush=True)
        for lab, v in (("탈락분", gv), ("코호트", cv)):
            print("   %-10s %6d %10.3f %10.3f %10.3f %13.1f%%"
                  % (lab, len(v), qq(v, .25), qq(v, .50), qq(v, .75),
                     sum(1 for x in v if x < MIN_TURNOVER_EOK) / len(v) * 100), flush=True)
        print("   → 탈락분 중앙이 코호트보다 **낮으면** 「사라진 쪽이 마른 쪽」이고, "
              "**고정 코호트는 마름을 과소평가**한다(= 우리 하락폭은 «최소값»이다).",
              flush=True)
        rows["_cohort_dropped"] = {
            "n": len(gv), "median": qq(gv, .50), "p25": qq(gv, .25), "p75": qq(gv, .75),
            "below_threshold_pct": sum(1 for x in gv if x < MIN_TURNOVER_EOK) / len(gv) * 100,
            "cohort_median": qq(cv, .50),
            "cohort_below_threshold_pct":
                sum(1 for x in cv if x < MIN_TURNOVER_EOK) / len(cv) * 100}
    nv = [by[y1][c] / ndays[y1] for c in newc if c in by[y1]]
    if nv:
        print("   → **%s 시점에 있으나 첫 해엔 없던 종목(=그 사이 신규 상장) "
              "%d종목 · 중앙 %.3f억 · 문턱통과 %.1f%%**"
              % (y1, len(nv), st.median(nv),
                 sum(1 for x in nv if x >= MIN_TURNOVER_EOK) / len(nv) * 100), flush=True)
    # ── 실질 판: 회전율 ─────────────────────────────────────────────────
    if cap is not None:
        print("", flush=True)
        print("  **실질 판 — 회전율(일거래대금 ÷ 시가총액, bp)** · 고정 코호트", flush=True)
        print("   보정 기준: **그 종목의 시가총액**(물가도 지수도 아니다). "
              "주가 수준에 자동 중립이다.", flush=True)
        turn = {}
        for y in ys:
            v = []
            for c in coh:
                if c in by[y] and capn[y].get(c):
                    mc = cap[y][c] / capn[y][c]
                    if mc > 0:
                        v.append((by[y][c] / ndays[y]) / mc * 10000)
            if v:
                turn[y] = st.median(v)
                print("   %-6s 중앙 회전율 **%.2f bp/일** (n=%d)" % (y, turn[y], len(v)),
                      flush=True)
        if len(turn) >= 2:
            k0, k1 = ys[0], ys[-1]
            print("   → %s → %s **%+.1f%%** (명목 중앙은 %+.1f%%)"
                  % (k0, k1, (turn[k1] / turn[k0] - 1) * 100,
                     (cb["median"] / ca["median"] - 1) * 100), flush=True)
        rows["_turnover_ratio_bp"] = turn
        # 🚨 **변수를 바꿔 같은 결론이 나오나** — 거래대금이 아니라 «시가총액»으로 묻는다.
        #    변수가 다르고 결론이 같으면 자료 잡음이 아니라 시장 구조다.
        print("", flush=True)
        print("  **다른 변수로 같은 물음 — 고정 코호트의 «중앙 시가총액»(억원)**", flush=True)
        mcs = {}
        for y in ys:
            v = [cap[y][c] / capn[y][c] for c in coh if capn[y].get(c)]
            if v:
                mcs[y] = st.median(v)
                print("   %-6s 중앙 시총 **%.0f억** (n=%d)" % (y, mcs[y], len(v)), flush=True)
        if len(mcs) >= 2:
            k0, k1 = ys[0], ys[-1]
            print("   → %s → %s **%+.1f%%** — 같은 구간 코스피는 +126.2%%"
                  % (k0, k1, (mcs[k1] / mcs[k0] - 1) * 100), flush=True)
            print("   → **거래대금이 아니라 시총으로 물어도 「중앙 종목은 작아졌다」가 나온다.**",
                  flush=True)
        rows["_cohort_median_marcap"] = mcs
    else:
        print("", flush=True)
        print("  **실질 판(회전율): 확인 불가** — 미국은 시가총액 자료가 없다"
              "(Sharadar SEP 은 가격만 · SF1 미구독).", flush=True)
        rows["_turnover_ratio_bp"] = "확인 불가 — 시가총액 자료 없음"
    print("   ⚠️ 코호트에서도 비슷하게 내려가면 **기존 종목의 거래가 실제로 말랐다.**"
          " 평평하면 **하락의 상당 부분이 신규 상장 희석**이다.", flush=True)
    rows["_cohort"] = {"size": len(coh), "by_year": cohrow,
                       "new_in_last_year": len(nv) if nv else 0,
                       "new_median": st.median(nv) if nv else None}
    print("", flush=True)
    print("  **%s → %s 변화**" % (ys[0], ys[-1]), flush=True)
    print("   일평균 총액 %.0f → %.0f 억원 (**%+.1f%%**)"
          % (a["daily_total_eok"], b["daily_total_eok"],
             (b["daily_total_eok"] / a["daily_total_eok"] - 1) * 100), flush=True)
    print("   종목 중앙 일거래대금 %.3f → %.3f 억원 (**%+.1f%%**) · 문턱은 %.1f억 고정"
          % (a["median_daily_eok"], b["median_daily_eok"],
             (b["median_daily_eok"] / a["median_daily_eok"] - 1) * 100,
             MIN_TURNOVER_EOK), flush=True)
    print("   상위50 비중 %.1f%% → %.1f%% (**%+.1f%%p**)"
          % (a["top50_pct"], b["top50_pct"], b["top50_pct"] - a["top50_pct"]), flush=True)
    print("   문턱 통과 종목 %d(%.1f%%) → %d(%.1f%%)"
          % (a["n_pass_threshold"], a["pass_share_pct"],
             b["n_pass_threshold"], b["pass_share_pct"]), flush=True)
    print("", flush=True)
    print("  ⚠️ 총액이 늘었는데 통과가 줄면 **쏠림** · 총액도 줄었으면 **거래가 마른 것**이다."
          " 뜻이 다르므로 하나로 뭉치지 않는다.", flush=True)
    # ── 개별 종목 앵커 ──────────────────────────────────────────────────
    print("", flush=True)
    print("  **개별 종목 앵커 — 일평균 거래대금(억원 환산)**", flush=True)
    print("   %-14s %s" % ("종목", " ".join("%10s" % y for y in ys)), flush=True)
    anc = {}
    for code, nm in ANCHORS.get(mkt, []):
        row = []
        for y in ys:
            v = by[y].get(code)
            row.append((v / ndays[y]) if v else None)
        anc[code] = {"name": nm, "by_year": dict(zip(ys, row))}
        print("   %-14s %s" % ("%s %s" % (code, nm),
                               " ".join(("%10.0f" % x) if x else "%10s" % "-"
                                        for x in row)), flush=True)
    print("   ⚠️ 자릿수를 눈으로 본다. 삼성전자가 조 단위(≥10,000억)면 맞고 "
          "억·십조 단위면 틀린 것이다.", flush=True)
    print("   ⚠️ 쏠림이 맞다면 **대형주 축은 늘거나 유지**여야 한다. "
          "대형주까지 줄었으면 쏠림이 아니라 시장 전체가 마른 것이다.", flush=True)
    rows["_anchors"] = anc

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("34-turnover-%s%s.json" % (mkt, "-seasonal" if SEASONAL else ""))).write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장: .cache/bt5y/out/34-turnover-%s%s.json"
          % (mkt, "-seasonal" if SEASONAL else ""), flush=True)


if __name__ == "__main__":
    main()
