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
A_ROE_MIN_PCT = 17.0
A_DECELERATION_GATE_DIVISOR = 3.0  # 직전 분기 YoY ≥ 3년 평균 증가율 / 3
A_BADGE_ROE_EXCELLENT = 25.0
A_BADGE_CPS_EPS_RATIO = 1.20
A_STABILITY_EXCELLENT_MAX = 25
A_STABILITY_MODERATE_MAX = 30

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
    2) 평균 절대 편차 / 평균 EPS = 편차율(%)
    3) score = 20 * log10(편차율 + 1) 후 [1, 99] 클램프
    4) 적자 분기 포함 → 평가 불가
    """
    if len(quarterly_eps) < 12:
        return None, f"분기 데이터 {len(quarterly_eps)}개 (12+ 필요)"
    if any(e <= 0 for e in quarterly_eps):
        return None, "적자 분기 포함 — 평가 불가"

    xs = [float(i) for i in range(len(quarterly_eps))]
    slope, intercept = _linear_regression(xs, quarterly_eps)
    deviations = [abs(quarterly_eps[i] - (slope * i + intercept)) for i in range(len(quarterly_eps))]
    mean_dev = sum(deviations) / len(deviations)
    mean_eps = sum(quarterly_eps) / len(quarterly_eps)
    if mean_eps <= 0:
        return None, "평균 EPS 0 이하 — 평가 불가"

    dev_pct = (mean_dev / mean_eps) * 100
    if dev_pct <= 0:
        return 1, "편차 0 (완전 일정)"
    score = max(1, min(99, int(round(20 * math.log10(dev_pct + 1)))))
    return score, f"편차율 {dev_pct:.1f}%"


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

    # 5년 연속 증가 (가점 배지)
    if len(annual_eps) >= 6:
        recent_6 = annual_eps[-6:]
        all_inc = all(
            recent_6[i][1] > recent_6[i - 1][1] and recent_6[i - 1][1] > 0
            for i in range(1, 6)
        )
        out["five_year_consecutive_increase"] = all_inc

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
    if out["latest_roe"] is not None and out["latest_roe"] >= A_BADGE_ROE_EXCELLENT:
        out["badges"].append("우수 ROE")
    if out["five_year_consecutive_increase"]:
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
