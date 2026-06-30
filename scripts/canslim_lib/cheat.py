"""미너비니 3C(Cup-Completion Cheat) 평가 부품 (순수 함수).

개념(컵·치트 선반·하단/중단 위치·거래량 마름)=마크 미너비니/오닐. 구체 수치·
계산규칙=이 프로젝트의 공학적 번역(원전 아님).
정의·근거: docs/superpowers/specs/2026-06-30-find-3c-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 250,
    "min_total_days": 40,
    "min_cup_depth": 12.0,
    "max_cup_depth": 50.0,
    "min_cup_days": 35,
    "min_shelf_pullback": 3.0,
    "min_shelf_days": 5,
    "max_shelf_days": 25,
    "max_shelf_depth": 12.0,
    "max_shelf_position": 66.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
}


def _sentinel() -> dict:
    return {"cup_low_idx": 0, "cup_low": 0.0, "left_rim_idx": 0, "left_rim_high": 0.0,
            "shelf_high_idx": 0, "shelf_high": 0.0, "cup_depth_pct": 0.0, "cup_base_days": 0}


def find_cheat_shelf(highs: list[float], lows: list[float],
                     min_shelf_pullback: float | None = None) -> dict:
    """컵 바닥을 먼저 앵커(전체 최저점)하고, 그 이전 최고가=왼쪽 테두리,
    바닥 이후(우측)에서 '뒤에 눌림이 확인된 최고 고가'=선반 고점(피벗)을 찾는다.

    치트 선반은 옛 고점(왼쪽 테두리)보다 낮으므로, 파워플레이처럼 '구간 전체 최고
    고가'를 피벗으로 잡으면 안 된다(왼쪽 테두리를 잡아버림). 그래서 바닥 기준 앵커.
    """
    if not highs or not lows:
        return _sentinel()
    n = len(highs)
    cup_low_idx = min(range(n), key=lambda i: lows[i])
    cup_low = lows[cup_low_idx]
    left_rim_idx = max(range(0, cup_low_idx + 1), key=lambda i: highs[i])
    left_rim_high = highs[left_rim_idx]

    right = range(cup_low_idx + 1, n)
    if min_shelf_pullback is None:
        cand = list(right[:-1]) if len(right) > 1 else []
    else:
        pb = min_shelf_pullback / 100.0
        cand = [i for i in right
                if i < n - 1 and min(lows[i + 1:]) <= highs[i] * (1 - pb)]
    if cand:
        shelf_high_idx = max(cand, key=lambda i: highs[i])
    elif len(right) > 0:
        shelf_high_idx = max(right, key=lambda i: highs[i])
    else:
        shelf_high_idx = cup_low_idx
    shelf_high = highs[shelf_high_idx]

    cup_depth_pct = (left_rim_high - cup_low) / left_rim_high * 100.0 if left_rim_high > 0 else 0.0
    cup_base_days = (n - 1) - left_rim_idx
    return {"cup_low_idx": cup_low_idx, "cup_low": cup_low,
            "left_rim_idx": left_rim_idx, "left_rim_high": left_rim_high,
            "shelf_high_idx": shelf_high_idx, "shelf_high": shelf_high,
            "cup_depth_pct": cup_depth_pct, "cup_base_days": cup_base_days}


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def evaluate_cheat(series: dict, params: dict | None = None) -> dict:
    """3C(Cup-Completion Cheat) 종합 판정."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    lb = p["lookback_days"]
    closes = (series.get("closes") or [])[-lb:]
    highs = (series.get("highs") or [])[-lb:]
    lows = (series.get("lows") or [])[-lb:]
    vols = (series.get("volumes") or [])[-lb:]
    dates = (series.get("dates") or [])[-lb:]

    base: dict = {
        "pattern_detected": False, "entry_ready": False,
        "cup_depth_pct": None, "cup_base_days": None,
        "shelf_position_pct": None, "shelf_depth_pct": None, "shelf_length_days": None,
        "pivot_price": None, "pct_to_pivot": None, "volume_dryup_ratio": None,
        "rally_vol_ratio": None, "tightness_pct": None,
        "status": "forming", "reason": None,
        "left_rim_date": None, "cup_low_date": None, "shelf_high_date": None,
    }
    n = len(closes)
    if n == 0:
        base["reason"] = "no_data"
        return base
    if n < p["min_total_days"]:
        base["reason"] = "base_too_short"
        return base

    cs = find_cheat_shelf(highs, lows, p["min_shelf_pullback"])
    lri, cli, shi = cs["left_rim_idx"], cs["cup_low_idx"], cs["shelf_high_idx"]
    left_rim, cup_low, shelf_high = cs["left_rim_high"], cs["cup_low"], cs["shelf_high"]
    base["cup_depth_pct"] = round(cs["cup_depth_pct"], 2)
    base["cup_base_days"] = cs["cup_base_days"]
    base["left_rim_date"] = dates[lri] if lri < len(dates) else None
    base["cup_low_date"] = dates[cli] if cli < len(dates) else None
    base["shelf_high_date"] = dates[shi] if shi < len(dates) else None
    base["pivot_price"] = round(shelf_high, 2)

    # --- 선반 지표 ---
    shelf_lows = lows[shi:]
    shelf_low = min(shelf_lows) if shelf_lows else shelf_high
    shelf_len = (n - 1) - shi
    shelf_depth = (shelf_high - shelf_low) / shelf_high * 100.0 if shelf_high > 0 else 0.0
    base["shelf_length_days"] = shelf_len
    base["shelf_depth_pct"] = round(shelf_depth, 2)

    # --- 선반 위치(컵 깊이의 몇 % 높이) ---
    denom = left_rim - cup_low
    shelf_position = (shelf_high - cup_low) / denom * 100.0 if denom > 0 else 0.0
    base["shelf_position_pct"] = round(shelf_position, 2)

    # --- 거래량 구간 ---
    rally_vols = vols[cli:shi + 1]
    rally_vol_avg = (_mean(rally_vols) if rally_vols else _mean(vols[lri:shi + 1])) or 0.0
    left_vol_avg = _mean(vols[lri:cli + 1])
    base["rally_vol_ratio"] = round(rally_vol_avg / left_vol_avg, 3) if left_vol_avg else None
    base["volume_dryup_ratio"] = (
        round((_mean(vols[-5:]) or 0.0) / rally_vol_avg, 3) if rally_vol_avg else None
    )
    tight = _mean(
        [(highs[i] - lows[i]) / closes[i] * 100.0 for i in range(n)[-10:] if closes[i]]
    )
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    # --- 게이트 판정(첫 불충족이 reason) ---
    depth = cs["cup_depth_pct"]
    cond_cup_min_depth = depth >= p["min_cup_depth"]
    cond_cup_max_depth = depth <= p["max_cup_depth"]
    cond_cup_days = cs["cup_base_days"] >= p["min_cup_days"]
    cond_shelf_min = shelf_len >= p["min_shelf_days"]
    cond_shelf_max = shelf_len <= p["max_shelf_days"]
    cond_shelf_depth = shelf_depth <= p["max_shelf_depth"]
    cond_shelf_pos = shelf_position <= p["max_shelf_position"]
    cond_dryup = base["volume_dryup_ratio"] is not None and base["volume_dryup_ratio"] <= 1.0

    if not cond_cup_min_depth:
        base["reason"] = "cup_too_shallow"
    elif not cond_cup_max_depth:
        base["reason"] = "cup_too_deep"
    elif not cond_cup_days:
        base["reason"] = "cup_too_short"
    elif not cond_shelf_min:
        base["reason"] = "shelf_too_short"
    elif not cond_shelf_max:
        base["reason"] = "shelf_too_long"
    elif not cond_shelf_depth:
        base["reason"] = "shelf_too_loose"
    elif not cond_shelf_pos:
        base["reason"] = "shelf_too_high_in_cup"
    elif not cond_dryup:
        base["reason"] = "volume_not_drying"
    else:
        base["pattern_detected"] = True

    # --- 피벗·상태(파워플레이와 동일 규칙) ---
    last_close = closes[-1]
    last_vol = vols[-1] if vols else 0.0
    base["pct_to_pivot"] = round((shelf_high - last_close) / shelf_high * 100.0, 2) if shelf_high > 0 else None
    if last_close > shelf_high and rally_vol_avg and last_vol >= rally_vol_avg * p["breakout_vol_mult"]:
        base["status"] = "breakout"
    elif shelf_depth > p["max_shelf_depth"] or last_close < shelf_low:
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
