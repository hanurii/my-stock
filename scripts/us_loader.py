# -*- coding: utf-8 -*-
"""미국(Sharadar) 로더 — `backtest_volatility_pilot.py` 의 pdata 경로와 **같은 자료구조**를 낸다.

🚨 라이선스: 가격 자료는 저장소에 넣지 않는다. `.cache/sharadar/` 는 gitignore 됨.
   이 파일은 코드만이고, 값은 결과 파일에 집계로만 남긴다.

내는 것 (한국 `load_pdata_range` / `build_pdata_series` 와 동일 스키마)
--------------------------------------------------------------------
`load_universe_range(start, end)` → `(universe_by_date, packed_turnover)`
    universe_by_date[date] = {code: {"name","market","cap_eok", "permaticker"}}
    packed_turnover[code]  = ([날짜…], [거래대금_억원상당…])
`build_all_series(start, end, codes)` → {code: {"dates","opens","highs","lows","closes","volumes"}}

★ 🚨 **분할 되돌리기는 철회했다 (M38 · 2026-08-24)**
  옛 사양(25번 3항)은 `closes = closeunadj` 로 **비수정주가**를 썼다. 그런데 한국 경로
  (`canslim_lib/pdata_series.py`)는 `fltRt` 연쇄로 **수정주가**를 만든다 — **정반대 규약**이었다.
  실측: 창(2021-02~2026-08) 안에서 기준가가 바뀐 종목 **1,070 / 5,666 = 18.9%**,
  그중 **가짜 하루 움직임 ≥90%p 가 940종목(16.6%)**, 방향은 **위로 934 · 아래로 136**
  (미국 소형주는 $1 상장유지 때문에 **역분할**이 잦다). 최대 ASTI 2022-01-31 **+306,188%p**.
  비수정 시계열에서는 그것이 52주 신고가·돌파·+20% 목표 도달로 그대로 읽힌다.
  → **Sharadar 컬럼을 그대로 쓴다**: `open/high/low/close` = 분할 조정·배당 미조정
    (= 한국 `fltRt` 규약), `volume` = 분할 조정된 거래량
    (실측 확인: AAPL 2019-12-05 volume 74,645,000 = 실제 18.66M × 4).
  ⚠️ **`closeadj`(배당까지 조정)는 쓰지 않는다** — 한국에 대응물이 없다.
  `closeunadj` 는 이제 **검산(G3′) 전용**이다.

★ 거래대금 (25번 4항 · M37 확정) — **값은 안 바뀐다(항등식)**
    turnover_usd  = close × volume
      ( 옛 식 `closeunadj × (volume/f)` 는 `f = closeunadj/close` 이므로 **정확히 같다** )
    turnover_eok  = turnover_usd × USD_KRW ÷ 1e8       ← 하네스가 그대로 5.0과 비교
      (= usd ÷ (1e8/usd_krw) = usd ÷ 76,923 @1,300원)
  **원 달러 값도 함께 낸다**(`turnover_usd_series`)  — 검산 가능하게.

★ 종목 키
  지시서는 `permaticker` 를 키로 쓰라고 했다. 실측: `tickers` 표 SEP 20,941행의
  **ticker 고유값이 20,941개로 1:1**이고, 재사용은 Sharadar 가 접미 숫자로 갈라 둔다
  (`AAC1`·`AAC2`·`A1` … 2,858개). → **가독성을 위해 `ticker` 를 키로 쓰고
  `permaticker` 를 유니버스 레코드에 함께 싣는다.** 되돌리려면 `CODE_KEY` 한 줄이다.
"""
from __future__ import annotations

import csv
import os
import io
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ★ 2026-08-27 — **전체 이력판으로 갈아탄다** (10년치 → 1997~2026).
#   자료가 C 드라이브에 안 들어가 D 로 옮겼다. 환경변수로 덮어쓸 수 있게 둔다.
#   🚨 파일이 «바뀌면» 옛 결과는 재현이 안 된다. 옛 판을 다시 돌리려면
#      SHARADAR_DIR=.cache/sharadar 로 두고 STOCKS_ZIP 을 stocks-10Y.csv.zip 로 돌린다.
_env = os.environ.get("SHARADAR_DIR")
if _env:
    SHARADAR = Path(_env)
else:
    for _c in (Path(r"D:/stock-data/sharadar"), ROOT / ".cache" / "sharadar"):
        if (_c / "tickers.csv.zip").exists():
            SHARADAR = _c
            break
    else:
        SHARADAR = ROOT / ".cache" / "sharadar"

TICKERS_ZIP = SHARADAR / "tickers.csv.zip"
# 전체 이력판이 있으면 그것을, 없으면 옛 10년판을 쓴다.
STOCKS_ZIP = (SHARADAR / "stocks.csv.zip" if (SHARADAR / "stocks.csv.zip").exists()
              else SHARADAR / "stocks-10Y.csv.zip")

# 이번 결제로 새로 들어온 표들 (없으면 None — 쓰는 쪽에서 확인한다)
def _opt(name):
    p = SHARADAR / (name + ".csv.zip")
    return p if p.exists() else None


FUNDAMENTALS_ZIP = _opt("fundamentals")   # 실적 (dimension=ARQ/ART 만 쓸 것)
DAILY_ZIP = _opt("daily")                 # 일별 시총·PER·PSR
ACTIONS_ZIP = _opt("actions")             # 분할·병합 — 주가 축 검산용
EVENTS_ZIP = _opt("events")               # 실적 발표일
SP500_ZIP = _opt("sp500")                 # 지수 편입 이력
HOLDINGS_TICKER_ZIP = _opt("holdings_ticker")   # 기관 보유

USD_KRW = 1300.0                 # 25번 4항 확정. 민감도 1,100·1,400 은 이 값만 바꿔 돌린다.
CODE_KEY = "ticker"              # "ticker" | "permaticker"

EXCHANGES = {"NASDAQ", "NYSE", "NYSEMKT"}
BASE_CATEGORIES = {"Domestic Common Stock", "Domestic Common Stock Primary Class"}
SEC_CATEGORIES = {"Domestic Common Stock Secondary Class"}
ADR_CATEGORIES = {"ADR Common Stock", "ADR Common Stock Primary Class",
                  "Canadian Common Stock", "Canadian Common Stock Primary Class"}
SPAC_SIC = "6770"

REF = "AAPL"                     # 거래일 달력 기준 (한국의 005930 자리)


def load_tickers(variant: str = "base") -> dict:
    """variant: 'base'(기본판) | 'sec'(+Secondary Class) | 'adr'(+ADR·Canadian).

    반환 {code: {"ticker","permaticker","name","exchange","category","siccode",
                 "firstpricedate","lastpricedate","isdelisted"}}
    """
    cats = set(BASE_CATEGORIES)
    if variant in ("sec", "adr"):
        cats |= SEC_CATEGORIES
    if variant == "adr":
        cats |= ADR_CATEGORIES
    out = {}
    with zipfile.ZipFile(TICKERS_ZIP) as z:
        name = z.namelist()[0]
        for r in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8")):
            if r.get("table") != "SEP":
                continue
            if r["category"] not in cats or r["exchange"] not in EXCHANGES:
                continue
            if r["siccode"] == SPAC_SIC:
                continue
            if not r["firstpricedate"] or not r["lastpricedate"]:
                continue
            out[r[CODE_KEY]] = {
                "ticker": r["ticker"], "permaticker": r["permaticker"],
                "name": r["name"], "exchange": r["exchange"],
                # 하네스가 이벤트 레코드에 그대로 넣는 키(한국 로더와 스키마 맞춤).
                # 🚨 G2가 잡음: 없으면 첫 진입에서 KeyError 로 죽는다.
                "market": r["exchange"], "cap_eok": None,
                "category": r["category"], "siccode": r["siccode"],
                "isdelisted": r["isdelisted"],
                "firstpricedate": r["firstpricedate"],
                "lastpricedate": r["lastpricedate"]}
    return out


def _iter_prices(codes: set, lo: str, hi: str):
    """가격 CSV 를 한 번만 흘려보낸다. (code, date, o,h,l,c,v, closeunadj) 를 낸다.
    ★ 메모리를 아끼려 여기서 아무것도 쌓지 않는다."""
    with zipfile.ZipFile(STOCKS_ZIP) as z:
        name = z.namelist()[0]
        rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8"))
        next(rd)                                  # header
        for row in rd:
            t, d = row[0], row[1]
            if d < lo or d > hi or t not in codes:
                continue
            yield t, d, row[2], row[3], row[4], row[5], row[6], row[8]


def build_all(start: str, end: str, variant: str = "base",
              usd_krw: float = USD_KRW, limit_codes: int | None = None,
              build_universe: bool = True):
    """한 번의 통과로 **시계열 + 거래대금 + 시점 유니버스**를 함께 만든다.

    반환 (universe_by_date, packed_turnover, full_series, meta)
    """
    meta = load_tickers(variant)
    # 창에 걸치는 종목만
    codes = {c for c, m in meta.items()
             if m["firstpricedate"] <= end and m["lastpricedate"] >= start}
    if limit_codes:                               # peak RSS 실측용 샤드
        codes = set(sorted(codes)[:limit_codes])

    ser = {c: {"dates": [], "opens": [], "highs": [], "lows": [],
               "closes": [], "volumes": []} for c in codes}
    tov_d = defaultdict(list)
    tov_v = defaultdict(list)
    tov_usd = defaultdict(list)
    n_rows = n_badfac = 0
    # 1억원 = 1e8원 · $1 = usd_krw 원  →  억원 = USD × usd_krw ÷ 1e8
    # 🚨 G2가 잡은 버그: 예전 식 `usd/(usd_krw*1e8)` 은 1,690,000배 작았고,
    #    지시서의 `usd/130,000,000` 도 1,690배 작았다. AAPL 2023-06-15 검산:
    #    $12,142,360,780 → **157,851억원**(옛 식 0.0934 · 지시서 식 93.4)
    scale = 1e8 / usd_krw

    for t, d, o, h, l, c, v, cu in _iter_prices(codes, start, end):
        cf = float(c)
        if cf <= 0:
            n_badfac += 1
            continue
        vf = float(v)
        s = ser[t]
        s["dates"].append(d)
        # 🚨 M38: 되돌리지 않는다. Sharadar 의 분할 조정 컬럼을 그대로 쓴다
        #    (한국 fltRt 수정주가와 같은 규약). `cu`(=closeunadj)는 G3′ 검산에만 쓴다.
        s["opens"].append(float(o))
        s["highs"].append(float(h))
        s["lows"].append(float(l))
        s["closes"].append(cf)
        s["volumes"].append(vf)
        usd = cf * vf                             # 옛 `cuf × (v/f)` 와 항등
        tov_d[t].append(d)
        tov_v[t].append(usd / scale)              # 억원 상당
        tov_usd[t].append(usd)                    # 원 달러 (검산용)
        n_rows += 1

    # CSV 가 날짜 오름차순이 아니므로 종목별로 정렬한다
    for c, s in ser.items():
        if not s["dates"]:
            continue
        order = sorted(range(len(s["dates"])), key=lambda i: s["dates"][i])
        for k in ("dates", "opens", "highs", "lows", "closes", "volumes"):
            s[k] = [s[k][i] for i in order]
    for c in list(tov_d):
        order = sorted(range(len(tov_d[c])), key=lambda i: tov_d[c][i])
        tov_d[c] = [tov_d[c][i] for i in order]
        tov_v[c] = [tov_v[c][i] for i in order]
        tov_usd[c] = [tov_usd[c][i] for i in order]

    full = {c: s for c, s in ser.items() if s["dates"]}
    packed = {c: (tov_d[c], tov_v[c]) for c in tov_d}
    packed_usd = {c: (tov_d[c], tov_usd[c]) for c in tov_d}

    # 시점 유니버스 — 달력은 REF 시계열에서 가져온다(한국이 005930 을 쓰는 자리)
    cal = full.get(REF, {}).get("dates") or sorted({d for s in full.values() for d in s["dates"]})
    universe = {}
    if build_universe:                            # peak 분해 실측용으로 끌 수 있다
        for d in cal:
            day = {}
            for c, m in meta.items():
                if c in full and m["firstpricedate"] <= d <= m["lastpricedate"]:
                    day[c] = m                    # ★ 같은 dict 를 공유한다(날마다 새로 안 만든다)
            universe[d] = day

    return universe, packed, full, {
        "variant": variant, "usd_krw": usd_krw, "n_codes_meta": len(meta),
        "n_codes_window": len(codes), "n_codes_with_series": len(full),
        "n_rows": n_rows, "n_bad_close": n_badfac, "n_dates": len(cal),
        "turnover_usd": packed_usd}
