"""CAN SLIM 점수 계산.

원전 7기준 모두 동일 가중치로 통과 개수에 따라 0~100점 환산.
+ 가속/모멘텀 보너스 약간.
"""

from __future__ import annotations

from typing import TypedDict


class CriterionResult(TypedDict):
    pass_: bool  # 'pass' is a Python keyword
    value: str
    detail: str


def compute_score(results: dict[str, tuple[bool, str, str]]) -> tuple[int, int, str]:
    """7기준 결과로 점수 계산.

    Args:
      results: {'C': (passed, value, detail), 'A': ..., ...}

    Returns:
      (score 0-100, passed_count 0-7, grade A/B/C/D)
    """
    passed_count = sum(1 for r in results.values() if r[0])

    # 100점 = 7기준 모두 통과. 각 기준 ~14.3점.
    base = passed_count * (100 / 7)

    # M(시장)은 가중치 부여 — 시장이 하락이면 다른 기준 통과해도 매수 위험
    # → M 통과 시 +5, 미통과 시 -5 (그래도 0~100 범위 유지)
    if "M" in results:
        if results["M"][0]:
            base = min(100, base + 5)
        else:
            base = max(0, base - 5)

    score = round(base)

    # 등급
    if passed_count >= 6:
        grade = "A"
    elif passed_count >= 5:
        grade = "B"
    elif passed_count >= 3:
        grade = "C"
    else:
        grade = "D"

    return score, passed_count, grade
