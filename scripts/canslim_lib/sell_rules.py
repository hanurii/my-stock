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


def rule_close_below_ma(series, bi):
    """규칙④ 이평선 아래 마감: 돌파 후 종가<20일선이면 위반.
    종가<50일선 + 대량 거래면 '심각' 표기(위반 1건으로 집계)."""
    rid = "close_below_ma"
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    first, severe, computable = None, None, False
    for i in range(bi + 1, n):
        if i + 1 < 20:
            continue  # 20일선 계산 불가
        computable = True
        ma20 = sum(closes[i - 19:i + 1]) / 20
        if closes[i] < ma20 and first is None:
            first = i
        if i + 1 >= 50:
            ma50 = sum(closes[i - 49:i + 1]) / 50
            avg = avg_volume(vols, i)
            if (closes[i] < ma50 and avg and vols[i] >= HEAVY_VOL_MULT * avg
                    and severe is None):
                severe = i
    if not computable:
        return {"id": rid, "status": "pending", "detail": "20일선 계산에 데이터 부족"}
    if severe is not None:
        return {"id": rid, "status": "violation",
                "detail": f"심각: {dates[severe]} 50일선 아래 + 대량 거래 마감"}
    if first is not None:
        return {"id": rid, "status": "violation", "detail": f"{dates[first]} 20일선 아래 마감"}
    return {"id": rid, "status": "pass", "detail": "20일선 위 유지"}


def rule_weak_days_dominant(series, bi):
    """규칙⑤ 하락일·나쁜 마감 우세(통합): 돌파 후 5거래일 이상 지난 뒤,
    하락일>상승일 또는 나쁜 마감>좋은 마감이면 위반.
    나쁜 마감 = 종가가 당일 고저 범위 아래 절반. 보합·고가=저가 날은 세지 않음."""
    rid = "weak_days_dominant"
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    elapsed = n - (bi + 1)
    if elapsed < MIN_TREND_DAYS:
        return {"id": rid, "status": "pending",
                "detail": f"경과 {elapsed}거래일 — {MIN_TREND_DAYS}거래일부터 판정"}
    down = up = bad = good = 0
    for i in range(bi + 1, n):
        if closes[i] < closes[i - 1]:
            down += 1
        elif closes[i] > closes[i - 1]:
            up += 1
        if highs[i] > lows[i]:
            mid = (highs[i] + lows[i]) / 2
            if closes[i] < mid:
                bad += 1
            elif closes[i] > mid:
                good += 1
    counts = f"하락 {down}·상승 {up} / 나쁜마감 {bad}·좋은마감 {good}"
    if down > up or bad > good:
        return {"id": rid, "status": "violation", "detail": counts}
    return {"id": rid, "status": "pass", "detail": counts}


def rule_squat(series, bi, pivot_price, breakout_confirmed=True):
    """규칙⑥ 스쿼트(돌파 실패): 돌파 후 종가가 피벗 아래로 복귀하면 위반.
    피벗 돌파가 확인되지 않았으면(돌파일 추정) 스쿼트 판정 자체가 성립하지 않음."""
    rid = "squat"
    if pivot_price is None:
        return {"id": rid, "status": "na", "detail": "피벗 없음 — 판정 불가"}
    if not breakout_confirmed:
        return {"id": rid, "status": "na", "detail": "피벗 돌파 미확인 — 판정 불가"}
    closes, dates = series["closes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    for i in range(bi + 1, n):
        if closes[i] < pivot_price:
            return {"id": rid, "status": "violation",
                    "detail": f"{dates[i]} 종가가 피벗({pivot_price:,.0f}) 아래 복귀"}
    return {"id": rid, "status": "pass", "detail": "피벗 위 유지"}


def evaluate_holding(series, buy_date, buy_price, stop_loss_pct, pivot_price=None):
    """보유 1종목 종합 판정. 손절(최우선) → 위반 1개 이상 조기 매도 → 정상 보유."""
    bi, estimated = find_breakout_index(series, buy_date, pivot_price)
    current = series["closes"][-1]
    stop_price = buy_price * (1 + stop_loss_pct / 100)
    rules = [
        rule_low_volume_breakout(series, bi),
        rule_heavy_volume_pullback(series, bi),
        rule_consecutive_lower_closes(series, bi),
        rule_close_below_ma(series, bi),
        rule_weak_days_dominant(series, bi),
        rule_squat(series, bi, pivot_price, breakout_confirmed=not estimated),
    ]
    violation_count = sum(1 for r in rules if r["status"] == "violation")
    if current <= stop_price:
        signal = "stop_loss"
    elif violation_count >= 1:
        signal = "early_sell"
    else:
        signal = "hold"
    return {
        "current_price": current,
        "profit_pct": round((current / buy_price - 1) * 100, 2),
        "stop_price": round(stop_price, 2),
        "pct_to_stop": round((stop_price / current - 1) * 100, 2),
        "breakout_date": series["dates"][bi],
        "breakout_date_estimated": estimated,
        "signal": signal,
        "violation_count": violation_count,
        "rules": rules,
    }
