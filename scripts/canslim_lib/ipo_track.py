"""신규상장(IPO) 예외 트랙 — 상장 20~199거래일 종목용 대체 트렌드 템플레이트.

설계: docs/superpowers/specs/2026-08-08-ipo-exception-track-design.md
근거: 미너비니·오닐의 primary base(상장 후 첫 베이스 3~5주 뒤 돌파) — 기존 8조건은
200일 이평·1년 RS 가 필요해 신규상장을 사실상 상장 1주년까지 무시한다(마키나락스 사례).

순수 함수 — I/O 없음. ipo_rs(iRS) 는 orchestrator(screen_trend_template.py) 가
전 종목 동일 창 percentile 로 계산해 주입한다. 기존 RS(1년 가중)와 다른 물건이라
필드·표기(iRS)를 분리한다. 파라미터 정본은 이 모듈의 DEFAULT_PARAMS.
"""

from __future__ import annotations

DEFAULT_PARAMS = {
    "min_days": 20,            # I7: 상장 최소 거래일 — primary base 최소 3주 + 미너비니 필터 판정 하한(20일)
    "max_days": 199,           # 200일부터는 기존 8조건 트랙이 담당
    "rs_window": 60,           # iRS 창(거래일) 상한 — 실제 창 = min(보유-1, 60)
    "rs_min": 80,              # 기존 SEPA 실전 기준과 동일
    "low_min_pct": 25.0,       # I3: 상장 후 최저가 대비 +25%↑ (기존 조건6 +30% 의 IPO 완화판)
    "high_max_pct": 25.0,      # I4: 상장 후 최고가 대비 -25% 이내 (기존 조건7 과 동일)
    "ma_window": 50,           # I1·I2 기준 MA — 데이터 짧으면 가용 범위로 축소
    "ma_rising_lookback": 22,  # I2: MA 상승 확인 구간 — 데이터 짧으면 가용 절반로 축소
}


def _round(x: float | None, n: int = 2) -> float | None:
    return round(x, n) if x is not None else None


def evaluate_ipo_track(
    closes: list[float],
    ipo_rs: int | None,
    filter_reasons: list | None = None,
    params: dict | None = None,
) -> dict:
    """IPO 트랙 7조건(I1~I7) 평가.

    Args:
      closes: 시간순(상장일→최신) 일별 종가. 마지막이 평가 기준일.
      ipo_rs: 전 종목 동일 창 percentile(1~99). None 이면 I5 자동 fail.
      filter_reasons: 미너비니 필터 결과 — None=필터 미적용(통과 처리),
        []=통과, 비어있지 않으면 I6 fail(사유 목록).
      params: DEFAULT_PARAMS 오버라이드.

    Returns:
      {"pass": bool, "passed_count": int(0..7),
       "criteria": {"I1"..{pass,value,detail}.."I7"}, "extras": {...}}
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    n = len(closes)

    # I7 미달이면 나머지 조건은 평가 의미 없음 — 전부 fail 로 채워 반환
    if n < p["min_days"] or not closes or closes[-1] is None or closes[-1] <= 0:
        detail = f"상장 {n}거래일 < 최소 {p['min_days']}일 (또는 종가 이상)"
        return {
            "pass": False, "passed_count": 0,
            "criteria": {f"I{i}": {"pass": False, "value": None, "detail": detail}
                         for i in range(1, 8)},
            "extras": {"data_days": n, "ma_window_used": None,
                       "ma_rising_lookback_used": None, "ma_now": None,
                       "ma_then": None, "high_listed": None, "low_listed": None},
        }

    last = closes[-1]
    lookback = min(p["ma_rising_lookback"], max(1, n // 2))
    w = min(p["ma_window"], n - lookback)   # n≥20, lookback≤n/2 → w≥n/2≥10
    ma_now = sum(closes[-w:]) / w
    ma_then = sum(closes[-w - lookback:-lookback]) / w
    high_listed = max(closes)
    low_listed = min(closes)

    # I1: 종가 > 기준MA (기존 조건1·2·5 의 축약 — 200/150MA 는 존재하지 않음)
    c1 = {"pass": last > ma_now, "value": _round(last - ma_now),
          "detail": f"종가 {last:,.2f} vs {w}일MA {ma_now:,.2f} ({last - ma_now:+,.2f})"}

    # I2: 기준MA 상승 (기존 조건3 대체)
    c2 = {"pass": ma_now > ma_then, "value": _round(ma_now - ma_then),
          "detail": f"{w}일MA 지금 {ma_now:,.2f} vs {lookback}일 전 {ma_then:,.2f} "
                    f"({ma_now - ma_then:+,.2f})"}

    # I3: 상장 후 최저가 대비 (기존 조건6 대체 — +30%→+25% 완화)
    if low_listed <= 0:
        c3 = {"pass": False, "value": None, "detail": "상장 후 최저가 데이터 이상 (0 이하)"}
    else:
        above_low = (last - low_listed) / low_listed * 100.0
        c3 = {"pass": above_low >= p["low_min_pct"], "value": _round(above_low, 1),
              "detail": f"상장 후 최저가 {low_listed:,.2f} → 종가 {last:,.2f} "
                        f"(+{above_low:.1f}%, 기준 ≥{p['low_min_pct']:g}%)"}

    # I4: 상장 후 최고가 근접 (기존 조건7 동일 로직 — 가용 전체 창)
    below_high = (high_listed - last) / high_listed * 100.0
    c4 = {"pass": below_high <= p["high_max_pct"], "value": _round(below_high, 1),
          "detail": f"상장 후 최고가 {high_listed:,.2f} vs 종가 {last:,.2f} "
                    f"(-{below_high:.1f}%, 기준 ≤{p['high_max_pct']:g}%)"}

    # I5: iRS (기존 조건8 대체 — 동일 창 percentile)
    if ipo_rs is None:
        c5 = {"pass": False, "value": None, "detail": "iRS 미산출 (비교풀 부족)"}
    else:
        c5 = {"pass": ipo_rs >= p["rs_min"], "value": int(ipo_rs),
              "detail": f"iRS {ipo_rs} (기준 ≥ {p['rs_min']})"}

    # I6: 미너비니 필터 (우선주·외국법인·저유동성)
    if filter_reasons is None:
        c6 = {"pass": True, "value": None, "detail": "필터 미적용 실행 (--minervini-filter 없음)"}
    elif not filter_reasons:
        c6 = {"pass": True, "value": None, "detail": "우선주·외국법인·저유동성 아님"}
    else:
        rules = ", ".join(str(r.get("rule", r)) for r in filter_reasons)
        c6 = {"pass": False, "value": None, "detail": f"미너비니 필터 제외: {rules}"}

    # I7: 상장 성숙도 (위에서 미달 조기반환 — 여기 도달하면 통과)
    c7 = {"pass": True, "value": n,
          "detail": f"상장 {n}거래일 ({p['min_days']}~{p['max_days']}일 구간)"}

    criteria = {"I1": c1, "I2": c2, "I3": c3, "I4": c4, "I5": c5, "I6": c6, "I7": c7}
    passed_count = sum(1 for v in criteria.values() if v["pass"])
    return {
        "pass": passed_count == 7,
        "passed_count": passed_count,
        "criteria": criteria,
        "extras": {
            "data_days": n,
            "ma_window_used": w,
            "ma_rising_lookback_used": lookback,
            "ma_now": _round(ma_now),
            "ma_then": _round(ma_then),
            "high_listed": _round(high_listed),
            "low_listed": _round(low_listed),
        },
    }
