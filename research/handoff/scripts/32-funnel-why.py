# -*- coding: utf-8 -*-
"""32 · **① 평가율이 왜 그렇게 움직이나** — 탈락 사유 분해 + 연도별 신규 상장 수.

물음
----
한국 평가율은 81% → 55% 로 **단조 하락**하는데 미국은 45% → 85% 로 **단조 상승**한다.
유니버스는 한국이 늘고(2,239→2,548) 미국이 준다(4,636→4,090).

🚨 **예측을 먼저 적는다 (결과 보기 전).**
검증 세션 가설 = 평가율은 「200일 종가·52주 고가를 가질 만큼 **오래 상장돼 있나**」,
즉 **유니버스의 나이**다. 이 가설이 맞으면:
  **「시계열 길이」가 탈락을 «지배»해야 하고, 유동성·거래정지는 부차적이어야 한다.**
  그리고 **신규 상장 수의 파도가 평가율의 거울상**이어야 한다
  (한국 2023~25 따따블 파도 · 미국 2020~21 SPAC·IPO 기록년).
틀리면 그 사실 자체가 결과다.

방법 — 하네스의 `stD` 필터를 **순서 그대로** 재현한다
------------------------------------------------------
`backtest_volatility_pilot_us.py:304~319`
  1. 시계열 없음                       (`full` 에 없음)
  2. `len(closes) < 200` 또는 `dates[-1] != D`   ← **시계열 길이/그날 시세 없음**
  3. `liveness.is_halted` = 최근 5거래일 거래량 전부 0   ← **거래정지**
  4. 50일 평균 거래대금 < 5억원 (표본 25일 미만이면 부적격)  ← **저유동**
  → 남은 것이 `n_eval`

🚨 **순서가 곧 정의다.** 앞 단계에서 걸린 것은 뒤 단계에서 세지 않는다.
   (그래서 「저유동 탈락」은 「길이는 충분한데 유동성이 모자란 것」만 센다.)

메모리: 시계열을 통째로 안 올린다 — 종목마다 **관측 수·최근 5거래량·최근 50거래대금**만
        들고 날짜를 훑는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/32-funnel-why.py kr|us
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / ".cache" / "bt5y" / "out"

START, END = "2021-02-01", "2026-08-21"
MIN_CLOSES = 200
HALT_DAYS = 5
TURN_WIN = 50
MIN_SAMPLE = TURN_WIN // 2
MIN_TURNOVER_EOK = 5.0
USD_KRW = 1300.0
EXCLUDE_KR = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN_KR = re.compile("^9[0-9]{5}$")


def feed_kr():
    """(날짜, {code: (시계열있음, 거래량, 거래대금_억, 유니버스포함)}) 오름차순."""
    P = ROOT / ".cache" / "pdata"
    for p in sorted(P.glob("price_*.json")):
        d = p.stem[6:]
        if d < "20200102":
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        day = {}
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ"):
                continue                      # KONEX·외국주는 유니버스 밖
            nm = r.get("itmsNm") or ""
            in_uni = not EXCLUDE_KR.search(nm)
            has_series = not FOREIGN_KR.match(code)   # pdata_series 가 외국법인을 뺀다
            try:
                c = float(r.get("clpr") or 0)
            except (TypeError, ValueError):
                c = 0
            if c <= 0:
                has_series = False
            v = r.get("trqu") or 0
            t = r.get("trPrc_eok") or 0
            day[code] = (has_series, float(v), float(t), in_uni)
        yield "%s-%s-%s" % (d[:4], d[4:6], d[6:]), day


def feed_us():
    """Sharadar 를 한 번 흘려보내며 날짜별로 모은다(가격 시계열을 안 쌓는다)."""
    import us_loader as U
    meta = U.load_tickers("base")
    codes = set(meta)
    by = defaultdict(dict)
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for row in rd:
            t, d = row[0], row[1]
            if t not in codes or d < "2020-01-02" or d > END:
                continue
            cf, vf = float(row[5]), float(row[6])
            by[d][t] = (cf > 0, vf, cf * vf * USD_KRW / 1e8, True)
    for d in sorted(by):
        yield d, by[d]


def main():
    mkt = sys.argv[1] if len(sys.argv) > 1 else "kr"
    nobs = Counter()
    vols = defaultdict(lambda: deque(maxlen=HALT_DAYS))
    tovs = defaultdict(lambda: deque(maxlen=TURN_WIN))
    first_seen = {}
    per_year = defaultdict(lambda: Counter())
    print("%s — 훑는 중 …" % mkt.upper(), flush=True)
    for date, day in (feed_kr() if mkt == "kr" else feed_us()):
        y = date[:4]
        scan = START <= date <= END
        for c, (has, v, t, in_uni) in day.items():
            if c not in first_seen:
                first_seen[c] = date
            if has:
                nobs[c] += 1
                vols[c].append(v)
                tovs[c].append(t)
        if not scan:
            continue
        cnt = per_year[y]
        for c, (has, v, t, in_uni) in day.items():
            if not in_uni:
                continue
            cnt["유니버스"] += 1
            if not has:
                cnt["①시계열없음"] += 1
                continue
            if nobs[c] < MIN_CLOSES:
                cnt["②시계열짧음"] += 1
                continue
            if len(vols[c]) >= HALT_DAYS and all(x == 0 for x in vols[c]):
                cnt["③거래정지"] += 1
                continue
            if len(tovs[c]) < MIN_SAMPLE or sum(tovs[c]) / len(tovs[c]) < MIN_TURNOVER_EOK:
                cnt["④저유동"] += 1
                continue
            cnt["평가"] += 1
    print("", flush=True)
    print("=" * 88, flush=True)
    print("%s — 평가 탈락 사유 분해 (하네스 필터 «순서 그대로»)" % mkt.upper(), flush=True)
    print("=" * 88, flush=True)
    print("  %-6s %10s %10s %10s %10s %10s %9s"
          % ("연도", "유니버스", "①시계열없음", "②짧음", "③거래정지", "④저유동", "평가율"),
          flush=True)
    rows = {}
    tot = Counter()
    for y in sorted(per_year):
        c = per_year[y]
        tot.update(c)
        u = c["유니버스"] or 1
        rows[y] = {k: c[k] for k in ("유니버스", "①시계열없음", "②시계열짧음",
                                     "③거래정지", "④저유동", "평가")}
        rows[y]["평가율"] = c["평가"] / u * 100
        print("  %-6s %10d %9.1f%% %9.1f%% %9.1f%% %9.1f%% %8.2f%%"
              % (y, c["유니버스"], c["①시계열없음"] / u * 100, c["②시계열짧음"] / u * 100,
                 c["③거래정지"] / u * 100, c["④저유동"] / u * 100, c["평가"] / u * 100),
              flush=True)
    u = tot["유니버스"] or 1
    print("  %-6s %10d %9.1f%% %9.1f%% %9.1f%% %9.1f%% %8.2f%%"
          % ("전체", tot["유니버스"], tot["①시계열없음"] / u * 100,
             tot["②시계열짧음"] / u * 100, tot["③거래정지"] / u * 100,
             tot["④저유동"] / u * 100, tot["평가"] / u * 100), flush=True)
    drop = u - tot["평가"]
    print("", flush=True)
    print("  **탈락분(%d) 안에서의 비중**: ①시계열없음 %.1f%% · ②짧음 %.1f%% · "
          "③거래정지 %.1f%% · ④저유동 %.1f%%"
          % (drop, tot["①시계열없음"] / drop * 100, tot["②시계열짧음"] / drop * 100,
             tot["③거래정지"] / drop * 100, tot["④저유동"] / drop * 100), flush=True)

    ny = Counter(d[:4] for d in first_seen.values())
    print("", flush=True)
    print("  **연도별 첫 등장(≈신규 상장) 종목 수**", flush=True)
    print("   " + " · ".join("%s %d" % (y, ny[y]) for y in sorted(ny)), flush=True)
    print("   ⚠️ 창 첫 해(2020)는 «그때 이미 상장돼 있던 것»이 전부 잡히므로 신규가 아니다.",
          flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("32-funnel-why-%s.json" % mkt)).write_text(json.dumps({
        "market": mkt, "by_year": rows,
        "total": {k: tot[k] for k in tot},
        "drop_share_pct": {k: tot[k] / drop * 100 for k in
                           ("①시계열없음", "②시계열짧음", "③거래정지", "④저유동")},
        "new_listings_by_year": dict(ny),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/32-funnel-why-%s.json" % mkt, flush=True)


if __name__ == "__main__":
    main()
