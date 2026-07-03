# scripts/canslim_lib/sell_rules.py
"""매수 후 미너비니 매도 규칙 위반(violation) 판정 순수 모듈.

입력: ohlcv_matrix.get_series() 형태의 일봉 dict (dates/closes/highs/lows/volumes)
정의: docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md
"""
from __future__ import annotations

HEAVY_VOL_MULT = 1.5        # 대량 거래 기준(직전 50일 평균 대비)
STRONG_BREAKOUT_MULT = 1.5  # 정상 돌파 거래량 기준
LOWER_CLOSE_RUN = 3         # 연속 저저점(종가<전일 저가) 위반 기준 일수
MIN_TREND_DAYS = 5          # 하락일·나쁜 마감 우세 판정 최소 경과 거래일
BREAKOUT_LOOKBACK = 20      # 매수일에서 돌파일을 찾는 최대 소급 거래일


def avg_volume(volumes, i, window=50, min_days=5):
    """i일 직전 최대 window 거래일 평균 거래량(판정일 제외). 표본 부족 시 None."""
    lo = max(0, i - window)
    sample = [v for v in volumes[lo:i] if v]
    if len(sample) < min_days:
        return None
    return sum(sample) / len(sample)


def find_breakout_index(series, buy_date, pivot_price):
    """매수일에서 최대 BREAKOUT_LOOKBACK 거래일 소급해
    '전일 종가 <= 피벗 < 당일 종가' 인 가장 최근 날을 찾는다.
    반환: (index, estimated) — 못 찾으면 매수일 인덱스(estimated=True).
    """
    dates, closes = series["dates"], series["closes"]
    buy_idx = 0
    for i in range(len(dates) - 1, -1, -1):
        if dates[i] <= buy_date:
            buy_idx = i
            break
    if pivot_price is None:
        return buy_idx, True
    lo = max(1, buy_idx - BREAKOUT_LOOKBACK + 1)
    for i in range(buy_idx, lo - 1, -1):
        if closes[i] > pivot_price and closes[i - 1] <= pivot_price:
            return i, False
    return buy_idx, True


def rule_low_volume_breakout(series, bi):
    """규칙① 저거래량 돌파: 돌파일 거래량 < 50일 평균이면 위반."""
    rid = "low_volume_breakout"
    vols = series["volumes"]
    avg = avg_volume(vols, bi)
    if avg is None:
        return {"id": rid, "status": "pending", "detail": "거래량 표본 부족"}
    if vols[bi] is None:
        return {"id": rid, "status": "pending", "detail": "돌파일 거래량 데이터 없음"}
    ratio = vols[bi] / avg
    if ratio < 1.0:
        return {"id": rid, "status": "violation",
                "detail": f"돌파일 거래량 {ratio:.1f}배 — 평균에도 못 미침"}
    if ratio < STRONG_BREAKOUT_MULT:
        return {"id": rid, "status": "pass",
                "detail": f"돌파일 거래량 {ratio:.1f}배 — 정상 돌파(1.5배+)에는 못 미침"}
    return {"id": rid, "status": "pass", "detail": f"돌파일 거래량 {ratio:.1f}배"}


def rule_heavy_volume_pullback(series, bi):
    """규칙② 대량 거래 후퇴: 돌파 후 하락 마감 + 거래량 1.5배 이상인 날이 있으면 위반."""
    rid = "heavy_volume_pullback"
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    worst = None  # (index, ratio)
    for i in range(bi + 1, n):
        avg = avg_volume(vols, i)
        if avg is None:
            continue
        if closes[i] < closes[i - 1] and vols[i] >= HEAVY_VOL_MULT * avg:
            ratio = vols[i] / avg
            if worst is None or ratio > worst[1]:
                worst = (i, ratio)
    if worst:
        i, ratio = worst
        return {"id": rid, "status": "violation",
                "detail": f"{dates[i]} 하락 마감 + 거래량 {ratio:.1f}배"}
    return {"id": rid, "status": "pass", "detail": "대량 거래 하락일 없음"}


def rule_consecutive_lower_closes(series, bi):
    """규칙③ 연속 저저점: 종가 < 전일 저가 가 3일 연속이면 위반 (종가 기준, 사용자 확정)."""
    rid = "consecutive_lower_closes"
    closes, lows, dates = series["closes"], series["lows"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    run = 0
    max_run, max_end = 0, None
    for i in range(bi + 1, n):
        if closes[i] < lows[i - 1]:
            run += 1
            if run > max_run:
                max_run, max_end = run, i
        else:
            run = 0
    if max_run >= LOWER_CLOSE_RUN:
        return {"id": rid, "status": "violation",
                "detail": f"종가<전일 저가 {max_run}일 연속 (~{dates[max_end]})"}
    if run == LOWER_CLOSE_RUN - 1:
        return {"id": rid, "status": "pass",
                "detail": f"경고: 종가<전일 저가 {run}일째 진행 중"}
    return {"id": rid, "status": "pass", "detail": "연속 저저점 없음"}
