"""미너비니 파워 플레이(High Tight Flag) 평가 부품 (순수 함수).

개념(깃대·깃발·조용한 출발·거래량 마름)=마크 미너비니. 구체 수치·계산규칙=이
프로젝트의 공학적 번역(원전 아님).
정의·근거: docs/superpowers/specs/2026-06-29-find-power-play-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "min_total_days": 20,
    "min_flagpole_gain": 90.0,
    "max_flagpole_days": 70,
    "pole_vol_mult": 1.5,
    "quiet_window": 20,
    "max_pre_pole_gain": 30.0,
    "min_flag_days": 8,
    "max_flag_days": 30,
    "max_flag_depth": 20.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
    "min_flag_pullback": 3.0,
    "flag_window": 45,
}


def find_flagpole(highs: list[float], lows: list[float], max_flagpole_days: int,
                  min_flag_pullback: float | None = None,
                  flag_window: int | None = None) -> dict:
    """깃발 천장(피벗)과 그 직전 max_flagpole_days 경계 안의 최저 저점(깃대 시작)을
    찾아 상승률·기간을 계산한다.

    flag_window 가 주어지면 피벗 후보 탐색을 최근 flag_window 개 봉으로 한정한다
    (미너비니: 피벗=최근 가장 타이트한 깃발 천장 → 무관한 옛 고점 배제). None 이면
    전체 구간(하위호환). min_flag_pullback 가 주어지면 '그 뒤로 그만큼(%) 이상 눌린'
    고점만 후보(돌파 봉이 피벗을 가로채지 않음).
    """
    if not highs or not lows:
        return {"flag_high_idx": 0, "flag_high": 0.0,
                "pole_start_idx": 0, "pole_start_low": 0.0,
                "flagpole_gain_pct": 0.0, "flagpole_days": 0}
    n = len(highs)
    lo = max(0, n - flag_window) if (flag_window is not None and flag_window > 0) else 0
    if min_flag_pullback is None:
        flag_high_idx = max(range(lo, n), key=lambda i: highs[i])
    else:
        pb = min_flag_pullback / 100.0
        cand = [i for i in range(lo, n - 1)
                if min(lows[i + 1:]) <= highs[i] * (1 - pb)]
        flag_high_idx = (max(cand, key=lambda i: highs[i]) if cand
                         else max(range(lo, n), key=lambda i: highs[i]))
    flag_high = highs[flag_high_idx]
    window_start = max(0, flag_high_idx - max_flagpole_days)
    search_end = flag_high_idx
    if search_end <= window_start:
        return {"flag_high_idx": flag_high_idx, "flag_high": flag_high,
                "pole_start_idx": flag_high_idx, "pole_start_low": flag_high,  # sentinel: no valid pole start
                "flagpole_gain_pct": 0.0, "flagpole_days": 0}
    pole_start_idx = min(range(window_start, search_end), key=lambda i: lows[i])
    pole_start_low = lows[pole_start_idx]
    gain = (flag_high - pole_start_low) / pole_start_low * 100.0 if pole_start_low > 0 else 0.0
    return {"flag_high_idx": flag_high_idx, "flag_high": flag_high,
            "pole_start_idx": pole_start_idx, "pole_start_low": pole_start_low,
            "flagpole_gain_pct": gain, "flagpole_days": flag_high_idx - pole_start_idx}


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def evaluate_power_play(series: dict, params: dict | None = None) -> dict:
    """파워 플레이(High Tight Flag) 종합 판정."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    lb = p["lookback_days"]
    closes = (series.get("closes") or [])[-lb:]
    highs = (series.get("highs") or [])[-lb:]
    lows = (series.get("lows") or [])[-lb:]
    vols = (series.get("volumes") or [])[-lb:]
    dates = (series.get("dates") or [])[-lb:]

    base: dict = {
        "pattern_detected": False, "entry_ready": False,
        "flagpole_gain_pct": None, "flagpole_days": None, "flagpole_vol_ratio": None,
        "pre_pole_gain_pct": None, "flag_length_days": None, "flag_depth_pct": None,
        "pivot_price": None, "pct_to_pivot": None, "volume_dryup_ratio": None,
        "tightness_pct": None, "status": "forming", "reason": None,
        "pole_start_date": None, "flag_high_date": None,
    }
    n = len(closes)
    if n == 0:
        base["reason"] = "no_data"
        return base
    if n < p["min_total_days"]:
        base["reason"] = "base_too_short"
        return base

    fp = find_flagpole(highs, lows, p["max_flagpole_days"], p["min_flag_pullback"], p["flag_window"])
    fhi = fp["flag_high_idx"]
    psi = fp["pole_start_idx"]
    flag_high = fp["flag_high"]
    base["flagpole_gain_pct"] = round(fp["flagpole_gain_pct"], 2)
    base["flagpole_days"] = fp["flagpole_days"]
    base["pole_start_date"] = dates[psi] if psi < len(dates) else None
    base["flag_high_date"] = dates[fhi] if fhi < len(dates) else None
    base["pivot_price"] = round(flag_high, 2)

    # --- 깃발 지표 ---
    flag_lows = lows[fhi:]
    flag_low = min(flag_lows) if flag_lows else flag_high
    flag_len = (n - 1) - fhi
    flag_depth = (flag_high - flag_low) / flag_high * 100.0 if flag_high > 0 else 0.0
    base["flag_length_days"] = flag_len
    base["flag_depth_pct"] = round(flag_depth, 2)

    # --- 조용한 베이스 / 깃대(상승) 구간 분리 + 거래량 지표 ---
    # 베이스 저점(psi)은 보통 조용한 바닥(구간 앞쪽)이므로, 저점 *직후*
    # quiet_window 거래일을 '조용한 베이스', 그 이후~flag_high 를 '깃대 상승'으로
    # 나눈다(저점이 맨 앞에 와도 견고). 상승 구간이 비면 [psi,fhi] 전체로 폴백.
    quiet_end = min(psi + p["quiet_window"], fhi)
    quiet_vols = vols[psi:quiet_end]
    quiet_highs = highs[psi:quiet_end]
    quiet_lows = lows[psi:quiet_end]
    quiet_vol_avg = _mean(quiet_vols)
    ascent_vols = vols[quiet_end:fhi + 1]
    pole_vol_avg = (_mean(ascent_vols) if ascent_vols else _mean(vols[psi:fhi + 1])) or 0.0
    base["flagpole_vol_ratio"] = (
        round(pole_vol_avg / quiet_vol_avg, 3) if quiet_vol_avg else None
    )
    base["volume_dryup_ratio"] = (
        round((_mean(vols[-5:]) or 0.0) / pole_vol_avg, 3) if pole_vol_avg else None
    )
    tight = _mean(
        [(highs[i] - lows[i]) / closes[i] * 100.0 for i in range(n)[-10:] if closes[i]]
    )
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    # --- 조용한 출발(보고용 소프트 신호 — 게이트 아님): 조용한 베이스 구간 변동폭 ---
    if quiet_highs and quiet_lows and min(quiet_lows) > 0:
        pre_gain = (max(quiet_highs) - min(quiet_lows)) / min(quiet_lows) * 100.0
        base["pre_pole_gain_pct"] = round(pre_gain, 2)

    # --- 하드 게이트 3개 판정 (조용·깃대거래량·dryup 는 소프트, 게이트 아님) ---
    cond_gain = fp["flagpole_gain_pct"] >= p["min_flagpole_gain"]
    cond_flag_min = flag_len >= p["min_flag_days"]
    cond_flag_max = flag_len <= p["max_flag_days"]
    cond_flag_depth = flag_depth <= p["max_flag_depth"]

    if not cond_gain:
        base["reason"] = "pole_gain_too_small"
    elif not cond_flag_min:
        base["reason"] = "flag_too_short"
    elif not cond_flag_max:
        base["reason"] = "flag_too_long"
    elif not cond_flag_depth:
        base["reason"] = "flag_too_deep"
    else:
        base["pattern_detected"] = True

    # --- 피벗·상태 ---
    last_close = closes[-1]
    last_vol = vols[-1] if vols else 0.0
    base["pct_to_pivot"] = round((flag_high - last_close) / flag_high * 100.0, 2) if flag_high > 0 else None
    if last_close > flag_high and pole_vol_avg and last_vol >= pole_vol_avg * p["breakout_vol_mult"]:
        base["status"] = "breakout"
    elif flag_depth > p["max_flag_depth"] or last_close < flag_low:
        base["status"] = "failed"
    elif (
        base["pct_to_pivot"] is not None
        and 0 <= base["pct_to_pivot"] <= p["near_pivot_pct"]
        and (base["volume_dryup_ratio"] if base["volume_dryup_ratio"] is not None else 9.9) <= 1.0
    ):
        base["status"] = "actionable"
    else:
        base["status"] = "forming"
    base["entry_ready"] = bool(
        base["pattern_detected"] and base["status"] in ("breakout", "actionable")
    )
    return base
