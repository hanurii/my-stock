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
ACCUM_WINDOW = 15           # 매집 신호·MVP 관찰 창(거래일)
UP_STREAK_IDEAL = 7         # 연속 상승 이상적 기준(미너비니)
TIGHT_DAY_PCT = 0.01        # 일중 변동폭 <1% = tight day(나쁜 마감 제외)
MVP_M_MIN = 12              # M: 15일 중 상승 마감 최소일
MVP_V_MULT = 1.25           # V: 창 평균 거래량 / 직전 15일 평균 최소배
MVP_P_MIN = 0.20            # P: 창 최고 종가 상승률 최소

# --- 강세 매도(과열·절정) 감시 ---
EXT_GATE_PCT    = 5.0     # 확장 게이트: (현재/피벗-1)*100 ≥ 5
CLIMAX_MIN_W    = 5       # 절정 분출 관찰 창 하한(거래일)
CLIMAX_25_MAX_W = 15      # +25% 판정 창 상한
CLIMAX_70_MAX_W = 10      # +70% 판정 창 상한
CLIMAX_25_GAIN  = 0.25    # 5~15일 상승률 문턱
CLIMAX_70_GAIN  = 0.70    # 5~10일 상승률 문턱
BLOWOFF_RECENT  = 3       # 최대 상승일/변동폭이 "최근"으로 인정되는 거래일
BLOWOFF_MIN_DAYS = 5      # blowoff 판정 최소 돌파후 거래일
GAP_RECENT      = 3       # 소진성 갭이 "최근"으로 인정되는 거래일
DISTRIB_WINDOW  = 10      # 분산(반전·처닝) trailing 관찰 거래일
CHURN_MOVE_PCT  = 0.01    # 처닝: 종가 변화 절대값 < 1%


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
        return {"id": rid, "status": "watch",
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
        return {"id": rid, "status": "watch",
                "detail": f"🟡 반전 회복 관찰중 (D+{elapsed}/{SQUAT_GRACE_DAYS})"}
    return {"id": rid, "status": "violation",
            "detail": f"유예 초과 — 피벗 회복 실패 (D+{elapsed})"}


def sig_climax_run(series):
    """S1 절정 분출: 최근 종가 trailing 상승률(5~15일 +25% / 5~10일 +70%)."""
    rid = "climax_run"
    closes = series["closes"]
    n = len(closes)
    best = None  # (w, r) — 25% 이상 중 최대
    for w in range(CLIMAX_MIN_W, CLIMAX_25_MAX_W + 1):
        if n - 1 - w < 0:
            continue
        base = closes[n - 1 - w]
        if not base:
            continue
        r = closes[-1] / base - 1
        if w <= CLIMAX_70_MAX_W and r >= CLIMAX_70_GAIN:
            return {"id": rid, "status": "fired",
                    "detail": f"최근 {w}거래일 +{r * 100:.0f}% — 폭발적 분출(70%+)"}
        if r >= CLIMAX_25_GAIN and (best is None or r > best[1]):
            best = (w, r)
    if best is not None:
        w, r = best
        return {"id": rid, "status": "fired",
                "detail": f"최근 {w}거래일 +{r * 100:.0f}% — 절정 구간(25%+)"}
    if n - 1 - CLIMAX_MIN_W < 0:
        return {"id": rid, "status": "pending", "detail": "데이터 부족"}
    return {"id": rid, "status": "clear", "detail": "절정 분출 없음"}


def sig_blowoff_day(series, bi):
    """S2 최대 상승일/변동폭이 최근 BLOWOFF_RECENT일 안에 출현(막판 폭발)."""
    rid = "blowoff_day"
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    start = bi + 1
    if n - start < BLOWOFF_MIN_DAYS:
        return {"id": rid, "status": "pending",
                "detail": f"돌파 후 {max(n - start, 0)}거래일 — 판정 전"}
    best_g = (None, -1.0)   # (idx, gain)
    best_r = (None, -1.0)   # (idx, range)
    for i in range(start, n):
        if closes[i - 1]:
            g = closes[i] / closes[i - 1] - 1
            if g > best_g[1]:
                best_g = (i, g)
        if closes[i]:
            rng = (highs[i] - lows[i]) / closes[i]
            if rng > best_r[1]:
                best_r = (i, rng)
    recent_lo = n - BLOWOFF_RECENT

    def when(i):
        k = (n - 1) - i
        return "오늘" if k == 0 else ("어제" if k == 1 else f"{k}일 전")

    gi, gv = best_g
    if gi is not None and gi >= recent_lo:
        return {"id": rid, "status": "fired",
                "detail": f"구간 최대 상승일 +{gv * 100:.0f}%이 {when(gi)} 출현"}
    ri, rv = best_r
    if ri is not None and ri >= recent_lo:
        return {"id": rid, "status": "fired",
                "detail": f"구간 최대 변동폭 {rv * 100:.0f}%가 {when(ri)} 출현"}
    return {"id": rid, "status": "clear", "detail": "막판 최대 상승/변동 아님"}


def evaluate_accumulation(series, bi):
    """돌파 후 첫 ACCUM_WINDOW 거래일 매집 신호 3종(등급 없이 체크리스트).
    창은 15일 지나면 첫 15일로 고정, 미만이면 진행 중 부분 계산."""
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    elapsed = (n - 1) - bi
    end = min(bi + ACCUM_WINDOW, n - 1)          # 첫 15일로 고정
    has_days = end >= bi + 1
    window = f"{ACCUM_WINDOW}일 완료" if elapsed >= ACCUM_WINDOW else f"D+{max(elapsed,0)}/{ACCUM_WINDOW}"
    up = down = good = bad = 0
    streak = max_streak = 0
    for i in range(bi + 1, end + 1):
        if closes[i] > closes[i - 1]:
            up += 1; streak += 1; max_streak = max(max_streak, streak)
        elif closes[i] < closes[i - 1]:
            down += 1; streak = 0
        else:
            streak = 0
        rng = highs[i] - lows[i]
        if rng > 0 and closes[i] and (rng / closes[i]) >= TIGHT_DAY_PCT:
            mid = (highs[i] + lows[i]) / 2
            if closes[i] > mid:
                good += 1
            elif closes[i] < mid:
                bad += 1

    def st(cond, data_ok):
        return "met" if cond else ("unmet" if data_ok else "pending")

    signals = [
        {"id": "up_days_dominant", "status": st(up > down, up + down > 0),
         "detail": f"상승 {up} · 하락 {down}"},
        {"id": "quality_closes", "status": st(good > bad, good + bad > 0),
         "detail": f"좋은 {good} · 나쁜 {bad}"},
        {"id": "up_streak_7",
         "status": ("met" if max_streak >= UP_STREAK_IDEAL else ("unmet" if has_days else "pending")),
         "detail": f"최고 {max_streak}일"},
    ]
    return {"window": window, "elapsed": elapsed, "signals": signals}


def evaluate_mvp(series, bi):
    """돌파 후 ACCUM_WINDOW 거래일 MVP(M·V·P). 15일 미경과면 전체 pending."""
    closes, vols = series["closes"], series["volumes"]
    n = len(closes)
    elapsed = (n - 1) - bi
    end = min(bi + ACCUM_WINDOW, n - 1)
    win_closes = closes[bi + 1:end + 1]
    p_gain = (max(win_closes) / closes[bi] - 1) if (win_closes and closes[bi]) else None
    p_detail = f"{p_gain * 100:+.0f}%" if p_gain is not None else "—"
    if elapsed < ACCUM_WINDOW:
        return {"status": "pending",
                "m": {"ok": None, "detail": f"{max(elapsed, 0)}/{ACCUM_WINDOW}일 (판정 전)"},
                "v": {"ok": None, "detail": "판정 전"},
                "p": {"ok": None, "detail": p_detail}}
    w = range(bi + 1, bi + ACCUM_WINDOW + 1)     # 확정 15일 창
    up = sum(1 for i in w if closes[i] > closes[i - 1])
    m_ok = up >= MVP_M_MIN
    win_vol = [vols[i] for i in w if vols[i] is not None]
    prior = [vols[i] for i in range(max(0, bi - ACCUM_WINDOW), bi) if vols[i] is not None]
    if len(prior) >= 5 and win_vol:
        v_ratio = (sum(win_vol) / len(win_vol)) / (sum(prior) / len(prior))
        v_ok = v_ratio >= MVP_V_MULT
        v_detail = f"직전 대비 {v_ratio:.1f}배"
    else:
        v_ok, v_detail = None, "거래량 표본 부족"
    p_ok = (p_gain is not None) and (p_gain >= MVP_P_MIN)
    status = "yes" if (m_ok and v_ok and p_ok) else "no"
    return {"status": status,
            "m": {"ok": m_ok, "detail": f"{up}/{ACCUM_WINDOW}일 상승"},
            "v": {"ok": v_ok, "detail": v_detail},
            "p": {"ok": p_ok, "detail": p_detail}}


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
    accumulation = evaluate_accumulation(series, bi)
    mvp = evaluate_mvp(series, bi)
    extension_pct = (round((current / pivot_price - 1) * 100, 1)
                     if pivot_price else None)
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
        "extension_pct": extension_pct,
        "accumulation": accumulation,
        "mvp": mvp,
    }
