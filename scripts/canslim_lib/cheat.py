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
