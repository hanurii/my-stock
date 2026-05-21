"""CAN SLIM 'A' 원칙 (Annual Earnings) 평가 — v2 점수 체계.

문서 기준: research/oneil-model-book/IMPL_canslim_a_page.md (v2)

핵심 설계
---------
- 3개 트랙 (정통 A · 턴어라운드 · 신규상장) 각 50점 만점.
- "탈락/통과" 이분법 없음. 모든 종목이 점수를 받음.
- 트랙 분류 우선순위: 정통 A → 턴어라운드 → 신규상장 → 분류 불가.
- 마진은 점수에서 제외, 5단계 라벨로 별도 노출.
- 경기민감은 정보용 라벨만, 점수 영향 없음.

이전 버전과 호환
---------------
이전 함수 (evaluate_a_detailed, evaluate_turnaround_detailed,
evaluate_new_listing_detailed, compute_a_score) 는 제거됨.
새 엔트리: evaluate_a_v2.
"""

from __future__ import annotations

import math
from typing import Any


# ────────────────────────────────────────────────────────
# 상수 — 한국형 보정 컷오프 (문서 v2 기준)
# ────────────────────────────────────────────────────────

# 정통 A 트랙 — EPS 성장 강도 (3년 평균 YoY) 부분 점수 구간
EPS_GROWTH_FULL_PCT = 25.0   # 만점 (한국형 = 글로벌 = 25%)
EPS_GROWTH_MID_PCT = 15.0
EPS_GROWTH_LOW_PCT = 5.0

# 정통 A 트랙 — ROE 부분 점수 구간 (한국형 보정)
ROE_GLOBAL_PCT = 17.0    # 글로벌 만점
ROE_KOREAN_PCT = 12.0    # 한국형 만점 (KOSPI 평균 8.2% 감안)
ROE_FLOOR_PCT = 8.0      # 부분 점수 하한

# 마진 라벨 컷오프
MARGIN_VERY_HIGH = 20.0   # 매우높음 (한국 상위 5%)
MARGIN_HIGH = 15.0        # 높음 (한국 상위 10%)
MARGIN_MID = 10.0         # 중간 (한국 상위 30%)
MARGIN_LOW = 5.0          # 낮음 (한국 상위 50%)
# < 5.0 → 매우낮음

# 턴어라운드 트랙 — 입장 조건 (정통 + 예비)
TURNAROUND_RECOVERY_ORTHODOX_PCT = 5.0
TURNAROUND_RECOVERY_PRELIM_PCT = 3.0
TURNAROUND_SURGE_ORTHODOX_PCT = 50.0
TURNAROUND_SURGE_PRELIM_PCT = 30.0
TURNAROUND_TTM_ORTHODOX_RATIO = 0.90
TURNAROUND_TTM_PRELIM_RATIO = 0.80
# 분기 급증 강도 만점 (2분기 연속 ≥ +100%)
TURNAROUND_SURGE_FULL_PCT = 100.0

# 신규상장 트랙 — 입장 조건
NEW_LISTING_QUARTERLY_MIN_PCT = 25.0    # 분기 EPS·매출 YoY 최소
NEW_LISTING_EPS_HIGH_PCT = 50.0         # 부분 점수 중간 구간
NEW_LISTING_EPS_FULL_PCT = 100.0        # 만점
NEW_LISTING_SALES_FULL_PCT = 50.0
NEW_LISTING_MIN_HISTORY = 2             # 분기 history 최소 2개 (v2: 3 → 2)
NEW_LISTING_MAX_ANNUAL_DATA = 3         # 상장 < 3년 근사 (연간 데이터 < 3년)

# 안정성 지수 (신규상장 축 ④)
STABILITY_EXCELLENT_MAX = 30
STABILITY_MODERATE_MAX = 40

# KSIC 경기민감주 prefix (라벨용, 점수 영향 없음)
CYCLICAL_KSIC_PREFIXES = ("24", "20", "17", "22", "29")


# ────────────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────────────


def is_cyclical_industry(induty_code: str | None) -> bool:
    """KSIC 첫 2자리로 경기민감주 판별. NULL/짧은 코드는 False (자동 통과)."""
    if not induty_code or len(induty_code) < 2:
        return False
    return induty_code[:2] in CYCLICAL_KSIC_PREFIXES


def margin_label(margin: float | None) -> str:
    """세전 마진율 → 5단계 라벨 (점수 영향 없음, 정보용)."""
    if margin is None:
        return "데이터 없음"
    if margin >= MARGIN_VERY_HIGH:
        return "매우높음"
    if margin >= MARGIN_HIGH:
        return "높음"
    if margin >= MARGIN_MID:
        return "중간"
    if margin >= MARGIN_LOW:
        return "낮음"
    return "매우낮음"


def grade_label(score: int) -> str:
    """50점 만점 기준 등급 (세 트랙 공통)."""
    if score >= 40:
        return "최상"
    if score >= 30:
        return "상"
    if score >= 20:
        return "중"
    return "하"


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def compute_earnings_stability(quarterly_eps: list[float]) -> tuple[int | None, str]:
    """순이익 안정성 지수 (1~99, 낮을수록 안정). 신규상장 축 ④ 에서 사용."""
    if len(quarterly_eps) < 12:
        return None, f"분기 데이터 {len(quarterly_eps)}개 (12+ 필요)"

    xs = [float(i) for i in range(len(quarterly_eps))]
    slope, intercept = _linear_regression(xs, quarterly_eps)
    deviations = [abs(quarterly_eps[i] - (slope * i + intercept)) for i in range(len(quarterly_eps))]
    mean_dev = sum(deviations) / len(deviations)
    mean_abs_eps = sum(abs(e) for e in quarterly_eps) / len(quarterly_eps)
    if mean_abs_eps <= 0:
        return None, "전 분기 EPS = 0"

    dev_pct = (mean_dev / mean_abs_eps) * 100
    if dev_pct <= 0:
        return 1, "편차 0 (완전 일정)"
    score = max(1, min(99, int(round(20 * math.log10(dev_pct + 1)))))
    has_loss = any(e <= 0 for e in quarterly_eps)
    loss_count = sum(1 for e in quarterly_eps if e <= 0)
    detail = f"편차율 {dev_pct:.1f}%"
    if has_loss:
        detail += f" (적자 {loss_count}분기 포함)"
    return score, detail


# ────────────────────────────────────────────────────────
# 점수 산정 — 축별
# ────────────────────────────────────────────────────────


def _score_eps_consistency_orthodox(
    annual_eps: list[tuple[str, float]],
    growths: list[float],
) -> tuple[int, str]:
    """정통 A 축 ① — EPS 지속성 10점.

    - 3년 strict 단조 증가 (적자 0회) → 10
    - 5년 위기 1회 dip 면제 (6년 데이터 + 1 dip + 회복) → 9
    - 1회 dip + 회복 (3-4년 데이터) → 6
    - 2회 dip → 3
    """
    values = [v for _, v in annual_eps]
    if not values or any(v <= 0 for v in values):
        return 0, "흑자 데이터 부족"

    # 6년 데이터로 strict 단조 증가 또는 위기 1회 dip + 회복 검사
    if len(values) >= 6:
        recent_6 = values[-6:]
        if all(recent_6[i] > recent_6[i - 1] for i in range(1, len(recent_6))):
            return 10, "5년 strict 단조 증가"
        dip_indices = [i for i in range(1, len(recent_6)) if recent_6[i] < recent_6[i - 1]]
        if len(dip_indices) == 1:
            dip_i = dip_indices[0]
            if dip_i + 1 < len(recent_6) and recent_6[dip_i + 1] >= recent_6[dip_i - 1]:
                return 9, "5년 위기 1회 dip 면제"

    # 최근 3-4년 strict 단조 증가
    recent_window = values[-4:] if len(values) >= 4 else values[-3:]
    if len(recent_window) >= 3 and all(
        recent_window[i] > recent_window[i - 1] for i in range(1, len(recent_window))
    ):
        return 10, "3년 strict 단조 증가"

    # dip 횟수 카운트
    if growths:
        dip_count = sum(1 for g in growths if g <= 0)
        if dip_count == 1:
            return 6, "1회 dip + 회복"
        if dip_count == 2:
            return 3, "2회 dip"
        return 0, "다회 dip"

    return 0, "지속성 평가 불가"


def _score_eps_growth(avg_growth: float | None) -> tuple[int, str]:
    """정통 A 축 ② — EPS 성장 강도 25점 (3년 평균 YoY)."""
    if avg_growth is None:
        return 0, "데이터 부족"
    if avg_growth >= EPS_GROWTH_FULL_PCT:
        return 25, f"+{avg_growth:.1f}% (≥25%)"
    if avg_growth >= EPS_GROWTH_MID_PCT:
        return 18, f"+{avg_growth:.1f}% (15~25%)"
    if avg_growth >= EPS_GROWTH_LOW_PCT:
        return 10, f"+{avg_growth:.1f}% (5~15%)"
    if avg_growth >= 0:
        return 3, f"+{avg_growth:.1f}% (0~5%)"
    return 0, f"{avg_growth:.1f}% (<0%)"


def _score_profitability_roe(roe: float | None) -> tuple[int, str]:
    """수익성 축 — ROE 단독 15점 (세 트랙 공통 척도)."""
    if roe is None:
        return 3, "ROE 데이터 없음"
    if roe >= ROE_GLOBAL_PCT:
        return 15, f"ROE {roe:.1f}% (≥17% 글로벌)"
    if roe >= ROE_KOREAN_PCT:
        return 12, f"ROE {roe:.1f}% (12~17% 한국형)"
    if roe >= ROE_FLOOR_PCT:
        return 8, f"ROE {roe:.1f}% (8~12%)"
    return 3, f"ROE {roe:.1f}% (<8%)"


def _score_recovery_strength(latest_annual_yoy: float | None) -> tuple[int, str]:
    """턴어라운드 축 ① — 회복 강도 5점 (직전 1년 EPS YoY)."""
    if latest_annual_yoy is None:
        return 0, "데이터 부족"
    if latest_annual_yoy >= 50:
        return 5, f"+{latest_annual_yoy:.1f}% (≥+50% 강한 회복)"
    if latest_annual_yoy >= 20:
        return 4, f"+{latest_annual_yoy:.1f}% (+20~+50%)"
    if latest_annual_yoy >= 5:
        return 3, f"+{latest_annual_yoy:.1f}% (+5~+20%)"
    if latest_annual_yoy >= 3:
        return 2, f"+{latest_annual_yoy:.1f}% (+3~+5% 예비)"
    return 0, f"{latest_annual_yoy:.1f}% (회복 미달)"


def _score_quarterly_surge(
    quarterly_eps_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
) -> tuple[int, str]:
    """턴어라운드 축 ② — 분기 급증 강도 25점.

    - 2분기 연속 ≥ +100% → 25
    - 2분기 ≥ +50% → 20
    - 단일 +50%+ (history 부족) → 15
    - 2분기 ≥ +30% (예비) → 10
    """
    if len(quarterly_eps_yoy_history) >= 2:
        last_two = [v for _, v in quarterly_eps_yoy_history[-2:]]
        a, b = last_two[0], last_two[1]
        if a >= TURNAROUND_SURGE_FULL_PCT and b >= TURNAROUND_SURGE_FULL_PCT:
            return 25, f"2분기 연속 ≥+100% ({a:.1f}%, {b:.1f}%)"
        if a >= TURNAROUND_SURGE_ORTHODOX_PCT and b >= TURNAROUND_SURGE_ORTHODOX_PCT:
            return 20, f"2분기 연속 ≥+50% ({a:.1f}%, {b:.1f}%)"
        if a >= TURNAROUND_SURGE_PRELIM_PCT and b >= TURNAROUND_SURGE_PRELIM_PCT:
            return 10, f"2분기 연속 ≥+30% 예비 ({a:.1f}%, {b:.1f}%)"
    if latest_quarter_yoy is not None and latest_quarter_yoy >= TURNAROUND_SURGE_ORTHODOX_PCT:
        return 15, f"단일 분기 +{latest_quarter_yoy:.1f}% (history 부족)"
    return 0, "분기 급증 미달"


def _score_ttm_recovery(ttm_high_ratio: float | None, is_all_time_high: bool) -> tuple[int, str]:
    """턴어라운드 축 ③ — TTM 회복도 5점."""
    if is_all_time_high:
        return 5, "사상 최고치 갱신"
    if ttm_high_ratio is None:
        return 0, "데이터 부족"
    if ttm_high_ratio >= 1.0:
        return 5, "사상 최고치 갱신"
    if ttm_high_ratio >= TURNAROUND_TTM_ORTHODOX_RATIO:
        return 4, f"TTM {ttm_high_ratio * 100:.0f}% (90~100%)"
    if ttm_high_ratio >= TURNAROUND_TTM_PRELIM_RATIO:
        return 3, f"TTM {ttm_high_ratio * 100:.0f}% (80~90% 예비)"
    return 0, f"TTM {ttm_high_ratio * 100:.0f}% (<80%)"


def _score_quarterly_eps_strength(history: list[tuple[str, float]]) -> tuple[int, str]:
    """신규상장 축 ① — 분기 EPS 강도 25점 (최근 2분기 평균 YoY)."""
    if len(history) < 2:
        return 0, "history 부족"
    last_two_avg = sum(v for _, v in history[-2:]) / 2
    if last_two_avg >= NEW_LISTING_EPS_FULL_PCT:
        return 25, f"2분기 평균 +{last_two_avg:.1f}% (≥+100%)"
    if last_two_avg >= NEW_LISTING_EPS_HIGH_PCT:
        return 20, f"2분기 평균 +{last_two_avg:.1f}% (+50~+100%)"
    if last_two_avg >= NEW_LISTING_QUARTERLY_MIN_PCT:
        return 13, f"2분기 평균 +{last_two_avg:.1f}% (+25~+50%)"
    return 0, f"2분기 평균 +{last_two_avg:.1f}% (<+25%)"


def _score_quarterly_sales_strength(history: list[tuple[str, float]]) -> tuple[int, str]:
    """신규상장 축 ② — 분기 매출 강도 5점 (최근 2분기 평균 YoY)."""
    if len(history) < 2:
        return 0, "history 부족"
    last_two_avg = sum(v for _, v in history[-2:]) / 2
    if last_two_avg >= NEW_LISTING_SALES_FULL_PCT:
        return 5, f"2분기 평균 +{last_two_avg:.1f}% (≥+50%)"
    if last_two_avg >= NEW_LISTING_QUARTERLY_MIN_PCT:
        return 3, f"2분기 평균 +{last_two_avg:.1f}% (+25~+50%)"
    return 0, f"2분기 평균 +{last_two_avg:.1f}% (<+25%)"


def _score_stability(quarterly_eps_for_stability: list[float] | None) -> tuple[int, str]:
    """신규상장 축 ④ — 안정성 5점."""
    if not quarterly_eps_for_stability or len(quarterly_eps_for_stability) < 12:
        return 1, "데이터 부족 (<12분기)"
    score, detail = compute_earnings_stability(quarterly_eps_for_stability)
    if score is None:
        return 1, detail
    if score < STABILITY_EXCELLENT_MAX:
        return 5, f"안정성 우수 ({detail})"
    if score <= STABILITY_MODERATE_MAX:
        return 3, f"안정성 보통 ({detail})"
    return 1, f"안정성 부족 ({detail})"


# ────────────────────────────────────────────────────────
# 분석 헬퍼 — 연간 EPS 시계열에서 파생 지표 추출
# ────────────────────────────────────────────────────────


def _compute_three_year_growths(annual_eps: list[tuple[str, float]]) -> list[float]:
    """최근 4년 윈도우에서 3개의 YoY 증가율 산출. ±500% 로 cap."""
    if len(annual_eps) < 2:
        return []
    window = annual_eps[-4:]
    growths: list[float] = []
    for i in range(1, len(window)):
        prev_v = window[i - 1][1]
        curr_v = window[i][1]
        if prev_v == 0:
            continue
        denom = abs(prev_v) if prev_v < 0 else prev_v
        g = (curr_v - prev_v) / denom * 100
        g_capped = max(-500.0, min(500.0, g))
        growths.append(round(g_capped, 2))
    return growths


def _compute_ttm_high_ratio(annual_eps: list[tuple[str, float]]) -> tuple[float | None, bool]:
    """최근 연 EPS 가 과거 사상 최고치 대비 비율 + 사상 최고치 여부."""
    if len(annual_eps) < 2:
        return None, False
    all_years_pos = [v for _, v in annual_eps if v > 0]
    if not all_years_pos:
        return None, False
    current = annual_eps[-1][1]
    if current <= 0:
        return None, False
    past_max = max(all_years_pos[:-1]) if len(all_years_pos) >= 2 else all_years_pos[0]
    if past_max <= 0:
        return None, False
    return round(current / past_max, 3), current >= past_max


def _compute_latest_annual_yoy(annual_eps: list[tuple[str, float]]) -> float | None:
    """직전 1년 EPS YoY (적자→흑자 전환은 999.99 placeholder)."""
    if len(annual_eps) < 2:
        return None
    prev_v = annual_eps[-2][1]
    curr_v = annual_eps[-1][1]
    if curr_v > 0 and prev_v <= 0:
        return 999.99
    if prev_v == 0:
        return None
    return round((curr_v - prev_v) / abs(prev_v) * 100, 2)


# ────────────────────────────────────────────────────────
# 트랙 분류
# ────────────────────────────────────────────────────────


def _is_orthodox_eligible(annual_eps: list[tuple[str, float]]) -> bool:
    """정통 A 입장 조건: 연간 EPS 데이터 ≥ 3년 + 최근 3년 모두 흑자.

    (단조 증가 여부는 점수로 차등화, 입장 조건엔 포함 안 함 — 부분 점수 의미 보장)
    """
    if len(annual_eps) < 3:
        return False
    recent_3 = annual_eps[-3:]
    return all(v > 0 for _, v in recent_3)


def _is_turnaround_eligible(
    latest_annual_yoy: float | None,
    quarterly_eps_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    ttm_high_ratio: float | None,
    is_all_time_high: bool,
) -> tuple[bool, bool]:
    """턴어라운드 입장 조건 검사. Returns: (orthodox_pass, preliminary_pass)."""

    # 1) 회복 강도
    recovery_orthodox = (
        latest_annual_yoy is not None
        and latest_annual_yoy >= TURNAROUND_RECOVERY_ORTHODOX_PCT
    )
    recovery_prelim = (
        latest_annual_yoy is not None
        and latest_annual_yoy >= TURNAROUND_RECOVERY_PRELIM_PCT
    )

    # 2) 분기 급증
    surge_orthodox = False
    surge_prelim = False
    if len(quarterly_eps_yoy_history) >= 2:
        last_two = [v for _, v in quarterly_eps_yoy_history[-2:]]
        if all(v >= TURNAROUND_SURGE_ORTHODOX_PCT for v in last_two):
            surge_orthodox = True
        if all(v >= TURNAROUND_SURGE_PRELIM_PCT for v in last_two):
            surge_prelim = True
    # history 부족 시 단일 분기 인정 (정통만)
    if not surge_orthodox and latest_quarter_yoy is not None:
        if latest_quarter_yoy >= TURNAROUND_SURGE_ORTHODOX_PCT:
            surge_orthodox = True
            surge_prelim = True

    # 3) TTM 회복도
    ttm_orthodox = is_all_time_high or (
        ttm_high_ratio is not None and ttm_high_ratio >= TURNAROUND_TTM_ORTHODOX_RATIO
    )
    ttm_prelim = is_all_time_high or (
        ttm_high_ratio is not None and ttm_high_ratio >= TURNAROUND_TTM_PRELIM_RATIO
    )

    orthodox_pass = recovery_orthodox and surge_orthodox and ttm_orthodox
    preliminary_pass = recovery_prelim and surge_prelim and ttm_prelim and not orthodox_pass
    return orthodox_pass, preliminary_pass


def _is_new_listing_eligible(
    annual_eps: list[tuple[str, float]],
    quarterly_eps_yoy_history: list[tuple[str, float]],
    sales_yoy_history: list[tuple[str, float]],
) -> bool:
    """신규상장 입장 조건:
      - 연간 EPS 데이터 < 3년 (상장 < 3년 근사)
      - 분기 EPS YoY 최근 2분기 모두 ≥ +25%
      - 분기 매출 YoY 최근 2분기 모두 ≥ +25%
    """
    if len(annual_eps) >= NEW_LISTING_MAX_ANNUAL_DATA:
        return False
    if len(quarterly_eps_yoy_history) < NEW_LISTING_MIN_HISTORY:
        return False
    if len(sales_yoy_history) < NEW_LISTING_MIN_HISTORY:
        return False
    eps_ok = all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in quarterly_eps_yoy_history[-2:])
    sales_ok = all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in sales_yoy_history[-2:])
    return eps_ok and sales_ok


# ────────────────────────────────────────────────────────
# 메인 엔트리 — v2 평가 + 점수 산정
# ────────────────────────────────────────────────────────


def evaluate_a_v2(
    annual_eps: list[tuple[str, float]],
    annual_roe: list[tuple[str, float]],
    quarterly_eps_yoy_history: list[tuple[str, float]],
    sales_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    induty_code: str | None,
    quarterly_eps_for_stability: list[float] | None = None,
    pretax_margin: float | None = None,
) -> dict:
    """C 통과 종목을 v2 점수 체계로 평가.

    Returns: 트랙별 점수 dict. 어디에도 분류되지 않으면 'unclassified' 트랙으로
    0점 entry 반환 (랭킹 시스템에서 사용하기 위함).

    트랙 분류 우선순위: 정통 A → 턴어라운드 → 신규상장 → 분류 불가 (0점).
    """
    latest_roe = round(annual_roe[-1][1], 2) if annual_roe else None
    three_year_growths = _compute_three_year_growths(annual_eps)
    avg_growth = (
        round(sum(three_year_growths) / len(three_year_growths), 2)
        if three_year_growths
        else None
    )
    latest_annual_yoy = _compute_latest_annual_yoy(annual_eps)
    ttm_high_ratio, is_all_time_high = _compute_ttm_high_ratio(annual_eps)

    is_cyclical_val = is_cyclical_industry(induty_code)
    margin_lbl = margin_label(pretax_margin)

    # 공통 raw 데이터 (모든 트랙에서 표시)
    raw = {
        "annual_eps": [(k, round(v, 2)) for k, v in annual_eps[-6:]],
        "annual_roe": [(k, round(v, 2)) for k, v in annual_roe[-6:]],
        "three_year_growths": three_year_growths,
        "three_year_avg_growth": avg_growth,
        "latest_annual_yoy": latest_annual_yoy,
        "latest_roe": latest_roe,
        "latest_quarter_yoy": latest_quarter_yoy,
        "pretax_margin": pretax_margin,
        "ttm_high_ratio": ttm_high_ratio,
        "is_all_time_high": is_all_time_high,
        "induty_code": induty_code,
    }

    common = {
        "margin_label": margin_lbl,
        "is_cyclical": is_cyclical_val,
        "raw": raw,
    }

    # 1) 정통 A 트랙 시도
    if _is_orthodox_eligible(annual_eps):
        return _build_orthodox(annual_eps, three_year_growths, avg_growth, latest_roe, common)

    # 2) 턴어라운드 트랙 시도
    orthodox_t, preliminary_t = _is_turnaround_eligible(
        latest_annual_yoy, quarterly_eps_yoy_history, latest_quarter_yoy,
        ttm_high_ratio, is_all_time_high,
    )
    if orthodox_t or preliminary_t:
        return _build_turnaround(
            latest_annual_yoy, quarterly_eps_yoy_history, latest_quarter_yoy,
            ttm_high_ratio, is_all_time_high, latest_roe,
            is_preliminary=preliminary_t, common=common,
        )

    # 3) 신규상장 트랙 시도
    if _is_new_listing_eligible(annual_eps, quarterly_eps_yoy_history, sales_yoy_history):
        return _build_new_listing(
            quarterly_eps_yoy_history, sales_yoy_history, latest_roe,
            quarterly_eps_for_stability, common,
        )

    # 4) 분류 불가 — 어떤 트랙에도 못 들어옴. 랭킹 시스템 위해 0점 entry 반환.
    return _build_unclassified(
        annual_eps, latest_annual_yoy,
        quarterly_eps_yoy_history, latest_quarter_yoy,
        ttm_high_ratio, is_all_time_high,
        sales_yoy_history,
        common,
    )


def _build_orthodox(
    annual_eps: list[tuple[str, float]],
    growths: list[float],
    avg_growth: float | None,
    latest_roe: float | None,
    common: dict,
) -> dict:
    s1, n1 = _score_eps_consistency_orthodox(annual_eps, growths)
    s2, n2 = _score_eps_growth(avg_growth)
    s3, n3 = _score_profitability_roe(latest_roe)
    total = s1 + s2 + s3

    badges: list[str] = []
    if growths and len(growths) >= 3 and all(g >= EPS_GROWTH_FULL_PCT for g in growths):
        badges.append("⭐ 매년 +25% 성장")
    if common["is_cyclical"]:
        badges.append("⚠️ 경기민감")

    return {
        "track": "orthodox",
        "track_label": "정통 A",
        "score": total,
        "grade": grade_label(total),
        "axis_breakdown": {
            "eps_consistency": s1,
            "eps_growth": s2,
            "profitability": s3,
        },
        "axis_notes": {
            "eps_consistency": n1,
            "eps_growth": n2,
            "profitability": n3,
        },
        "is_preliminary": False,
        "badges": badges,
        **common,
    }


def _build_turnaround(
    latest_annual_yoy: float | None,
    quarterly_eps_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    ttm_high_ratio: float | None,
    is_all_time_high: bool,
    latest_roe: float | None,
    is_preliminary: bool,
    common: dict,
) -> dict:
    s1, n1 = _score_recovery_strength(latest_annual_yoy)
    s2, n2 = _score_quarterly_surge(quarterly_eps_yoy_history, latest_quarter_yoy)
    s3, n3 = _score_ttm_recovery(ttm_high_ratio, is_all_time_high)
    s4, n4 = _score_profitability_roe(latest_roe)
    total = s1 + s2 + s3 + s4

    badges: list[str] = []
    if is_preliminary:
        badges.append("🟡 예비 턴어라운드")
    else:
        badges.append("🔄 턴어라운드")
    if common["is_cyclical"]:
        badges.append("⚠️ 경기민감")

    return {
        "track": "turnaround",
        "track_label": "예비 턴어라운드" if is_preliminary else "턴어라운드",
        "score": total,
        "grade": grade_label(total),
        "axis_breakdown": {
            "recovery_strength": s1,
            "quarterly_surge": s2,
            "ttm_recovery": s3,
            "profitability": s4,
        },
        "axis_notes": {
            "recovery_strength": n1,
            "quarterly_surge": n2,
            "ttm_recovery": n3,
            "profitability": n4,
        },
        "is_preliminary": is_preliminary,
        "badges": badges,
        **common,
    }


def _build_unclassified(
    annual_eps: list[tuple[str, float]],
    latest_annual_yoy: float | None,
    quarterly_eps_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    ttm_high_ratio: float | None,
    is_all_time_high: bool,
    sales_yoy_history: list[tuple[str, float]],
    common: dict,
) -> dict:
    """분류 불가 entry — 0점. 어느 트랙 어느 게이트에서 떨어졌는지 fail_reasons 에 기록.

    랭킹 시스템에서 C 통과 종목 *전체* 를 다루기 위해 None 대신 0점 entry 반환.
    """
    fail_reasons: list[str] = []

    # 정통 A 미진입 사유
    recent_3 = annual_eps[-3:] if len(annual_eps) >= 3 else annual_eps
    if len(annual_eps) < 3:
        fail_reasons.append(f"[정통 A] 연간 데이터 {len(annual_eps)}년 (3년 필요)")
    else:
        loss_count = sum(1 for _, v in recent_3 if v <= 0)
        if loss_count > 0:
            fail_reasons.append(f"[정통 A] 최근 3년 중 적자 {loss_count}회")

    # 턴어라운드 미진입 사유
    ann_yoy_str = f"{latest_annual_yoy:.1f}%" if latest_annual_yoy is not None else "N/A"
    if latest_annual_yoy is None or latest_annual_yoy < TURNAROUND_RECOVERY_PRELIM_PCT:
        fail_reasons.append(f"[턴어라운드] 직전 1년 회복 {ann_yoy_str} (예비 ≥+{TURNAROUND_RECOVERY_PRELIM_PCT}% 필요)")

    surge_prelim_pass = False
    if len(quarterly_eps_yoy_history) >= 2:
        last_two = [v for _, v in quarterly_eps_yoy_history[-2:]]
        surge_prelim_pass = all(v >= TURNAROUND_SURGE_PRELIM_PCT for v in last_two)
    elif latest_quarter_yoy is not None and latest_quarter_yoy >= TURNAROUND_SURGE_ORTHODOX_PCT:
        surge_prelim_pass = True
    if not surge_prelim_pass:
        fail_reasons.append(
            f"[턴어라운드] 분기 급증 부족 (2분기 연속 ≥+{TURNAROUND_SURGE_PRELIM_PCT}% 예비 필요)"
        )

    ttm_str = (
        "사상 최고치" if is_all_time_high
        else f"{ttm_high_ratio * 100:.0f}%" if ttm_high_ratio is not None
        else "N/A (현재 적자)"
    )
    ttm_prelim_pass = is_all_time_high or (
        ttm_high_ratio is not None and ttm_high_ratio >= TURNAROUND_TTM_PRELIM_RATIO
    )
    if not ttm_prelim_pass:
        fail_reasons.append(
            f"[턴어라운드] TTM 사상 최고치 근접도 {ttm_str} (예비 ≥{int(TURNAROUND_TTM_PRELIM_RATIO*100)}% 필요)"
        )

    # 신규상장 미진입 사유
    if len(annual_eps) >= NEW_LISTING_MAX_ANNUAL_DATA:
        fail_reasons.append(
            f"[신규상장] 연간 데이터 {len(annual_eps)}년 (<{NEW_LISTING_MAX_ANNUAL_DATA}년 필요)"
        )
    else:
        if len(quarterly_eps_yoy_history) < NEW_LISTING_MIN_HISTORY:
            fail_reasons.append(
                f"[신규상장] 분기 EPS history {len(quarterly_eps_yoy_history)}개 (≥{NEW_LISTING_MIN_HISTORY} 필요)"
            )
        elif not all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in quarterly_eps_yoy_history[-2:]):
            fail_reasons.append(f"[신규상장] 분기 EPS YoY 2분기 모두 ≥+{NEW_LISTING_QUARTERLY_MIN_PCT}% 미달")
        if len(sales_yoy_history) < NEW_LISTING_MIN_HISTORY:
            fail_reasons.append(
                f"[신규상장] 분기 매출 history {len(sales_yoy_history)}개 (≥{NEW_LISTING_MIN_HISTORY} 필요)"
            )
        elif not all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in sales_yoy_history[-2:]):
            fail_reasons.append(f"[신규상장] 분기 매출 YoY 2분기 모두 ≥+{NEW_LISTING_QUARTERLY_MIN_PCT}% 미달")

    badges: list[str] = ["분류 불가"]
    if common["is_cyclical"]:
        badges.append("⚠️ 경기민감")

    return {
        "track": "unclassified",
        "track_label": "분류 불가",
        "score": 0,
        "grade": "하",
        "axis_breakdown": {},
        "axis_notes": {},
        "is_preliminary": False,
        "badges": badges,
        "fail_reasons": fail_reasons,
        **common,
    }


def _build_new_listing(
    quarterly_eps_yoy_history: list[tuple[str, float]],
    sales_yoy_history: list[tuple[str, float]],
    latest_roe: float | None,
    quarterly_eps_for_stability: list[float] | None,
    common: dict,
) -> dict:
    s1, n1 = _score_quarterly_eps_strength(quarterly_eps_yoy_history)
    s2, n2 = _score_quarterly_sales_strength(sales_yoy_history)
    s3, n3 = _score_profitability_roe(latest_roe)
    s4, n4 = _score_stability(quarterly_eps_for_stability)
    total = s1 + s2 + s3 + s4

    badges: list[str] = ["🆕 신규상장"]
    if common["is_cyclical"]:
        badges.append("⚠️ 경기민감")

    return {
        "track": "new_listing",
        "track_label": "신규상장",
        "score": total,
        "grade": grade_label(total),
        "axis_breakdown": {
            "quarterly_eps_strength": s1,
            "quarterly_sales_strength": s2,
            "profitability": s3,
            "stability": s4,
        },
        "axis_notes": {
            "quarterly_eps_strength": n1,
            "quarterly_sales_strength": n2,
            "profitability": n3,
            "stability": n4,
        },
        "is_preliminary": False,
        "badges": badges,
        **common,
    }
