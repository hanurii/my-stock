# scripts/canslim_lib/sell_rules.py
"""매수 후 미너비니 매도 규칙 위반(violation) 판정 순수 모듈.

입력: ohlcv_matrix.get_series() 형태의 일봉 dict (dates/closes/highs/lows/volumes)
정의: docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md
"""
from __future__ import annotations

HEAVY_VOL_MULT = 1.5        # 대량 거래 기준(직전 50일 평균 대비)
STRONG_BREAKOUT_MULT = 1.5  # 정상 돌파 거래량 기준
LOWER_LOW_RUN = 3           # 연속 저점경신(저가 기준) 위반 기준 일수
MIN_TREND_DAYS = 5          # 하락일·나쁜 마감 우세 판정 최소 경과 거래일
BREAKOUT_LOOKBACK = 20      # 매수일에서 돌파일을 찾는 최대 소급 거래일
SQUAT_GRACE_DAYS = 10       # 돌파 후 반전 회복 유예(약 2주)


def avg_volume(volumes, i, window=50, min_days=5):
    """i일 직전 최대 window 거래일 평균 거래량(판정일 제외). 표본 부족 시 None."""
    lo = max(0, i - window)
    sample = [v for v in volumes[lo:i] if v]
    if len(sample) < min_days:
        return None
    return sum(sample) / len(sample)


def find_breakout_index(series, buy_date, pivot_price):
    """매수일에서 최대 BREAKOUT_LOOKBACK 거래일 소급해
    '전일 고가 <= 피벗 < 당일 고가' 인 가장 최근 날(장중 돌파 포함)을 찾는다.
    반환: (index, estimated) — 못 찾으면 매수일 인덱스(estimated=True).
    """
    dates, highs = series["dates"], series["highs"]
    buy_idx = 0
    for i in range(len(dates) - 1, -1, -1):
        if dates[i] <= buy_date:
            buy_idx = i
            break
    if pivot_price is None:
        return buy_idx, True
    lo = max(1, buy_idx - BREAKOUT_LOOKBACK + 1)
    for i in range(buy_idx, lo - 1, -1):
        if highs[i] > pivot_price and highs[i - 1] <= pivot_price:
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
                "detail": f"돌파일 거래량 {ratio:.2f}배 — 평균에도 못 미침"}
    if ratio < STRONG_BREAKOUT_MULT:
        return {"id": rid, "status": "pass",
                "detail": f"돌파일 거래량 {ratio:.2f}배 — 정상 돌파(1.5배+)에는 못 미침"}
    return {"id": rid, "status": "pass", "detail": f"돌파일 거래량 {ratio:.2f}배"}


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


def rule_consecutive_lower_lows(series, bi):
    """규칙③ 연속 저저점(저가 기준+거래량): 돌파 후 '저가<전일 저가'이고
    거래량 ≥ 50일 평균인 날이 3거래일 연속이면 위반. 거래량 낮은 저점경신은
    위반이 아니라 🟡경고로만 표시(미너비니 WAGE 사례)."""
    rid = "consecutive_lower_lows"
    lows, vols, dates = series["lows"], series["volumes"], series["dates"]
    n = len(lows)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    qrun = qmax = 0          # 거래량 붙은 저점경신 연속
    qend = None
    rawrun = rawmax = 0      # 거래량 무관 저점경신 연속(경고용)
    for i in range(bi + 1, n):
        is_ll = lows[i] < lows[i - 1]
        rawrun = rawrun + 1 if is_ll else 0
        rawmax = max(rawmax, rawrun)
        avg = avg_volume(vols, i)
        qualified = (is_ll and avg is not None and vols[i] is not None
                     and vols[i] >= avg)
        qrun = qrun + 1 if qualified else 0
        if qrun > qmax:
            qmax, qend = qrun, i
    if qmax >= LOWER_LOW_RUN:
        return {"id": rid, "status": "violation",
                "detail": f"거래량 붙은 저점경신 {qmax}일 연속 (~{dates[qend]})"}
    if rawmax >= LOWER_LOW_RUN:
        return {"id": rid, "status": "pass",
                "detail": f"🟡경고: 저점경신 {rawmax}회(거래량 낮음)"}
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
        return {"id": rid, "status": "violation",
                "detail": f"{dates[first]} 20일선 아래 마감 (돌파 {first - bi}거래일째)"}
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


def rule_breakout_failure(series, bi, pivot_price, breakout_confirmed=True):
    """규칙⑥ 돌파 실패(스쿼트+거래량 비대칭 통합).
    - 거래량 동반(>돌파일) 피벗 이탈 → 유예 무시 위반(실패한 돌파).
    - 조용한 스쿼트 → 10거래일 유예 안에선 관찰중(pass), 초과하면 위반.
    - 피벗 위 복귀 → pass. 피벗/돌파 미확인 → na."""
    rid = "breakout_failure"
    if pivot_price is None:
        return {"id": rid, "status": "na", "detail": "피벗 없음 — 판정 불가"}
    if not breakout_confirmed:
        return {"id": rid, "status": "na", "detail": "피벗 돌파 미확인 — 판정 불가"}
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    breakout_vol = vols[bi]
    below = [i for i in range(bi, n) if closes[i] < pivot_price]
    if not below:
        return {"id": rid, "status": "pass", "detail": "피벗 위 유지"}
    # 거래량 동반 돌파 실패(비대칭) — 유예 무시, 가장 심한 날을 detail로
    worst = None
    if breakout_vol:
        for i in below:
            if vols[i] and vols[i] > breakout_vol:
                ratio = vols[i] / breakout_vol
                if worst is None or ratio > worst[1]:
                    worst = (i, ratio)
    if worst:
        i, ratio = worst
        return {"id": rid, "status": "violation",
                "detail": f"거래량 동반 돌파 실패 — {dates[i]} 거래량 {ratio:.1f}배(돌파일 대비)"}
    # 조용한 스쿼트 — 회복/유예 판정
    if closes[-1] >= pivot_price:
        return {"id": rid, "status": "pass", "detail": "스쿼트 후 반전 회복(피벗 위 복귀)"}
    elapsed = (n - 1) - bi
    if elapsed <= SQUAT_GRACE_DAYS:
        return {"id": rid, "status": "pass",
                "detail": f"🟡 반전 회복 관찰중 (D+{elapsed}/{SQUAT_GRACE_DAYS})"}
    return {"id": rid, "status": "violation",
            "detail": f"유예 초과 — 피벗 회복 실패 (D+{elapsed})"}


def evaluate_holding(series, buy_date, buy_price, stop_loss_pct, pivot_price=None):
    """보유 1종목 종합 판정. 손절(최우선) → 위반 1개 이상 조기 매도 → 정상 보유."""
    bi, estimated = find_breakout_index(series, buy_date, pivot_price)
    current = series["closes"][-1]
    stop_price = buy_price * (1 + stop_loss_pct / 100)
    rules = [
        rule_low_volume_breakout(series, bi),
        rule_heavy_volume_pullback(series, bi),
        rule_consecutive_lower_lows(series, bi),
        rule_close_below_ma(series, bi),
        rule_weak_days_dominant(series, bi),
        rule_breakout_failure(series, bi, pivot_price, breakout_confirmed=not estimated),
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
