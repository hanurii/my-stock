"""CAN SLIM 'A' 원칙 (Annual Earnings) 평가 — C 와 격리된 모듈.

evaluate_a_detailed: 사용자 메모리 user_canslim_thresholds.md 의 A 컷오프를 그대로 적용.
- 메인 트랙 통과 조건 5개 AND 조합
- 가점 배지 raw 값 노출

원본 criteria.py 의 evaluate_a 는 미수정.
"""

from __future__ import annotations

import math
from typing import Any


# 사용자 컷오프 (메모리 user_canslim_thresholds.md A 섹션과 동일)
A_ANNUAL_EPS_GROWTH_MIN_PCT = 25.0
A_ROE_MIN_PCT = 12.0  # 한국 보정 (한국 KOSPI 평균 ROE 8.2%, O'Neil 원전 17% → 12%)
A_DECELERATION_GATE_DIVISOR = 3.0  # 직전 분기 YoY ≥ 3년 평균 증가율 / 3
A_BADGE_ROE_GLOBAL = 17.0  # O'Neil 원전 기준 충족 — "글로벌 ROE" 배지
A_BADGE_ROE_EXCELLENT = 25.0  # 탁월 ROE
A_BADGE_CPS_EPS_RATIO = 1.20
# 안정성 지수 임계값 — 한국 보정 (+5 shift)
# O'Neil 원전: <25 우수 / 25~30 보통 / >30 부족
# 한국 보정: 한국 KOSPI 시총 상위 다수가 cyclical 산업(반도체·자동차·철강·화학·배터리)이라 원전 적용 시 거의 전부 "부족" 분류.
# 한국 종목 분포 분석 기반 +5 shift: <30 우수 / 30~40 보통 / >40 부족
A_STABILITY_EXCELLENT_MAX = 30
A_STABILITY_MODERATE_MAX = 40

# 턴어라운드 트랙 컷오프 (별도 트랙 — 메인 트랙 미충족 종목 중 V자 회복주 잡기)
TURNAROUND_ANNUAL_EPS_MIN_PCT = 5.0  # 직전 1년 연 EPS YoY +5% 이상
TURNAROUND_QUARTERLY_YOY_MIN_PCT = 50.0  # 분기 EPS YoY +50% 이상 (사용자 본문 "급증" 정량화)
TURNAROUND_TTM_HIGH_RATIO = 0.90  # TTM EPS 가 직전 N년 사상 최고치의 90% 이상

# 예비 턴어라운드 컷오프 — 정통 한 단계 완화. 한 두 개 약간 미달이지만 다음 분기에 잡힐 가능성 높은 종목
TURNAROUND_PRELIM_ANNUAL_EPS_MIN_PCT = 0.0  # 양수 회복만 확인
TURNAROUND_PRELIM_QUARTERLY_YOY_MIN_PCT = 30.0  # 분기 +30%+ 급증
TURNAROUND_PRELIM_TTM_HIGH_RATIO = 0.80  # TTM 80%+ (예: 삼성전자 82%)

# 신규 상장 (<3년) 트랙 컷오프 — 연간 데이터 부족 종목 중 분기 가속 강한 후보
NEW_LISTING_QUARTERLY_MIN_PCT = 25.0  # 분기 EPS YoY 모든 분기 +25%+ (지속성)
NEW_LISTING_MIN_HISTORY = 3  # 분기 history 최소 3개 (1~2분기는 불충분)

# KSIC (한국표준산업분류) 코드 prefix 기반 경기민감주 (사용자 본문 5개)
# 24=1차 금속(철강), 20=화학, 17=펄프/종이(제지), 22=고무/플라스틱, 29=기타 기계/장비
CYCLICAL_KSIC_PREFIXES = ("24", "20", "17", "22", "29")


def is_cyclical_industry(induty_code: str | None) -> bool:
    if not induty_code or len(induty_code) < 2:
        return False
    return induty_code[:2] in CYCLICAL_KSIC_PREFIXES


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
    """순이익 안정성 지수 (1~99, 낮을수록 안정).

    공개 합의된 근사 (IBD 정확 공식 비공개):
    1) 분기 EPS 시계열을 시간 t 에 대한 선형 회귀로 추세선 fit
    2) 평균 절대 편차 / 평균 |EPS| = 편차율(%)
       (적자 분기 포함해도 분모 안전 — mean(|EPS|) 는 부호 무관)
    3) score = 20 * log10(편차율 + 1) 후 [1, 99] 클램프

    적자 분기가 있어도 점수 산출. 데이터 < 12분기 또는 전 분기 EPS=0 인 경우만 None.
    """
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
        detail += f" (적자 {loss_count}분기 포함, 평균 |EPS| 정규화)"
    return score, detail


def evaluate_new_listing_detailed(
    annual_eps: list[tuple[str, float]],
    quarterly_eps_yoy_history: list[tuple[str, float]],
    sales_yoy_history: list[tuple[str, float]],
    induty_code: str | None,
    annual_roe: list[tuple[str, float]] | None = None,
    quarterly_eps_for_stability: list[float] | None = None,
) -> dict:
    """A 신규 상장 (<3년) 트랙 — 연간 데이터 부족 종목 중 분기 EPS·매출 강한 후보.

    O'Neil 원전 (사용자 본문 #8): 상장 3년 미만으로 연 데이터 없으면
      - 최근 5~6분기 EPS 큰 폭 증가
      - 분기 매출 증가율도 충분
      - 1~2분기만 좋은 건 불충분 (지속성 확인)
    """
    out: dict[str, Any] = {
        "new_listing_pass": False,
        "annual_eps_count": len(annual_eps),
        "annual_eps": [(k, round(v, 2)) for k, v in annual_eps[-5:]],
        "quarterly_yoy_history": [(p, round(v, 2)) for p, v in quarterly_eps_yoy_history[-5:]],
        "sales_yoy_history": [(p, round(v, 2)) for p, v in sales_yoy_history[-5:]],
        "induty_code": induty_code,
        "cyclical": is_cyclical_industry(induty_code),
        "earnings_stability_score": None,
        "earnings_stability_detail": "",
        "latest_roe": annual_roe[-1][1] if annual_roe else None,
        "badges": [],
        "fail_reasons": [],
    }

    # 1) 분기 EPS 지속성
    if len(quarterly_eps_yoy_history) < NEW_LISTING_MIN_HISTORY:
        out["fail_reasons"].append(
            f"분기 EPS YoY history {len(quarterly_eps_yoy_history)}개 (≥{NEW_LISTING_MIN_HISTORY} 필요)"
        )
    eps_pass = (
        len(quarterly_eps_yoy_history) >= NEW_LISTING_MIN_HISTORY
        and all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in quarterly_eps_yoy_history)
    )

    # 2) 분기 매출 지속성
    if len(sales_yoy_history) < NEW_LISTING_MIN_HISTORY:
        out["fail_reasons"].append(
            f"분기 매출 YoY history {len(sales_yoy_history)}개 (≥{NEW_LISTING_MIN_HISTORY} 필요)"
        )
    sales_pass = (
        len(sales_yoy_history) >= NEW_LISTING_MIN_HISTORY
        and all(v >= NEW_LISTING_QUARTERLY_MIN_PCT for _, v in sales_yoy_history)
    )

    # 3) 비경기민감
    cyclical_pass = not out["cyclical"]

    out["new_listing_pass"] = bool(eps_pass and sales_pass and cyclical_pass)

    if not eps_pass and len(quarterly_eps_yoy_history) >= NEW_LISTING_MIN_HISTORY:
        weakest = min(v for _, v in quarterly_eps_yoy_history)
        out["fail_reasons"].append(
            f"분기 EPS YoY 지속성 미충족 (최약 +{weakest:.1f}%, ≥+{NEW_LISTING_QUARTERLY_MIN_PCT}% 필요)"
        )
    if not sales_pass and len(sales_yoy_history) >= NEW_LISTING_MIN_HISTORY:
        weakest = min(v for _, v in sales_yoy_history)
        out["fail_reasons"].append(
            f"분기 매출 YoY 지속성 미충족 (최약 +{weakest:.1f}%, ≥+{NEW_LISTING_QUARTERLY_MIN_PCT}% 필요)"
        )
    if not cyclical_pass:
        out["fail_reasons"].append(f"경기민감주 (KSIC {induty_code})")

    # 안정성 + ROE 배지 (참고)
    if quarterly_eps_for_stability and len(quarterly_eps_for_stability) >= 12:
        score, detail = compute_earnings_stability(quarterly_eps_for_stability)
        out["earnings_stability_score"] = score
        out["earnings_stability_detail"] = detail
        if score is not None:
            if score < A_STABILITY_EXCELLENT_MAX:
                out["badges"].append("안정성 우수")
            elif score <= A_STABILITY_MODERATE_MAX:
                out["badges"].append("안정성 보통")
            else:
                out["badges"].append("안정성 부족")
    if out["latest_roe"] is not None:
        if out["latest_roe"] >= A_BADGE_ROE_EXCELLENT:
            out["badges"].append("탁월 ROE")
        elif out["latest_roe"] >= A_BADGE_ROE_GLOBAL:
            out["badges"].append("글로벌 ROE")

    return out


def evaluate_turnaround_detailed(
    annual_eps: list[tuple[str, float]],
    annual_roe: list[tuple[str, float]],
    quarterly_eps_yoy_history: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    induty_code: str | None,
    quarterly_eps_for_stability: list[float] | None = None,
) -> dict:
    """A 턴어라운드 트랙 평가 — 메인 트랙 미충족 V자 회복주 잡기.

    O'Neil 원전 (사용자 제공): 클리브랜드 클리프스 사례 — 적자 → 64% → 241% 두 분기 → 8개월 +170%.

    조건 (모두 충족):
      1. 직전 1년 연 EPS YoY ≥ 5% (회복 확인)
      2. 분기 EPS 2분기 연속 YoY ≥ +50% 급증
         (history 부족 시 직전 분기 단일 +50%+ 만으로도 OK — V자 막 시작 단계)
      3. 가장 최근 연 EPS 가 과거 5년 최고치의 90% 이상 (사상 최고치 근접)
         또는 가장 최근 연 EPS 가 사상 최고치 자체
      4. KSIC 경기민감주 prefix 미해당
    """
    out: dict[str, Any] = {
        "turnaround_pass": False,
        "preliminary_turnaround_pass": False,
        "annual_eps": [(k, round(v, 2)) for k, v in annual_eps[-5:]],
        "annual_roe": [(k, round(v, 2)) for k, v in annual_roe[-5:]],
        "latest_annual_yoy": None,
        "two_quarter_surge": False,
        "two_quarter_surge_detail": "",
        "preliminary_two_quarter_surge": False,
        "ttm_high_ratio": None,
        "is_all_time_high": False,
        "latest_quarter_yoy": latest_quarter_yoy,
        "induty_code": induty_code,
        "cyclical": is_cyclical_industry(induty_code),
        "earnings_stability_score": None,
        "earnings_stability_detail": "",
        "latest_roe": None,
        "badges": [],
        "fail_reasons": [],
    }

    # 1) 직전 1년 연 EPS YoY
    if len(annual_eps) >= 2:
        prev_key, prev_v = annual_eps[-2]
        curr_key, curr_v = annual_eps[-1]
        if prev_v != 0 and curr_v > 0:
            yoy = (curr_v - prev_v) / abs(prev_v) * 100
            out["latest_annual_yoy"] = round(yoy, 2)
        elif curr_v > 0 and prev_v <= 0:
            # 적자→흑자 전환
            out["latest_annual_yoy"] = 999.99  # 무한대 표시 placeholder

    # 2) 2분기 연속 +50%+ 급증 (정통)
    if len(quarterly_eps_yoy_history) >= 2:
        last_two = quarterly_eps_yoy_history[-2:]
        if all(v >= TURNAROUND_QUARTERLY_YOY_MIN_PCT for _, v in last_two):
            out["two_quarter_surge"] = True
            out["two_quarter_surge_detail"] = (
                f"{last_two[0][0]} +{last_two[0][1]:.1f}%, {last_two[1][0]} +{last_two[1][1]:.1f}%"
            )
        if all(v >= TURNAROUND_PRELIM_QUARTERLY_YOY_MIN_PCT for _, v in last_two):
            out["preliminary_two_quarter_surge"] = True
            if not out["two_quarter_surge_detail"]:
                out["two_quarter_surge_detail"] = (
                    f"{last_two[0][0]} +{last_two[0][1]:.1f}%, {last_two[1][0]} +{last_two[1][1]:.1f}% (예비)"
                )
    # history 부족 케이스 — 직전 분기 단일로 V자 시작 인정
    elif latest_quarter_yoy is not None:
        if latest_quarter_yoy >= TURNAROUND_QUARTERLY_YOY_MIN_PCT:
            out["two_quarter_surge"] = True
            out["two_quarter_surge_detail"] = f"직전 분기 단일 +{latest_quarter_yoy:.1f}% (history 부족)"
        if latest_quarter_yoy >= TURNAROUND_PRELIM_QUARTERLY_YOY_MIN_PCT:
            out["preliminary_two_quarter_surge"] = True
            if not out["two_quarter_surge_detail"]:
                out["two_quarter_surge_detail"] = f"직전 분기 단일 +{latest_quarter_yoy:.1f}% (예비)"

    # 3) TTM 사상 최고치 근접 — 연간 EPS 기반 근사
    if len(annual_eps) >= 2:
        all_years = [v for _, v in annual_eps if v > 0]
        if all_years:
            past_max = max(all_years[:-1]) if len(all_years) >= 2 else all_years[0]
            current = annual_eps[-1][1]
            if current > 0 and past_max > 0:
                out["ttm_high_ratio"] = round(current / past_max, 3)
                out["is_all_time_high"] = current >= past_max

    # ROE / 안정성 (배지·표시용, 통과 영향 X)
    if annual_roe:
        out["latest_roe"] = round(annual_roe[-1][1], 2)
    if quarterly_eps_for_stability and len(quarterly_eps_for_stability) >= 12:
        score, detail = compute_earnings_stability(quarterly_eps_for_stability)
        out["earnings_stability_score"] = score
        out["earnings_stability_detail"] = detail

    pass_recovery = (
        out["latest_annual_yoy"] is not None
        and out["latest_annual_yoy"] >= TURNAROUND_ANNUAL_EPS_MIN_PCT
    )
    pass_surge = out["two_quarter_surge"]
    pass_high = (
        out["is_all_time_high"]
        or (out["ttm_high_ratio"] is not None and out["ttm_high_ratio"] >= TURNAROUND_TTM_HIGH_RATIO)
    )
    pass_cyclical = not out["cyclical"]

    out["turnaround_pass"] = bool(pass_recovery and pass_surge and pass_high and pass_cyclical)

    # 예비 턴어라운드 — 정통 미충족이지만 한두 항목 약간 미달, 다음 분기 잡힐 가능성 높음
    prelim_recovery = (
        out["latest_annual_yoy"] is not None
        and out["latest_annual_yoy"] >= TURNAROUND_PRELIM_ANNUAL_EPS_MIN_PCT
    )
    prelim_surge = out["preliminary_two_quarter_surge"]
    prelim_high = (
        out["is_all_time_high"]
        or (out["ttm_high_ratio"] is not None and out["ttm_high_ratio"] >= TURNAROUND_PRELIM_TTM_HIGH_RATIO)
    )
    out["preliminary_turnaround_pass"] = bool(
        prelim_recovery and prelim_surge and prelim_high and pass_cyclical and not out["turnaround_pass"]
    )

    if not pass_recovery:
        ann_str = f"{out['latest_annual_yoy']}%" if out["latest_annual_yoy"] is not None else "N/A"
        out["fail_reasons"].append(f"직전 1년 EPS YoY {ann_str} (≥{TURNAROUND_ANNUAL_EPS_MIN_PCT}% 필요)")
    if not pass_surge:
        out["fail_reasons"].append(f"2분기 연속 +{TURNAROUND_QUARTERLY_YOY_MIN_PCT}%+ 급증 미충족")
    if not pass_high:
        ratio_str = f"{out['ttm_high_ratio']*100:.0f}%" if out["ttm_high_ratio"] is not None else "N/A"
        out["fail_reasons"].append(f"TTM 사상 최고치 {ratio_str} (≥{TURNAROUND_TTM_HIGH_RATIO*100:.0f}% 또는 신고가 필요)")
    if not pass_cyclical:
        out["fail_reasons"].append(f"경기민감주 (KSIC {induty_code})")

    # 배지
    if out["is_all_time_high"]:
        out["badges"].append("사상 최고치")
    if out["latest_roe"] is not None:
        if out["latest_roe"] >= A_BADGE_ROE_EXCELLENT:
            out["badges"].append("탁월 ROE")
        elif out["latest_roe"] >= A_BADGE_ROE_GLOBAL:
            out["badges"].append("글로벌 ROE")
    score = out["earnings_stability_score"]
    if score is not None:
        if score < A_STABILITY_EXCELLENT_MAX:
            out["badges"].append("안정성 우수")
        elif score <= A_STABILITY_MODERATE_MAX:
            out["badges"].append("안정성 보통")
        else:
            out["badges"].append("안정성 부족")

    return out


def evaluate_a_detailed(
    annual_eps: list[tuple[str, float]],
    annual_roe: list[tuple[str, float]],
    annual_cps: list[tuple[str, float]],
    latest_quarter_yoy: float | None,
    induty_code: str | None,
    quarterly_eps_for_stability: list[float] | None = None,
) -> dict:
    """A 메인 트랙 평가 + 가점 배지용 raw 값 추출.

    메인 트랙 통과 조건 (모두 충족):
      1. 최근 3년 연속 EPS 매년 증가 (감소 연도 0개)
      2. 3년 평균 연 EPS 증가율 ≥ 25%
      3. 가장 최근 ROE ≥ 17%
      4. 직전 분기 EPS YoY ≥ 3년 평균 EPS 증가율 × 1/3 (성장 둔화 게이트)
      5. KSIC 산업 코드가 경기민감주 prefix(24/20/17/22/29) 미해당
    """
    out: dict[str, Any] = {
        "main_track_pass": False,
        "annual_eps": [(k, round(v, 2)) for k, v in annual_eps[-5:]],
        "annual_roe": [(k, round(v, 2)) for k, v in annual_roe[-5:]],
        "annual_cps": [(k, round(v, 2)) for k, v in annual_cps[-5:]] if annual_cps else [],
        "three_year_growths": [],
        "three_year_avg_growth": None,
        "five_year_consecutive_increase": False,
        "consecutive_3y_increase": False,
        "latest_roe": None,
        "latest_cps": None,
        "latest_eps": None,
        "latest_cps_eps_ratio": None,
        "latest_quarter_yoy": latest_quarter_yoy,
        "deceleration_gate_pass": False,
        "deceleration_gate_threshold": None,
        "induty_code": induty_code,
        "cyclical": is_cyclical_industry(induty_code),
        "earnings_stability_score": None,
        "earnings_stability_detail": "",
        "badges": [],
        "fail_reasons": [],
    }

    # 1) 3년 EPS 연속 증가 + 평균 증가율
    if len(annual_eps) >= 4:
        recent_4 = annual_eps[-4:]  # 4개 연도 → 3개 YoY
        all_increase = True
        growths: list[float] = []
        broken = False
        for i in range(1, 4):
            prev_key, prev_v = recent_4[i - 1]
            curr_key, curr_v = recent_4[i]
            if prev_v <= 0:
                out["fail_reasons"].append(f"{prev_key} 적자")
                all_increase = False
                broken = True
                break
            if curr_v <= prev_v:
                all_increase = False
            g = (curr_v - prev_v) / prev_v * 100
            growths.append(round(g, 2))
        out["three_year_growths"] = growths
        out["consecutive_3y_increase"] = all_increase and not broken
        if growths:
            out["three_year_avg_growth"] = round(sum(growths) / len(growths), 2)
    else:
        out["fail_reasons"].append(f"연간 EPS 데이터 부족 ({len(annual_eps)}년, 4년 필요)")

    # 5년 연속 증가 (가점 배지) — O'Neil 원전: 위기 1회 dip 다음해 회복 시 면제
    out["five_year_with_crisis_waiver"] = False
    if len(annual_eps) >= 6:
        recent_6 = annual_eps[-6:]
        values = [v for _, v in recent_6]
        # 적자 끼면 위기 면제 미적용 (적자는 별개 문제)
        if all(v > 0 for v in values):
            # strict 단조 증가 우선 체크
            if all(values[i] > values[i - 1] for i in range(1, len(values))):
                out["five_year_consecutive_increase"] = True
            else:
                # 1회 위기 dip 면제 룰
                dip_indices = [i for i in range(1, len(values)) if values[i] < values[i - 1]]
                if len(dip_indices) == 1:
                    dip_i = dip_indices[0]
                    # dip 이 마지막 해가 아니어야 함 (회복 확인 필요)
                    if dip_i + 1 < len(values) and values[dip_i + 1] >= values[dip_i - 1]:
                        out["five_year_consecutive_increase"] = True
                        out["five_year_with_crisis_waiver"] = True

    # 2) 최신 ROE
    if annual_roe:
        out["latest_roe"] = round(annual_roe[-1][1], 2)

    # 3) CPS / EPS 비율
    if annual_eps:
        out["latest_eps"] = round(annual_eps[-1][1], 2)
    if annual_cps and annual_eps:
        latest_cps = annual_cps[-1][1]
        latest_eps = annual_eps[-1][1]
        out["latest_cps"] = round(latest_cps, 2)
        if latest_eps > 0:
            out["latest_cps_eps_ratio"] = round(latest_cps / latest_eps, 3)

    # 4) 성장 둔화 게이트
    avg_g = out["three_year_avg_growth"]
    qy = out["latest_quarter_yoy"]
    if avg_g is not None and qy is not None:
        gate = avg_g / A_DECELERATION_GATE_DIVISOR
        out["deceleration_gate_threshold"] = round(gate, 2)
        out["deceleration_gate_pass"] = qy >= gate

    # 5) 안정성 지수 (가점 배지용)
    if quarterly_eps_for_stability and len(quarterly_eps_for_stability) >= 12:
        score, detail = compute_earnings_stability(quarterly_eps_for_stability)
        out["earnings_stability_score"] = score
        out["earnings_stability_detail"] = detail

    # 메인 트랙 통과 판정
    pass_eps_consec = out["consecutive_3y_increase"]
    pass_eps_avg = (
        out["three_year_avg_growth"] is not None
        and out["three_year_avg_growth"] >= A_ANNUAL_EPS_GROWTH_MIN_PCT
    )
    pass_roe = out["latest_roe"] is not None and out["latest_roe"] >= A_ROE_MIN_PCT
    pass_decel = out["deceleration_gate_pass"]
    pass_cyclical = not out["cyclical"]

    out["main_track_pass"] = bool(
        pass_eps_consec and pass_eps_avg and pass_roe and pass_decel and pass_cyclical
    )

    if not pass_eps_consec:
        out["fail_reasons"].append("3년 연속 EPS 증가 미충족")
    if not pass_eps_avg:
        avg_str = f"{out['three_year_avg_growth']}%" if out["three_year_avg_growth"] is not None else "N/A"
        out["fail_reasons"].append(f"3년 평균 증가율 {avg_str} (≥{A_ANNUAL_EPS_GROWTH_MIN_PCT}% 필요)")
    if not pass_roe:
        roe_str = f"{out['latest_roe']}%" if out["latest_roe"] is not None else "N/A"
        out["fail_reasons"].append(f"ROE {roe_str} (≥{A_ROE_MIN_PCT}% 필요)")
    if not pass_decel:
        gate_str = f"{out['deceleration_gate_threshold']}%" if out["deceleration_gate_threshold"] is not None else "N/A"
        qy_str = f"{qy}%" if qy is not None else "N/A"
        out["fail_reasons"].append(f"성장 둔화 — 직전 분기 YoY {qy_str} < 3년 평균/3 ({gate_str})")
    if not pass_cyclical:
        out["fail_reasons"].append(f"경기민감주 (KSIC {induty_code})")

    # 가점 배지
    if out["latest_roe"] is not None:
        if out["latest_roe"] >= A_BADGE_ROE_EXCELLENT:
            out["badges"].append("탁월 ROE")
        elif out["latest_roe"] >= A_BADGE_ROE_GLOBAL:
            out["badges"].append("글로벌 ROE")
    if out["five_year_consecutive_increase"]:
        if out.get("five_year_with_crisis_waiver"):
            out["badges"].append("5년 연속 성장 (위기 면제)")
        else:
            out["badges"].append("5년 연속 성장")
    if out["latest_cps_eps_ratio"] is not None and out["latest_cps_eps_ratio"] >= A_BADGE_CPS_EPS_RATIO:
        out["badges"].append("현금창출력 우수")
    score = out["earnings_stability_score"]
    if score is not None:
        if score < A_STABILITY_EXCELLENT_MAX:
            out["badges"].append("안정성 우수")
        elif score <= A_STABILITY_MODERATE_MAX:
            out["badges"].append("안정성 보통")
        else:
            out["badges"].append("안정성 부족")

    return out
