"""VCP 책 충실도 감사 (순수 부품 + 데이터 로더).

검출기(evaluate_vcp)가 미너비니 책 VCP 규칙을 얼마나 충실히 구현하는지 숫자로
렌더링한다. 모든 거래량 판정은 거래량 50일 이동평균 기준(책 정의).
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
"""
from __future__ import annotations


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
