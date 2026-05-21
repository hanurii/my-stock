"""CAN SLIM 'S' 원칙 — v2 점수 체계 (60점 만점).

설계 (IMPL_canslim_s_page.md v2):
- 입력 = C 통과 종목 전체.
- 60점 = 주주가치 50점 + 부채비율 10점.
- 컷오프 / 통과·미통과 폐기. 모든 종목이 점수와 함께 노출.

주주가치 (50점):
- 기본 25점에서 출발.
- 가점:
  - 자사주 소각 (treasury_cancellation_years): 1년 +5 / 2년 +10 / 3년+ +15
  - 연속 배당 (consecutive_dividend_years): 1년 +2 / 2~3년 +5 / 4년+ +10
- 감점:
  - 희석 이벤트 (dilutive_event_count, 5년): 건당 -5
- 최종: clamp(0, 50)

부채비율 (10점):
- 일반 산업: ≤50%→10 / ≤100%→7 / ≤150%→4 / ≤200%→2 / >200%→0
- 금융업 (KSIC 64·65·66 또는 이름 패턴): 5점 고정

데이터 소스:
- shareholder-returns.json (`scripts/fetch-shareholder-returns.ts` 산출)
- DART fnlttMultiAcnt (bulk 부채총계 / 자본총계)
- 종목명 이름 패턴 (금융업 자동 분류)
"""

from __future__ import annotations

import re
from typing import Any

# growth/page.tsx 와 동일한 DILUTIVE_TYPES 집합 (기존 주주를 일방적으로 희석)
DILUTIVE_TYPES = {
    "전환권행사",
    "신주인수권행사",
    "유상증자(제3자배정)",
    "주식매수선택권행사",
    "상환권행사",
}

# 금융업 종목명 패턴 (KSIC 64·65·66)
FINANCIAL_NAME_PATTERNS = re.compile(
    r"(은행|보험|증권|카드|캐피탈|금융지주|자산운용|신탁|선물|투자증권|저축은행|"
    r"손해보험|생명보험|화재|상호저축|할부금융|리스|벤처투자|자산신탁|투자신탁)"
)

# KSIC prefix (DART company.json induty_code) — 있을 때만 사용
FINANCIAL_KSIC_PREFIXES = ("64", "65", "66")


def is_financial_industry(*, induty_code: str | None = None, name: str | None = None) -> bool:
    """KSIC prefix 우선, 없으면 종목명 패턴으로 금융업 판정."""
    if induty_code and len(induty_code) >= 2 and induty_code[:2] in FINANCIAL_KSIC_PREFIXES:
        return True
    if name and FINANCIAL_NAME_PATTERNS.search(name):
        return True
    return False


# ── shareholder-returns 원본 → 지표 계산 ──

def compute_shareholder_metrics(
    sr_entry: dict[str, Any] | None,
    current_year: int,
) -> dict[str, int]:
    """shareholder-returns.json 의 한 종목 entry → 점수 계산용 지표.

    Returns:
      {
        "treasury_cancellation_years": int,  # cancelled > 0 인 연도 수
        "consecutive_dividend_years": int,   # 현재 연도 이전 연속 배당 연도 수
        "dilutive_event_count": int,         # 최근 5년 DILUTIVE_TYPES 매칭 건수
        "has_data": bool,                    # sr_entry 존재 여부
      }
    """
    if sr_entry is None:
        return {
            "treasury_cancellation_years": 0,
            "consecutive_dividend_years": 0,
            "dilutive_event_count": 0,
            "has_data": False,
        }

    # 자사주 소각 연도 수
    treasury_stock = sr_entry.get("treasury_stock") or []
    cancellation_years = sum(1 for t in treasury_stock if (t.get("cancelled") or 0) > 0)

    # 연속 배당: 현재 연도 이전부터 역순으로 dps>0 인 연도 수
    dividends = sr_entry.get("dividends") or []
    valid_divs = sorted(
        [d for d in dividends if (d.get("year") or 0) < current_year],
        key=lambda d: d.get("year") or 0,
        reverse=True,
    )
    consecutive_div_years = 0
    for d in valid_divs:
        dps = d.get("dps")
        if dps is not None and dps > 0:
            consecutive_div_years += 1
        else:
            break

    # 최근 5년 희석 이벤트
    cutoff_year = current_year - 5
    capital_changes = sr_entry.get("capital_changes") or []
    dilutive_count = sum(
        1
        for c in capital_changes
        if (c.get("type") or "") in DILUTIVE_TYPES
        and (c.get("year") or 0) >= cutoff_year
    )

    return {
        "treasury_cancellation_years": cancellation_years,
        "consecutive_dividend_years": consecutive_div_years,
        "dilutive_event_count": dilutive_count,
        "has_data": True,
    }


# ── 점수 함수 ──

def score_shareholder(metrics: dict[str, int]) -> dict[str, Any]:
    """주주가치 점수 (50점, 기본 25). 가점/감점 details 포함."""
    base = 25
    details: list[dict[str, Any]] = []

    # 자사주 소각 가점
    cy = metrics["treasury_cancellation_years"]
    if cy >= 3:
        cancel_bonus = 15
        cancel_basis = f"{cy}년 소각 실적 (3년 이상)"
    elif cy == 2:
        cancel_bonus = 10
        cancel_basis = "2년 소각 실적"
    elif cy == 1:
        cancel_bonus = 5
        cancel_basis = "1년 소각 실적"
    else:
        cancel_bonus = 0
        cancel_basis = "소각 실적 없음"
    details.append({"item": "자사주 소각", "basis": cancel_basis, "score": cancel_bonus})

    # 연속 배당 가점
    dy = metrics["consecutive_dividend_years"]
    if dy >= 4:
        div_bonus = 10
        div_basis = f"{dy}년 연속 배당 (4년 이상)"
    elif dy >= 2:
        div_bonus = 5
        div_basis = f"{dy}년 연속 배당"
    elif dy == 1:
        div_bonus = 2
        div_basis = "1년 배당 (단년)"
    else:
        div_bonus = 0
        div_basis = "배당 없음"
    details.append({"item": "연속 배당", "basis": div_basis, "score": div_bonus})

    # 희석 감점
    dc = metrics["dilutive_event_count"]
    dilution_penalty = -5 * dc
    dilution_basis = (
        f"희석 이벤트 {dc}건 × -5점" if dc > 0 else "희석 이력 없음"
    )
    details.append({"item": "지분 희석", "basis": dilution_basis, "score": dilution_penalty})

    # 데이터 없음 표시
    if not metrics.get("has_data"):
        details.append({
            "item": "데이터 없음",
            "basis": "shareholder-returns.json 미수록 → 기본값 25점",
            "score": 0,
        })

    raw = base + cancel_bonus + div_bonus + dilution_penalty
    final = max(0, min(50, raw))

    return {
        "score": final,
        "base": base,
        "details": details,
        "metrics": metrics,
    }


def score_debt(
    debt_ratio: float | None,
    is_financial: bool,
) -> dict[str, Any]:
    """부채비율 점수 (10점). 금융업은 5점 고정."""
    if is_financial:
        return {
            "score": 5,
            "basis": "금융기관 (KSIC 64·65·66) — 5점 고정",
            "debt_ratio": debt_ratio,
        }
    if debt_ratio is None:
        return {
            "score": 0,
            "basis": "부채비율 데이터 없음",
            "debt_ratio": None,
        }
    if debt_ratio <= 50:
        s, basis = 10, "≤ 50% (매우 안전)"
    elif debt_ratio <= 100:
        s, basis = 7, "≤ 100% (안정)"
    elif debt_ratio <= 150:
        s, basis = 4, "≤ 150% (보통)"
    elif debt_ratio <= 200:
        s, basis = 2, "≤ 200% (높음)"
    else:
        s, basis = 0, "> 200% (과도)"
    return {
        "score": s,
        "basis": f"{round(debt_ratio, 1)}% — {basis}",
        "debt_ratio": debt_ratio,
    }


def score_s_v2(
    *,
    name: str,
    induty_code: str | None,
    sr_entry: dict[str, Any] | None,
    debt_ratio: float | None,
    current_year: int,
) -> dict[str, Any]:
    """S 점수 계산 통합 함수.

    Returns:
      {
        "s_score": int,                   # 0~60
        "shareholder_score": int,         # 0~50
        "debt_score": int,                # 0~10
        "is_financial": bool,
        "shareholder_metrics": {...},
        "shareholder_details": [...],
        "debt_basis": str,
        "debt_ratio": float|None,
        "badges": list[str],
      }
    """
    metrics = compute_shareholder_metrics(sr_entry, current_year)
    sh = score_shareholder(metrics)

    financial = is_financial_industry(induty_code=induty_code, name=name)
    debt = score_debt(debt_ratio, financial)

    badges: list[str] = []
    if metrics["treasury_cancellation_years"] >= 2:
        badges.append("소각")
    if metrics["consecutive_dividend_years"] >= 3:
        badges.append("배당")
    if metrics["dilutive_event_count"] >= 3:
        badges.append("희석주의")
    if financial:
        badges.append("금융기관")
    if not metrics.get("has_data"):
        badges.append("주주환원 데이터 없음")

    return {
        "s_score": sh["score"] + debt["score"],
        "shareholder_score": sh["score"],
        "debt_score": debt["score"],
        "is_financial": financial,
        "shareholder_metrics": metrics,
        "shareholder_details": sh["details"],
        "debt_basis": debt["basis"],
        "debt_ratio": debt["debt_ratio"],
        "badges": badges,
    }
