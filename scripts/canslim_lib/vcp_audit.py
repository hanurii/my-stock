"""VCP 책 충실도 감사 (순수 부품 + 데이터 로더).

검출기(evaluate_vcp)가 미너비니 책 VCP 규칙을 얼마나 충실히 구현하는지 숫자로
렌더링한다. 모든 거래량 판정은 거래량 50일 이동평균 기준(책 정의).
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
"""
from __future__ import annotations

from canslim_lib.vcp import zigzag, find_contractions  # noqa: E402


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
