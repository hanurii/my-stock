"""Minervini 트렌드 템플레이트 8가지 조건 평가기.

참고: research/oneil-model-book/trend_template.md

8 criteria:
  1) 종가 > 150MA AND 종가 > 200MA
  2) 150MA > 200MA
  3) 200MA가 최근 1개월 상승 (4-5개월 상승은 플래그 — 정렬용)
  4) 50MA > 150MA AND 50MA > 200MA
  5) 종가 > 50MA
  6) 종가 ≥ 52주 신저가 × 1.30
  7) 종가 ≥ 52주 신고가 × 0.75 (= 신고가의 25% 이내)
  8) RS (1-99 백분위) ≥ rs_min

순수 함수 — I/O 없음. orchestrator(screen_trend_template.py) 가
universe-level 로 RS 를 계산해서 주입한다.
"""

from __future__ import annotations

TT_LOW_MIN_PCT = 30.0
TT_HIGH_MAX_PCT = 25.0
TT_SMA200_RISING_LOOKBACK_DAYS = 22       # 약 1개월
TT_SMA200_RISING_PREFERRED_DAYS = 110     # 약 5개월
TT_RS_MIN_DEFAULT = 70

SMA_WINDOW_50 = 50
SMA_WINDOW_150 = 150
SMA_WINDOW_200 = 200
WINDOW_52W = 252


def _sma(closes: list[float], window: int, end_offset: int = 0) -> float | None:
    """closes 끝에서 end_offset 만큼 더 거슬러 올라간 지점의 window일 단순 이동평균.

    end_offset=0  → 마지막 window일 평균 = avg(closes[-window:])
    end_offset=22 → 22 거래일 전을 끝으로 하는 window일 평균 = avg(closes[-window-22 : -22])
    """
    if window <= 0:
        return None
    if end_offset < 0:
        return None
    needed = window + end_offset
    if len(closes) < needed:
        return None
    if end_offset == 0:
        window_slice = closes[-window:]
    else:
        window_slice = closes[-needed:-end_offset]
    return sum(window_slice) / window


def _round(x: float | None, n: int = 2) -> float | None:
    return round(x, n) if x is not None else None


def evaluate_trend_template(
    closes: list[float],
    rs: int | None,
    rs_min: int = TT_RS_MIN_DEFAULT,
) -> dict:
    """8개 조건 평가.

    Args:
      closes: 시간순(과거→최신) 일별 종가. 마지막이 평가 기준일.
      rs: 1~99 사이 RS 점수. None 이면 조건 8 자동 fail.
      rs_min: RS 합격선 (default 70).

    Returns:
      {
        "pass": bool,                  # 8개 모두 통과 시 True
        "passed_count": int,           # 0..8
        "criteria": {"1": {pass,value,detail}, ..., "8": {...}},
        "extras": {sma50,sma150,sma200,high_52w,low_52w,
                   sma200_rising_5m_preferred, return_252d_pct, data_days}
      }
    """
    n_days = len(closes)

    # 데이터 부족: SMA200 자체가 불가
    if n_days < SMA_WINDOW_200:
        return {
            "pass": False,
            "passed_count": 0,
            "criteria": {
                str(i): {
                    "pass": False,
                    "value": None,
                    "detail": f"데이터 부족 (보유 일수 {n_days} < 200)",
                }
                for i in range(1, 9)
            },
            "extras": {
                "sma50": None, "sma150": None, "sma200": None,
                "high_52w": None, "low_52w": None,
                "sma200_rising_5m_preferred": None,
                "return_252d_pct": None,
                "data_days": n_days,
            },
        }

    last = closes[-1]
    sma50 = _sma(closes, SMA_WINDOW_50)
    sma150 = _sma(closes, SMA_WINDOW_150)
    sma200 = _sma(closes, SMA_WINDOW_200)

    # 52주 윈도우 (보유 일수 < 252 면 가용 전체 사용)
    win52 = closes[-WINDOW_52W:] if n_days >= WINDOW_52W else closes
    high_52w = max(win52)
    low_52w = min(win52)

    # 1년 수익률 (RS 계산용 — 252일 정확히 보유한 경우만)
    if n_days >= WINDOW_52W + 1 and closes[-WINDOW_52W - 1] > 0:
        return_252d_pct = (last / closes[-WINDOW_52W - 1] - 1.0) * 100.0
    else:
        # 252일 미만 — 가용한 최장 기간으로 환산 (RS orchestrator 가 단축윈도우 처리)
        if n_days >= 2 and closes[0] > 0:
            return_252d_pct = (last / closes[0] - 1.0) * 100.0
        else:
            return_252d_pct = None

    # ── 조건 1: 종가 > 150MA AND > 200MA ──
    if sma150 is None or sma200 is None:
        c1 = {"pass": False, "value": None,
              "detail": f"데이터 부족 (150MA/200MA 계산 불가, 보유 {n_days}일)"}
    else:
        c1_pass = last > sma150 and last > sma200
        c1 = {"pass": c1_pass, "value": _round(last),
              "detail": f"종가 {last:,.2f} | 150MA {sma150:,.2f} | 200MA {sma200:,.2f}"}

    # ── 조건 2: 150MA > 200MA ──
    if sma150 is None or sma200 is None:
        c2 = {"pass": False, "value": None,
              "detail": f"데이터 부족 (보유 {n_days}일)"}
    else:
        c2_pass = sma150 > sma200
        c2 = {"pass": c2_pass, "value": _round(sma150 - sma200),
              "detail": f"150MA {sma150:,.2f} - 200MA {sma200:,.2f} = {sma150 - sma200:+,.2f}"}

    # ── 조건 3: 200MA 최근 1개월 상승 (5개월은 플래그) ──
    sma200_1m_ago = _sma(closes, SMA_WINDOW_200, end_offset=TT_SMA200_RISING_LOOKBACK_DAYS)
    sma200_5m_ago = _sma(closes, SMA_WINDOW_200, end_offset=TT_SMA200_RISING_PREFERRED_DAYS)
    rising_5m_pref = (sma200 is not None and sma200_5m_ago is not None
                     and sma200 > sma200_5m_ago)

    if sma200 is None or sma200_1m_ago is None:
        c3 = {"pass": False, "value": None,
              "detail": f"데이터 부족 (1개월 전 200MA 계산 불가, 보유 {n_days}일 — 222일 필요)"}
    else:
        c3_pass = sma200 > sma200_1m_ago
        flag = "5M↑ 우수" if rising_5m_pref else ("5M↓" if sma200_5m_ago is not None else "5M 미산출")
        c3 = {
            "pass": c3_pass,
            "value": _round(sma200 - sma200_1m_ago),
            "detail": f"200MA 지금 {sma200:,.2f} vs 1M 전 {sma200_1m_ago:,.2f} "
                      f"({sma200 - sma200_1m_ago:+,.2f}) | {flag}",
        }

    # ── 조건 4: 50MA > 150MA AND > 200MA ──
    if sma50 is None or sma150 is None or sma200 is None:
        c4 = {"pass": False, "value": None,
              "detail": f"데이터 부족 (보유 {n_days}일)"}
    else:
        c4_pass = sma50 > sma150 and sma50 > sma200
        c4 = {"pass": c4_pass, "value": _round(sma50),
              "detail": f"50MA {sma50:,.2f} | 150MA {sma150:,.2f} | 200MA {sma200:,.2f}"}

    # ── 조건 5: 종가 > 50MA ──
    if sma50 is None:
        c5 = {"pass": False, "value": None, "detail": "50MA 계산 불가"}
    else:
        c5_pass = last > sma50
        c5 = {"pass": c5_pass, "value": _round(last - sma50),
              "detail": f"종가 {last:,.2f} vs 50MA {sma50:,.2f} ({last - sma50:+,.2f})"}

    # ── 조건 6: 종가 ≥ 52주저 × 1.30 (즉 +30% 이상) ──
    if low_52w <= 0:
        c6 = {"pass": False, "value": None, "detail": "52주 신저가 데이터 이상 (0 이하)"}
    else:
        above_low_pct = (last - low_52w) / low_52w * 100.0
        c6_pass = above_low_pct >= TT_LOW_MIN_PCT
        c6 = {"pass": c6_pass, "value": _round(above_low_pct, 1),
              "detail": f"52주 신저가 {low_52w:,.2f} → 종가 {last:,.2f} (+{above_low_pct:.1f}%)"}

    # ── 조건 7: 종가 ≥ 52주고 × 0.75 (= -25% 이내) ──
    if high_52w <= 0:
        c7 = {"pass": False, "value": None, "detail": "52주 신고가 데이터 이상 (0 이하)"}
    else:
        below_high_pct = (high_52w - last) / high_52w * 100.0
        c7_pass = below_high_pct <= TT_HIGH_MAX_PCT
        c7 = {"pass": c7_pass, "value": _round(below_high_pct, 1),
              "detail": f"52주 신고가 {high_52w:,.2f} vs 종가 {last:,.2f} (-{below_high_pct:.1f}%)"}

    # ── 조건 8: RS ≥ rs_min ──
    if rs is None:
        c8 = {"pass": False, "value": None,
              "detail": f"RS 미산출 (universe 비교 불가)"}
    else:
        c8_pass = rs >= rs_min
        c8 = {"pass": c8_pass, "value": int(rs),
              "detail": f"RS {rs} (기준 ≥ {rs_min})"}

    criteria = {"1": c1, "2": c2, "3": c3, "4": c4,
                "5": c5, "6": c6, "7": c7, "8": c8}
    passed_count = sum(1 for v in criteria.values() if v["pass"])
    all_pass = passed_count == 8

    return {
        "pass": all_pass,
        "passed_count": passed_count,
        "criteria": criteria,
        "extras": {
            "sma50": _round(sma50),
            "sma150": _round(sma150),
            "sma200": _round(sma200),
            "sma200_1m_ago": _round(sma200_1m_ago),
            "sma200_5m_ago": _round(sma200_5m_ago),
            "high_52w": _round(high_52w),
            "low_52w": _round(low_52w),
            "sma200_rising_5m_preferred": rising_5m_pref,
            "return_252d_pct": _round(return_252d_pct, 2),
            "data_days": n_days,
        },
    }
