"""'미너비니가 사지 않는 주식' 걸러내기 (SEPA 전용 유니버스 필터).

2026-07 한 달간 연쇄 손절 10종목(11왕복)의 공통 프로필 실측에서 나온 필터다
(`docs/superpowers/specs/2026-08-03-minervini-non-buyable-filter.md`):
미너비니의 SEPA는 "기관이 사 모으는 주도주"가 전제인데, 아래 세 부류는
추세 8조건을 기술적으로 통과해도 그 전제 자체가 성립하지 않는다.

1. **우선주** (preferred_stock) — 의결권 없는 파생 주식. 기관 수급이 없고
   유동성이 얇아 미너비니 유니버스 밖. GS우(-4.9%·-4.8%)·S-Oil우(-9.5%,
   지정가 손절 미체결 사고)가 실증 사례. KRX 코드 규칙: 보통주는 끝자리 0,
   우선주(신형 포함)는 5/7/9 등 — 끝자리가 0이 아니면 우선주로 본다.
2. **외국법인** (foreign_listing) — 코드 9xxxxx 인 코스닥 외국기업(중국계 등).
   회계·지배구조 신뢰 문제로 만성 저평가·기관 부재. 로스웰(900260)이 사례.
3. **저유동성** (low_liquidity) — 50일 평균 거래대금이 기준(기본 10억원) 미만.
   기관이 못 들어오는 유동성 = 손절 시장가 집행 자체가 가격을 무너뜨린다
   (로스웰 0.67억: 포지션 2천만원이 하루 거래대금의 30%). 기준 근거는 스펙 문서.

적용 위치: `screen_trend_template.py`의 **RS 계산 뒤, 8조건 평가 앞**.
RS 백분위는 전체 시장 대비여야 하므로 비교풀은 건드리지 않고(저유동 종목이
시장의 ~57%라 풀에서 빼면 전 종목 RS 가 왜곡됨), 관문 산출물에서만 뺀다 —
`sepa-trend-candidates.json`에서 사라지므로 이 파일을 읽는 VCP·3C·파워플레이
(트렌드/전수)·매수추천 전부에 전파된다. 공유 스크리너(trend-template·make-hero,
RS 70 페이지)는 이 필터를 켜지 않는다(`--minervini-filter` — SEPA 전용).
"""

from __future__ import annotations

from bisect import bisect_right

# 50일 평균 거래대금 하한(억원). 근거: 스펙 문서(포지션 2천만원 ≤ ADV 2% 등).
MIN_TURNOVER_EOK_DEFAULT = 10.0
# 평균 거래대금 창(거래일). VCP dry-up 으로 최근 며칠이 인위적으로 얇아지는 것을
# 평활하기 위해 50일 — 판정에는 최소 20일을 요구한다.
TURNOVER_WINDOW_DAYS = 50
TURNOVER_MIN_DAYS = 20

EXCLUSION_LABEL = "미너비니가 사지 않는 주식"


def avg_turnover_eok(series: dict | None, asof: str | None = None,
                     window: int = TURNOVER_WINDOW_DAYS) -> float | None:
    """최근 `window` 거래일 평균 거래대금(억원). 판정 불가면 None.

    series: {"dates":[...], "closes":[...], "volumes":[...]} (ohlcv_matrix.get_series).
    asof: 주어지면 그 날짜까지로 잘라(룩어헤드 방지) 계산 — 백테스트용.
    """
    if not series:
        return None
    closes = series.get("closes") or []
    vols = series.get("volumes") or []
    dates = series.get("dates") or []
    n = min(len(closes), len(vols))
    if asof and dates:
        n = min(n, bisect_right(dates, asof))
    if n < TURNOVER_MIN_DAYS:
        return None
    lo = max(0, n - window)
    vals = [(closes[i] or 0) * (vols[i] or 0) for i in range(lo, n)]
    return sum(vals) / len(vals) / 1e8


def classify_non_minervini(stock: dict, series: dict | None,
                           asof: str | None = None,
                           min_turnover_eok: float = MIN_TURNOVER_EOK_DEFAULT
                           ) -> list[dict]:
    """해당 종목이 '미너비니가 사지 않는 주식'에 걸리는 사유 목록(빈 리스트=통과)."""
    code = str(stock.get("code", "")).zfill(6)
    reasons: list[dict] = []

    if code and code[-1] != "0":
        reasons.append({
            "rule": "preferred_stock",
            "detail": "우선주(코드 끝자리≠0) — 기관 수급 없는 파생 주식, 미너비니 유니버스 밖",
        })

    if code.startswith("9"):
        reasons.append({
            "rule": "foreign_listing",
            "detail": "코스닥 외국법인(코드 9xxxxx) — 회계·지배구조 신뢰 문제로 기관 부재",
        })

    turnover = avg_turnover_eok(series, asof=asof)
    if turnover is not None and turnover < min_turnover_eok:
        reasons.append({
            "rule": "low_liquidity",
            "detail": (f"50일 평균 거래대금 {turnover:.1f}억 < {min_turnover_eok:g}억 — "
                       "기관이 못 들어오는 유동성(손절 시장가가 가격을 무너뜨림)"),
            "avg_turnover_eok": round(turnover, 2),
        })
    return reasons


def filter_minervini_universe(universe: list[dict], get_series,
                              asof: str | None = None,
                              min_turnover_eok: float = MIN_TURNOVER_EOK_DEFAULT
                              ) -> tuple[list[dict], list[dict]]:
    """유니버스를 (통과, 제외) 로 나눈다. 제외 원소에 exclusion_reasons 부가.

    liveness.filter_live_universe 와 같은 계약 — 유니버스 단계에서 한 번 걸러
    하위 산출물 전부(VCP·3C·파워플레이·매수추천)에 전파된다.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    for stock in universe:
        code = str(stock.get("code", "")).zfill(6)
        reasons = classify_non_minervini(
            stock, get_series(code), asof=asof, min_turnover_eok=min_turnover_eok)
        if reasons:
            dropped.append({**stock, "exclusion_reasons": reasons})
        else:
            kept.append(stock)
    return kept, dropped
