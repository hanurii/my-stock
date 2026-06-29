"""미너비니 VCP(변동성 수축 패턴) 평가 부품 (순수 함수).

개념(VCP·피벗·수축·거래량 마름)=마크 미너비니. 구체 수치·계산규칙=이 프로젝트의
공학적 번역(원전 아님). 정의·근거: docs/superpowers/specs/2026-06-29-find-vcp-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "zigzag_pct": 8.0,
    "min_base_days": 10,
    "contraction_tol": 1.15,
    "max_final_depth": 10.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
    "base_vol_cap": 50,
}


def zigzag(values: list[float], pct: float) -> list[tuple[int, float, str]]:
    """퍼센트-역행 ZigZag. 교대 피벗 (index, price, kind) 리스트.

    시작점은 첫 확정 레그 방향에 따라 high/low 로 포함되고, 끝에는 진행 중인
    마지막 극점을 닫는 피벗으로 추가한다.
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [(0, values[0], "high")]
    thr = pct / 100.0
    pivots: list[tuple[int, float, str]] = []
    ext_idx, ext_val = 0, values[0]
    direction = 0  # 0 미정, 1 상승레그(ext=고점후보), -1 하락레그(ext=저점후보)
    for i in range(1, n):
        v = values[i]
        if direction == 0:
            if v >= ext_val * (1 + thr):
                pivots.append((0, values[0], "low"))
                direction, ext_idx, ext_val = 1, i, v
            elif v <= ext_val * (1 - thr):
                pivots.append((0, values[0], "high"))
                direction, ext_idx, ext_val = -1, i, v
            elif v > ext_val:
                ext_idx, ext_val = i, v
        elif direction == 1:
            if v > ext_val:
                ext_idx, ext_val = i, v
            elif v <= ext_val * (1 - thr):
                pivots.append((ext_idx, ext_val, "high"))
                direction, ext_idx, ext_val = -1, i, v
        else:  # direction == -1
            if v < ext_val:
                ext_idx, ext_val = i, v
            elif v >= ext_val * (1 + thr):
                pivots.append((ext_idx, ext_val, "low"))
                direction, ext_idx, ext_val = 1, i, v
    closing = "high" if direction == 1 else "low"
    pivots.append((ext_idx, ext_val, closing))
    return pivots


def find_contractions(pivots: list[tuple[int, float, str]]) -> list[float]:
    """인접한 (고점 → 바로 다음 저점) 쌍의 되돌림 깊이%를 시간순으로."""
    depths: list[float] = []
    for a, b in zip(pivots, pivots[1:]):
        if a[2] == "high" and b[2] == "low":
            high, low = a[1], b[1]
            if high > 0:
                depths.append((high - low) / high * 100.0)
    return depths


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def evaluate_vcp(series: dict, params: dict | None = None) -> dict:
    """VCP 종합 판정.

    series 키: dates, closes, highs, lows, volumes.
    반환 dict 키: vcp_detected, num_contractions, contractions,
    base_length_days, base_depth_pct, pivot_price, pct_to_pivot,
    volume_dryup_ratio, tightness_pct, status, swings, reason.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    closes = (series.get("closes") or [])[-p["lookback_days"]:]
    highs = (series.get("highs") or [])[-p["lookback_days"]:]
    lows = (series.get("lows") or [])[-p["lookback_days"]:]
    vols = (series.get("volumes") or [])[-p["lookback_days"]:]
    dates = (series.get("dates") or [])[-p["lookback_days"]:]

    base: dict = {
        "vcp_detected": False, "num_contractions": 0, "contractions": [],
        "base_length_days": 0, "base_depth_pct": None, "pivot_price": None,
        "pct_to_pivot": None, "volume_dryup_ratio": None, "tightness_pct": None,
        "status": "forming", "swings": [], "reason": None,
    }
    if len(closes) < p["min_base_days"]:
        base["reason"] = "no_data" if not closes else "base_too_short"
        return base

    # 베이스 시작 = lookback 내 최고 종가 지점
    start = max(range(len(closes)), key=lambda i: closes[i])
    bc = closes[start:]
    bh = highs[start:]
    bl = lows[start:]
    bv = vols[start:]
    bd = dates[start:]
    base["base_length_days"] = len(bc)
    if len(bc) < p["min_base_days"]:
        base["reason"] = "base_too_short"
        return base

    swings = zigzag(bc, p["zigzag_pct"])
    base["swings"] = [
        {"date": bd[i] if i < len(bd) else None, "price": round(pr, 2), "kind": k}
        for i, pr, k in swings
    ]
    contractions = find_contractions(swings)
    base["contractions"] = [round(d, 2) for d in contractions]
    base["num_contractions"] = len(contractions)

    cap = p["base_vol_cap"]
    base_vol_avg = _mean(bv[-cap:] if len(bv) > cap else bv) or 0.0
    last_close = bc[-1]

    # 피벗 = 마지막 확정된 "high" 스윙 가격
    # swings[-1]은 진행 중인(미확정) 클로징 피벗이므로 제외; 없으면 클로징 피벗 사용
    confirmed_highs = [pr for _, pr, k in swings[:-1] if k == "high"]
    if not confirmed_highs:
        confirmed_highs = [pr for _, pr, k in swings[-1:] if k == "high"]
    pivot = confirmed_highs[-1] if confirmed_highs else None
    base["pivot_price"] = round(pivot, 2) if pivot is not None else None
    if pivot is not None:
        base["pct_to_pivot"] = round((pivot - last_close) / pivot * 100.0, 2)

    base["volume_dryup_ratio"] = (
        round((_mean(bv[-5:]) or 0.0) / base_vol_avg, 3) if base_vol_avg else None
    )
    tight = _mean(
        [(bh[i] - bl[i]) / bc[i] * 100.0 for i in range(len(bc))[-10:] if bc[i]]
    )
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    # VCP 4조건
    T = len(contractions)
    cond_count = 2 <= T <= 6
    cond_mono = (
        all(contractions[i] <= contractions[i - 1] * p["contraction_tol"]
            for i in range(1, T))
        if T >= 2 else False
    )
    third = max(1, len(bv) // 3)
    early_vol = _mean(bv[:third]) or 0.0
    late_vol = _mean(bv[-third:]) or 0.0
    cond_volcontract = late_vol < early_vol
    cond_final_tight = (contractions[-1] <= p["max_final_depth"]) if T >= 1 else False
    base["vcp_detected"] = bool(cond_count and cond_mono and cond_volcontract and cond_final_tight)
    if base["vcp_detected"]:
        base["base_depth_pct"] = round(max(contractions), 2)

    # 상태 판정
    last_vol = bv[-1] if bv else 0.0
    base_low = min(bl) if bl else last_close
    mono_violated = T >= 2 and contractions[-1] > contractions[-2] * p["contraction_tol"]
    if pivot is not None and last_close > pivot and base_vol_avg and last_vol >= base_vol_avg * p["breakout_vol_mult"]:
        base["status"] = "breakout"
    elif mono_violated or last_close < base_low:
        base["status"] = "failed"
    elif (
        base["pct_to_pivot"] is not None
        and 0 <= base["pct_to_pivot"] <= p["near_pivot_pct"]
        and (base["volume_dryup_ratio"] or 9.9) <= 1.0
    ):
        base["status"] = "actionable"
    else:
        base["status"] = "forming"
    return base
