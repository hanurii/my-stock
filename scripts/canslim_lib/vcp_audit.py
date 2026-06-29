"""VCP 책 충실도 감사 (순수 부품 + 데이터 로더).

검출기(evaluate_vcp)가 미너비니 책 VCP 규칙을 얼마나 충실히 구현하는지 숫자로
렌더링한다. 모든 거래량 판정은 거래량 50일 이동평균 기준(책 정의).
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
"""
from __future__ import annotations

from canslim_lib.vcp import zigzag, find_contractions, evaluate_vcp, DEFAULT_PARAMS  # noqa: E402


def volume_ma(volumes: list[float], window: int = 50) -> list[float]:
    """거래량 trailing 이동평균. 초반(창 미만)은 가용분 평균(부분창)."""
    out: list[float] = []
    for i in range(len(volumes)):
        lo = max(0, i - window + 1)
        seg = volumes[lo:i + 1]
        out.append(sum(seg) / len(seg) if seg else 0.0)
    return out


def audit_prior_advance(closes: list[float], b0: int, lookback: int = 60) -> dict:
    """베이스 시작 직전 lookback 내 최저 종가 → 베이스시작 상승%·기간."""
    lo_i = max(0, b0 - lookback)
    window = closes[lo_i:b0 + 1]
    if not window:
        return {"value_pct": None, "days": None, "low_price": None}
    low = min(window)
    low_idx = lo_i + window.index(low)
    adv = (closes[b0] - low) / low * 100.0 if low else None
    return {
        "value_pct": round(adv, 2) if adv is not None else None,
        "days": b0 - low_idx,
        "low_price": round(low, 2),
    }


def audit_contractions(base_closes: list[float], zigzag_pct: float, mono_tol: float) -> dict:
    """각 수축의 깊이(%), 총 수축 개수, 축소 추세 여부, 스윙 정보."""
    swings = zigzag(base_closes, zigzag_pct)
    depths = [round(d, 2) for d in find_contractions(swings)]
    T = len(depths)
    shrinking = all(depths[i] <= depths[i - 1] * mono_tol for i in range(1, T)) if T >= 2 else False
    return {"depths": depths, "count": T, "shrinking": shrinking, "swings": swings}


def _seg_mean(xs: list[float]) -> float | None:
    """리스트 평균 (None 제외)."""
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def audit_contraction_volumes(base_vols, base_ma50, swings, mono_tol) -> dict:
    """각 (고→다음저) 수축 구간의 평균거래량 / 그 구간 평균ma50 (%)."""
    per = []
    for a, b in zip(swings, swings[1:]):
        if a[2] == "high" and b[2] == "low":
            i, j = a[0], b[0]
            v = _seg_mean(base_vols[i:j + 1])
            m = _seg_mean(base_ma50[i:j + 1])
            pct = round(v / m * 100.0, 2) if (v is not None and m) else None
            per.append({"vol_vs_ma50_pct": pct})
    vals = [p["vol_vs_ma50_pct"] for p in per if p["vol_vs_ma50_pct"] is not None]
    decreasing = all(vals[i] <= vals[i - 1] for i in range(1, len(vals))) if len(vals) >= 2 else False
    last_below = (vals[-1] < 100.0) if vals else False
    return {"per": per, "decreasing": decreasing, "last_below_ma50": last_below}


def audit_dry_point(base_vols, base_ma50, base_dates, right_frac: float) -> dict:
    """베이스 우측(right_frac 비율) 구간에서 min(거래량/ma50)와 그 날짜."""
    n = len(base_vols)
    start = max(0, int(n * (1 - right_frac)))
    best_pct, best_date = None, None
    for k in range(start, n):
        m = base_ma50[k]
        if not m:
            continue
        pct = base_vols[k] / m * 100.0
        if best_pct is None or pct < best_pct:
            best_pct, best_date = pct, base_dates[k] if k < len(base_dates) else None
    return {"min_vol_vs_ma50_pct": round(best_pct, 2) if best_pct is not None else None,
            "date": best_date}


def audit_breakout(series, pivot, b1, ma50, params) -> dict:
    """b1 이후 종가>피벗인 날들에 대한 돌파 감사.

    Returns:
        pivot: 피벗 가격
        detector_flags: 현 검출기 규칙(종가>피벗 AND 거래량≥base_vol_avg×breakout_vol)인 날짜 목록
        clean_candidates: 책 정의 클린 돌파 날짜·지표 목록
        pass: clean_candidates 비어있지 않음
    """
    closes = series["closes"]; opens = series["opens"]; vols = series["volumes"]; dates = series["dates"]
    n = len(closes)
    if pivot is None:
        return {"pivot": None, "detector_flags": [], "clean_candidates": [], "pass": False}
    cap = params.get("base_vol_cap", 50)
    base_vols = vols[max(0, b1 - cap + 1):b1 + 1]
    base_vol_avg = (sum(base_vols) / len(base_vols)) if base_vols else 0.0
    bv = params.get("breakout_vol", 1.4); near = params.get("near", 5.0)
    detector_flags, clean = [], []
    for i in range(b1 + 1, n):
        if closes[i] <= pivot:
            continue
        m = ma50[i] if i < len(ma50) and ma50[i] else None
        vol_vs = round(vols[i] / m * 100.0, 2) if m else None
        up = closes[i] > opens[i]
        ext = round((closes[i] - pivot) / pivot * 100.0, 2)
        first = closes[i - 1] <= pivot if i > 0 else True
        rec = {"date": dates[i], "vol_vs_ma50_pct": vol_vs, "up_candle": up,
               "extension_pct": ext, "first_cross": first}
        if base_vol_avg and vols[i] >= base_vol_avg * bv:
            detector_flags.append(dates[i])
        if first and up and (vol_vs is not None and vol_vs >= bv * 100.0) and ext <= near:
            clean.append(rec)
    return {"pivot": round(pivot, 2), "detector_flags": detector_flags,
            "clean_candidates": clean, "pass": len(clean) > 0}


def audit_item(series, b0, b1, params, meta) -> dict:
    """한 종목의 VCP 책 충실도 성적표 (5개 축 종합).

    evaluate_vcp 를 재사용해 검출기 평결 + 피벗을 가져오고,
    나머지 축은 Task 1·2 부품으로 직접 계산한다.
    """
    closes = series["closes"]; vols = series["volumes"]; dates = series["dates"]
    ma50 = volume_ma(vols, params.get("vol_ma_window", 50))
    base_closes = closes[b0:b1 + 1]
    base_vols = vols[b0:b1 + 1]; base_ma50 = ma50[b0:b1 + 1]; base_dates = dates[b0:b1 + 1]

    adv = audit_prior_advance(closes, b0, params.get("prior_lookback", 60))
    con = audit_contractions(base_closes, params.get("zigzag_pct", 8.0), params.get("mono_tol", 1.15))
    cvol = audit_contraction_volumes(base_vols, base_ma50, con["swings"], params.get("mono_tol", 1.15))
    dry = audit_dry_point(base_vols, base_ma50, base_dates, params.get("right_frac", 0.34))

    # 검출기 평결 + 피벗 (기존 evaluate_vcp 재사용, b1 기준)
    ev_params = {k: params.get(k, DEFAULT_PARAMS[k]) for k in
                 ("lookback_days", "zigzag_pct", "max_final_depth", "breakout_vol_mult", "near_pivot_pct")}
    sub = {k: series[k][:b1 + 1] for k in ("dates", "closes", "highs", "lows", "volumes", "opens") if series.get(k)}
    ev = evaluate_vcp(sub, ev_params)
    bo = audit_breakout(series, ev.get("pivot_price"), b1, ma50, params)

    axes = {
        "prior_advance": {**adv, "pass": (adv["value_pct"] is not None and adv["value_pct"] >= params.get("min_advance", 25.0))},
        "contractions": {"depths": con["depths"], "count": con["count"], "shrinking": con["shrinking"],
                         "pass": (2 <= con["count"] <= 6 and con["shrinking"])},
        "contraction_volumes": {**cvol, "pass": (cvol["decreasing"] and cvol["last_below_ma50"])},
        "dry_point": {**dry, "pass": (dry["min_vol_vs_ma50_pct"] is not None
                                      and dry["min_vol_vs_ma50_pct"] <= params.get("dry_max", 0.7) * 100.0)},
        "breakout": bo,
    }
    return {
        "code": meta.get("code"), "name": meta.get("name"), "source": meta.get("source"),
        "base_start": dates[b0] if b0 < len(dates) else None,
        "base_end": dates[b1] if b1 < len(dates) else None,
        "detector_verdict": {"vcp_detected": ev.get("vcp_detected"), "status_at_b1": ev.get("status")},
        "axes": axes,
    }
