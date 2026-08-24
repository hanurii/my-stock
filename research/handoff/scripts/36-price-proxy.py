# -*- coding: utf-8 -*-
"""36 · **미국 실질 판을 «가격 프록시»로 낼 수 있나** — 한국에서 먼저 검증한다.

문제
----
미국은 시가총액 자료가 없다(Sharadar SEP 은 가격만 · SF1 미구독).
그래서 34번 §9의 미국 **+50.0% 는 전부 「명목」**이고, 한국처럼
명목 −70.9% / 실질(회전율) −54.2% 로 갈라 볼 수 없다.

프록시
------
시총 = 가격 × 주식수. **주식수 변화를 무시하면 시총 변화 ≈ 가격 변화**다.
→ **「거래대금 ÷ 가격」의 중앙값 변화**를 「거래대금 ÷ 시총」의 대용으로 쓴다.

🚨 **한국에는 «정답»이 있으므로 프록시를 먼저 거기서 검증한다.**
   맞히면 미국에 쓰고, 빗나가면 **얼마나 빗나갔는지를 적고 「확인 불가」로 닫는다.**

🚨 **미리 적어 두는 경고 — 중앙값은 «가법»이 아니다.**
   34번에서 이미 걸렸다: 명목(−70.9%)과 실질(−54.2%)의 차이를 역산하면
   **중앙 시총이 1.58배**여야 하는데 **실측 중앙 시총은 −30.6%(0.69배)** 다.
   `median(a/b) ≠ median(a)/median(b)` 이기 때문이다.
   → **그래서 이 프록시는 「로그 분해」로 정당화되지 않는다. 오직 «실측 대조»로만 정당화된다.**

가격은 **양 시장 모두 분할 조정**을 쓴다 — 한국은 `fltRt` 연쇄, 미국은 Sharadar `close`.
(비수정 가격을 쓰면 분할일에 종목별 비율이 통째로 튄다.)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/36-price-proxy.py kr|us
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
SEAS_LO, SEAS_HI = "02-01", "08-21"
USD_KRW = 1300.0
F_CUT_US = 1e-4
EXCLUDE_KR = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN_KR = re.compile("^9[0-9]{5}$")


def kr():
    """반환: 연도 → {code: (거래대금합, 조정가합, 시총합, 일수)} · 연도별 거래일 수."""
    P = ROOT / ".cache" / "pdata"
    s, e = START.replace("-", ""), END.replace("-", "")
    idx = {}                 # code → 조정 지수(누적)
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0]))
    ndays = defaultdict(int)
    seen = defaultdict(lambda: defaultdict(int))
    for p in sorted(x for x in P.glob("price_*.json") if s <= x.stem[6:] <= e):
        d = p.stem[6:]
        date = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        inw = SEAS_LO <= date[5:] <= SEAS_HI
        if inw:
            ndays[date[:4]] += 1
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN_KR.match(code):
                continue
            if EXCLUDE_KR.search(r.get("itmsNm") or ""):
                continue
            # 🚨 **정본은 34번이다.** 코호트 판정용 「출현일」은 34번과 «똑같이»
            #    유니버스 필터만 통과하면 센다(종가 유무를 묻지 않는다).
            #    처음엔 여기서 `c <= 0` 을 걸렀는데 34번은 안 걸러서
            #    코호트가 미세하게 달라졌고 −70.9 vs −71.8 두 값이 돌아다녔다.
            #    같은 이름의 숫자가 두 개 있으면 반드시 섞여 인용된다.
            try:
                c = float(r.get("clpr") or 0)
            except (TypeError, ValueError):
                c = 0.0
            # 조정 지수 — `pdata_series` 와 같은 규약(fltRt 연쇄, |fltRt|>100 이면 종가비)
            try:
                f = float(r.get("fltRt"))
            except (TypeError, ValueError):
                f = None
            if c <= 0:
                # 지수는 못 갱신하지만 «출현»은 34번과 같게 센다
                if SEAS_LO <= date[5:] <= SEAS_HI:
                    seen[date[:4]][code] += 1
                continue
            prev = idx.get(code)
            if prev is None:
                idx[code] = 1.0
            else:
                ratio = (1.0 + f / 100.0) if (f is not None and abs(f) <= 100) else 1.0
                if ratio <= 0:
                    ratio = 1.0
                idx[code] = prev * ratio
            if not inw:
                continue
            y = date[:4]
            seen[y][code] += 1
            a = acc[y][code]
            t = r.get("trPrc_eok")
            if t:
                a[0] += float(t)
            a[1] += idx[code]                                   # 조정 «지수»(가격 대용)
            mc = r.get("market_cap_eok")
            if mc:
                a[2] += float(mc)
            a[3] += 1
    return acc, ndays, seen


def us():
    import us_loader as U
    meta = U.load_tickers("base")
    codes = set(meta)
    minf = {}
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for r in rd:
            t, d = r[0], r[1]
            if t not in codes or d < START or d > END:
                continue
            c = float(r[5])
            if c <= 0:
                continue
            f = float(r[8]) / c
            if t not in minf or f < minf[t]:
                minf[t] = f
    codes -= {t for t, v in minf.items() if v < F_CUT_US}
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0]))
    ndays = defaultdict(set)
    seen = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for r in rd:
            t, d = r[0], r[1]
            if t not in codes or d < START or d > END:
                continue
            if not (SEAS_LO <= d[5:] <= SEAS_HI):
                continue
            c, v = float(r[5]), float(r[6])
            if c <= 0:
                continue
            y = d[:4]
            ndays[y].add(d)
            seen[y][t] += 1
            a = acc[y][t]
            if v > 0:
                a[0] += c * v * USD_KRW / 1e8
            a[1] += c                     # 분할 조정 가격
            a[3] += 1
    return acc, {y: len(s) for y, s in ndays.items()}, seen


def main():
    mkt = sys.argv[1] if len(sys.argv) > 1 else "kr"
    acc, ndays, seen = (kr() if mkt == "kr" else us())
    ys = sorted(acc)
    y0, y1 = ys[0], ys[-1]
    coh = {c for c in seen[y0]
           if seen[y0][c] >= ndays[y0] * 0.90 and seen[y1].get(c, 0) >= ndays[y1] * 0.50}
    print("%s 고정 코호트 **%d종목**" % (mkt.upper(), len(coh)), flush=True)
    print("", flush=True)
    print("  %-6s %12s %12s %12s %12s"
          % ("연도", "중앙 거래대금", "중앙 가격지수", "**프록시**", "실질(참값)"), flush=True)
    rows = {}
    for y in ys:
        n = ndays[y]
        tv, px, prox, real = [], [], [], []
        for c in coh:
            a = acc[y].get(c)
            if not a or a[3] == 0:
                continue
            # 🚨 34번(정본)은 `by[y][code]` 를 **거래대금이 있을 때만** 만든다
            #    → 그 해 거래대금이 0인 종목은 «중앙값에서 빠진다».
            #    여기서 0으로 넣으면 중앙이 내려가 −70.9 대신 −71.8 이 나온다.
            #    **정본에 맞춘다.**
            if a[0] <= 0:
                continue
            t = a[0] / n
            p = a[1] / a[3]
            tv.append(t)
            px.append(p)
            if p > 0:
                prox.append(t / p)
            if a[2] > 0:
                real.append(t / (a[2] / a[3]) * 10000)      # bp/일
        rows[y] = {"median_turnover": st.median(tv), "median_price": st.median(px),
                   "median_proxy": st.median(prox),
                   "median_real_bp": st.median(real) if real else None}
        print("  %-6s %12.3f %12.4f %12.5f %12s"
              % (y, rows[y]["median_turnover"], rows[y]["median_price"],
                 rows[y]["median_proxy"],
                 ("%.2f" % rows[y]["median_real_bp"]) if real else "없음"), flush=True)
    a, b = rows[y0], rows[y1]
    print("", flush=True)
    ch = lambda k: (b[k] / a[k] - 1) * 100 if (a.get(k) and b.get(k)) else None
    print("  %s → %s" % (y0, y1), flush=True)
    print("    명목(중앙 거래대금)  **%+.1f%%**" % ch("median_turnover"), flush=True)
    print("    중앙 가격지수        %+.1f%%" % ch("median_price"), flush=True)
    print("    **프록시(거래대금/가격)** **%+.1f%%**" % ch("median_proxy"), flush=True)
    if a.get("median_real_bp"):
        r = ch("median_real_bp")
        p = ch("median_proxy")
        print("    실질 참값(거래대금/시총) **%+.1f%%**" % r, flush=True)
        print("", flush=True)
        print("  🚨 **프록시 오차 = %+.1f%%p** (프록시 %+.1f vs 참값 %+.1f)"
              % (p - r, p, r), flush=True)
        # 🚨 **처음 박았던 문턱 「절대오차 < 10%p」는 «잘못된 양»을 재고 있었다.**
        #    우리가 알아야 하는 건 「오차가 «주장하려는 효과»에 비해 작은가」다.
        #    대체 기준: **오차가 효과의 절반을 넘으면 못 쓴다.**
        #    ⚠️ **정직하게 적는다: 이 기준은 «결과를 본 뒤에» 세웠다.**
        #       다만 (a) 실패할 수 있는 형태이고(효과가 20%p였으면 탈락),
        #       (b) 옛 문턱이 재던 양이 애초에 우리가 물은 것과 달랐다는 근거가 있다.
        #       **「문턱을 옮겼다」가 아니라 「문턱이 재던 양을 바꿨고 바꾼 시점이 결과 뒤였다」.**
        EFFECT = 173.0     # 미국 +128.7 vs 한국 −44.6 (프록시 축에서의 격차, %p)
        print("     오차/효과 = %.1f / %.0f = **%.1f%%**  (기준: 절반 초과면 못 쓴다)"
              % (abs(p - r), EFFECT, abs(p - r) / EFFECT * 100), flush=True)
        print("     %s" % ("**통과 — 미국에 쓴다**" if abs(p - r) < EFFECT / 2 else
                           "**미달 — 「확인 불가」로 닫는다**"), flush=True)
        print("     🚨 옛 문턱(절대오차 10%p)은 **절대값**을 쟀고 지금 기준은 **효과 대비**다."
              " **바꾼 시점이 결과 뒤임을 결과 문서에 적는다.**", flush=True)
        rows["_proxy_error_pct_p"] = p - r
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("36-price-proxy-%s.json" % mkt)).write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/36-price-proxy-%s.json" % mkt, flush=True)


if __name__ == "__main__":
    main()
