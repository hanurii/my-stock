"""CAN SLIM 7기준 판정 함수 — 한국 시장 보정판 (v1).

각 함수는 (passed: bool, value: str, detail: str) 튜플을 반환.

원전 vs 한국 보정:
- C, A의 EPS 성장률, N, L의 RS — 원전 그대로
- A의 ROE 17% → 15% (한국 trailing ROE 평균 ~9% 고려)
- S의 거래량 surge 50% → 30% (한국 시장 평균 돌파 거래량)
- I 외인+기관 합산 보유율 5%+ + 추세 (단순 외인 proxy → 실제 합산)
"""

from __future__ import annotations

import statistics
from typing import Any

# ── 임계값 (한국 보정판 v1) ──

C_QUARTERLY_EPS_MIN = 25.0   # 분기 EPS YoY +25% 이상 (원전 유지)
A_ANNUAL_EPS_MIN = 25.0       # 연간 EPS 3년 +25% 이상 (원전 유지)
A_ROE_MIN = 15.0              # ROE 15% 이상 (한국 보정: 17 → 15)
N_HIGH_PROXIMITY_MAX = 15.0   # 52주 고점에서 15% 이내 (원전 유지)
S_VOLUME_SURGE_MIN = 30.0     # 거래량 +30% 급증 (한국 보정: 50 → 30)
S_SHARES_MAX_M = 50.0         # 유통주식수 5천만주 미만 (참고용, 한국에선 시총으로 대체)
L_RS_MIN = 80.0               # 상대강도 80 이상 (원전 유지, universe 백분위 정확 계산)
I_COMBINED_HOLDING_MIN = 5.0  # 외인+기관 합산 보유율 5% 이상 (한국 보정)


def _fmt_pct(v: float) -> str:
    return f"{v:+.1f}%"


# ─────────────────────────────────────────────────
# C: Current Quarterly Earnings
# ─────────────────────────────────────────────────

def evaluate_c(quarterly_eps: list[tuple[str, float]]) -> tuple[bool, str, str]:
    """최근 분기 EPS의 전년 동기 대비 성장률.

    Args:
      quarterly_eps: [(period_key, eps), ...] — 시간순. period_key는 'YYYYMM' 형식.

    "분기 EPS YoY +25% 이상" + 가속(직전 분기보다 더 높은 성장률)이면 통과.
    """
    if len(quarterly_eps) < 5:
        return False, "데이터 부족", f"분기 EPS 데이터 {len(quarterly_eps)}개 — YoY 비교에 5개 필요"

    latest_key, latest_eps = quarterly_eps[-1]
    # 전년 동기 (4분기 전)
    yoy_key, yoy_eps = quarterly_eps[-5]

    if yoy_eps <= 0:
        if latest_eps > 0:
            return True, f"흑자전환 ({latest_eps:.0f})", f"{yoy_key} 적자→ {latest_key} 흑자 {latest_eps:.0f}원"
        return False, "양사 적자", f"{yoy_key} {yoy_eps:.0f} → {latest_key} {latest_eps:.0f}"

    growth = (latest_eps - yoy_eps) / yoy_eps * 100
    passed = growth >= C_QUARTERLY_EPS_MIN

    # 가속 체크
    accel_note = ""
    if len(quarterly_eps) >= 6:
        prev_q_key, prev_q_eps = quarterly_eps[-2]
        yoy_prev_key, yoy_prev_eps = quarterly_eps[-6]
        if yoy_prev_eps > 0:
            prev_growth = (prev_q_eps - yoy_prev_eps) / yoy_prev_eps * 100
            if growth > prev_growth:
                accel_note = f", 직전분기 {_fmt_pct(prev_growth)} → 가속"
            else:
                accel_note = f", 직전분기 {_fmt_pct(prev_growth)} → 둔화"

    value = _fmt_pct(growth)
    detail = f"{yoy_key} EPS {yoy_eps:.0f} → {latest_key} {latest_eps:.0f} = YoY {value}{accel_note}"
    return passed, value, detail


def evaluate_c_detailed(
    quarterly_eps: list[tuple[str, float]],
    quarterly_sales: list[tuple[str, float]] | None = None,
    dilution_flag: bool | None = None,
) -> dict:
    """C 원칙(분기 EPS) raw 사실값 추출. 등급화·점수화 없음.

    호출자가 페이지에서 정렬·필터·노출제외에 사용한다.
    quarterly_eps, quarterly_sales: [(period_key, value), ...] 시간순.
    """
    out: dict = {
        "yoy_pct": None,
        "latest_quarter": None,
        "latest_eps": None,
        "prev_yoy_pct": None,
        "accel_delta_pp": None,
        "sales_yoy_pct": None,
        "eps_new_high": False,
        "consecutive_decline_quarters": 0,
        "severe_decel": False,
        "is_turnaround": False,
        "dilution_flag": dilution_flag,
    }

    if len(quarterly_eps) < 5:
        return out

    latest_key, latest_eps = quarterly_eps[-1]
    yoy_key, yoy_eps = quarterly_eps[-5]
    out["latest_quarter"] = latest_key
    out["latest_eps"] = latest_eps
    out["is_turnaround"] = (yoy_eps < 0 and latest_eps > 0)

    # YoY % 계산: 절댓값 분모 공식 사용 (흑자전환도 일반 종목과 동일하게 비교 가능)
    # 단 현재 분기가 적자(latest_eps <= 0)면 C 부적격이므로 None 유지.
    if latest_eps > 0 and yoy_eps != 0:
        yoy = (latest_eps - yoy_eps) / abs(yoy_eps) * 100
        out["yoy_pct"] = round(yoy, 2)

    # 직전 분기 YoY (가속 비교용)
    if len(quarterly_eps) >= 6:
        _, prev_q_eps = quarterly_eps[-2]
        _, yoy_prev_eps = quarterly_eps[-6]
        if prev_q_eps > 0 and yoy_prev_eps != 0:
            prev_yoy = (prev_q_eps - yoy_prev_eps) / abs(yoy_prev_eps) * 100
            out["prev_yoy_pct"] = round(prev_yoy, 2)
            if out["yoy_pct"] is not None:
                out["accel_delta_pp"] = round(out["yoy_pct"] - prev_yoy, 2)
                if prev_yoy > 0 and out["yoy_pct"] <= prev_yoy / 3:
                    out["severe_decel"] = True

    decline_streak = 0
    for i in range(len(quarterly_eps) - 1, max(len(quarterly_eps) - 9, 3), -1):
        if i - 4 < 0:
            break
        _, curr = quarterly_eps[i]
        _, prior = quarterly_eps[i - 4]
        if prior > 0 and curr < prior:
            decline_streak += 1
        else:
            break
    out["consecutive_decline_quarters"] = decline_streak

    if len(quarterly_eps) >= 8:
        recent_4 = [eps for _, eps in quarterly_eps[-4:]]
        prior_window = [eps for _, eps in quarterly_eps[:-4]]
        if prior_window:
            prior_max = max(prior_window)
            new_high_count = sum(1 for v in recent_4 if v >= prior_max * 0.95)
            out["eps_new_high"] = new_high_count >= 3

    if quarterly_sales and len(quarterly_sales) >= 5:
        latest_sales_key, latest_sales = quarterly_sales[-1]
        _, yoy_sales = quarterly_sales[-5]
        if yoy_sales > 0:
            out["sales_yoy_pct"] = round((latest_sales - yoy_sales) / yoy_sales * 100, 2)

    return out


# ─────────────────────────────────────────────────
# A: Annual Earnings
# ─────────────────────────────────────────────────

def evaluate_a(annual_eps: list[tuple[str, float]], annual_roe: list[tuple[str, float]]) -> tuple[bool, str, str]:
    """연간 EPS 3년 이상 +25% 성장 + ROE 17%+.

    원전: "최근 3년간 연간 EPS 25%+ 성장 AND ROE ≥ 17%"
    여기선 두 조건 모두 충족해야 pass.
    """
    if len(annual_eps) < 3:
        return False, "데이터 부족", f"연간 EPS 데이터 {len(annual_eps)}개 — 3년 필요"

    # 3개년 EPS YoY 성장률
    growths: list[float] = []
    failures: list[str] = []
    for i in range(len(annual_eps) - 2, len(annual_eps)):
        prev_key, prev_eps = annual_eps[i - 1]
        curr_key, curr_eps = annual_eps[i]
        if prev_eps <= 0:
            failures.append(f"{prev_key} 적자")
            continue
        g = (curr_eps - prev_eps) / prev_eps * 100
        growths.append(g)

    eps_pass = len(growths) >= 2 and all(g >= A_ANNUAL_EPS_MIN for g in growths)

    # 최근 ROE
    latest_roe = annual_roe[-1][1] if annual_roe else 0.0
    roe_pass = latest_roe >= A_ROE_MIN

    passed = eps_pass and roe_pass

    eps_summary = ", ".join(f"{_fmt_pct(g)}" for g in growths) if growths else "계산불가"
    eps_periods = " → ".join(f"{k}:{v:.0f}" for k, v in annual_eps[-3:])

    value = f"EPS 3y {eps_summary} / ROE {latest_roe:.1f}%"
    detail = (
        f"EPS {eps_periods} ({'통과' if eps_pass else '미달, 25%+ 필요'}) | "
        f"ROE {latest_roe:.1f}% ({'통과' if roe_pass else f'미달, {A_ROE_MIN}%+ 필요'})"
    )
    if failures:
        detail += f" | 이슈: {', '.join(failures)}"
    return passed, value, detail


# ─────────────────────────────────────────────────
# N: New highs / New something
# ─────────────────────────────────────────────────

def evaluate_n(closes: list[float]) -> tuple[bool, str, str]:
    """52주 고점의 15% 이내에 있는지.

    Args:
      closes: 52주 (약 250 영업일) 일봉 종가. 시간순.

    "52주 신고가의 15% 이내" + 베이스 후 돌파 구간이면 통과.
    """
    if len(closes) < 50:
        return False, "데이터 부족", f"가격 데이터 {len(closes)}일 — 52주 분석에 부족"

    high = max(closes)
    last = closes[-1]
    if high <= 0:
        return False, "가격 이상", "52주 고점 0 이하"

    distance_pct = (high - last) / high * 100
    passed = distance_pct <= N_HIGH_PROXIMITY_MAX

    # 신고가 근접 + 최근 5일 평균이 50일 평균 위인지 (모멘텀)
    recent_avg = sum(closes[-5:]) / 5
    base_avg = sum(closes[-50:]) / min(50, len(closes))
    momentum = "상승 모멘텀" if recent_avg > base_avg else "약세"

    value = f"52주 고점 -{distance_pct:.1f}%"
    detail = f"고점 {high:,.0f}, 현재 {last:,.0f}, 갭 -{distance_pct:.1f}% | {momentum} (5일avg {recent_avg:,.0f} vs 50일avg {base_avg:,.0f})"
    return passed, value, detail


# ─────────────────────────────────────────────────
# S: Supply & Demand (volume surge)
# ─────────────────────────────────────────────────

def evaluate_s(volumes: list[int], market_cap_eok: float) -> tuple[bool, str, str]:
    """수급: 거래량 급증 + 시가총액(유통주식수 proxy).

    원전 5천만주 미만 기준은 한국 KOSPI 대형주에선 거의 다 미달이라
    여기선 보조 지표로만 사용. 핵심은 거래량 급증.
    """
    if len(volumes) < 50:
        return False, "데이터 부족", f"거래량 {len(volumes)}일"

    recent5 = volumes[-5:]
    base50 = volumes[-55:-5] if len(volumes) >= 55 else volumes[:-5]
    recent_avg = sum(recent5) / len(recent5) if recent5 else 0
    base_avg = sum(base50) / len(base50) if base50 else 0
    if base_avg <= 0:
        return False, "거래량 이상", "기준 평균 0"

    surge_pct = (recent_avg - base_avg) / base_avg * 100
    volume_pass = surge_pct >= S_VOLUME_SURGE_MIN

    # 시총 보조 (1조 = 1만 억 미만이면 유통주식수 적은 편으로 가산)
    small_float = market_cap_eok < 30000  # 3조 미만 = 중소형
    cap_note = "중소형 (수급 영향 큼)" if small_float else "대형 (수급 영향 작음)"

    passed = volume_pass  # 거래량 급증을 핵심 조건으로
    value = f"거래량 {_fmt_pct(surge_pct)}"
    detail = f"최근 5일 평균 {recent_avg:,.0f}주 vs 50일 평균 {base_avg:,.0f}주 = {_fmt_pct(surge_pct)} | 시총 {market_cap_eok:,.0f}억 ({cap_note})"
    return passed, value, detail


# ─────────────────────────────────────────────────
# L: Leader (Relative Strength)
# ─────────────────────────────────────────────────

def evaluate_l(stock_closes: list[float], index_closes: list[float], universe_returns: list[float] | None = None) -> tuple[bool, str, str]:
    """상대강도(RS) 계산.

    원전: 12개월 수익률을 전 종목과 비교한 백분위. RS 80+면 상위 20%.
    universe_returns가 주어지면 백분위로 RS 계산. 없으면 KOSPI 대비 초과수익으로 근사.
    """
    if len(stock_closes) < 200 or len(index_closes) < 200:
        return False, "데이터 부족", f"가격 {len(stock_closes)}일 / 지수 {len(index_closes)}일"

    stock_return = (stock_closes[-1] - stock_closes[0]) / stock_closes[0] * 100
    index_return = (index_closes[-1] - index_closes[0]) / index_closes[0] * 100
    excess = stock_return - index_return

    if universe_returns:
        # 백분위 = 자기보다 낮은 수익률 비중 * 100
        rank = sum(1 for r in universe_returns if r < stock_return) / len(universe_returns) * 100
        passed = rank >= L_RS_MIN
        value = f"RS {rank:.0f}"
        detail = f"12M 수익률 {_fmt_pct(stock_return)} (지수 {_fmt_pct(index_return)}, 초과 {_fmt_pct(excess)}) | RS {rank:.0f} ({'통과' if passed else f'미달, {L_RS_MIN:.0f}+ 필요'})"
    else:
        # 임시: 지수 대비 초과수익 +20%면 통과
        passed = excess >= 20.0
        value = f"초과수익 {_fmt_pct(excess)}"
        detail = f"종목 {_fmt_pct(stock_return)} vs 지수 {_fmt_pct(index_return)} = 초과 {_fmt_pct(excess)} (RS 백분위 미계산, +20% 임계)"

    return passed, value, detail


# ─────────────────────────────────────────────────
# I: Institutional Sponsorship
# ─────────────────────────────────────────────────

def evaluate_i(
    foreign_ownership: float,
    institutional_ownership: float | None = None,
    recent_trend: str | None = None,
) -> tuple[bool, str, str]:
    """기관 매집: 외인 + 기관 합산 보유율 + 최근 추세.

    원전: 기관 보유 5%+ 및 분기 증가 추세.
    한국 보정: DART 5%룰 공시 기반 기관 보유율 + 외인소진율 합산.
    institutional_ownership=None이면 외인 단독으로 판정 (DART fallback).
    recent_trend: 'up' / 'flat' / 'down' / None — 최근 합산 보유율 추세.
    """
    inst = institutional_ownership if institutional_ownership is not None else 0.0
    combined = foreign_ownership + inst

    # 보유율 기준
    holding_pass = combined >= I_COMBINED_HOLDING_MIN

    # 추세 기준 (정보 없으면 보유율만으로 판정)
    if recent_trend == "down":
        trend_pass = False
    else:
        trend_pass = True  # up/flat/None은 통과 처리

    passed = holding_pass and trend_pass

    inst_part = f", 기관 {inst:.1f}%" if institutional_ownership is not None else ", 기관 N/A"
    trend_part = f", 추세 {recent_trend}" if recent_trend else ""
    value = f"외인 {foreign_ownership:.1f}%{inst_part}"
    detail = (
        f"외인 {foreign_ownership:.1f}%{inst_part} = 합산 {combined:.1f}%{trend_part} | "
        f"{'통과' if passed else f'미달, 합산 {I_COMBINED_HOLDING_MIN}%+ 필요'}"
    )
    return passed, value, detail


# ─────────────────────────────────────────────────
# M: Market Direction
# ─────────────────────────────────────────────────

def evaluate_m(index_closes: list[float]) -> tuple[bool, str, str]:
    """KOSPI 추세 판정. 200일 이평선 위 + 50일선이 200일선 위면 상승 추세.

    Stage 2 uptrend 정의:
    - 종가 > 200일 SMA
    - 50일 SMA > 200일 SMA
    - 200일 SMA가 최근 1개월간 상승 중

    하나라도 미충족이면 압력/조정 단계로 분류.
    """
    if len(index_closes) < 220:
        return False, "데이터 부족", f"지수 {len(index_closes)}일 — 200일선 분석 불가"

    sma50 = sum(index_closes[-50:]) / 50
    sma200 = sum(index_closes[-200:]) / 200
    sma200_1m_ago = sum(index_closes[-220:-20]) / 200
    last = index_closes[-1]

    above_200 = last > sma200
    sma50_above_200 = sma50 > sma200
    sma200_rising = sma200 > sma200_1m_ago

    if above_200 and sma50_above_200 and sma200_rising:
        verdict = "확정 상승 추세 (Stage 2)"
        passed = True
    elif above_200 and sma50_above_200:
        verdict = "상승 추세, 200일선 횡보"
        passed = True
    elif above_200:
        verdict = "200일선 위, 단기 압력"
        passed = False
    else:
        verdict = "조정 단계 (Stage 4)"
        passed = False

    value = verdict
    detail = (
        f"종가 {last:,.1f} | 50일선 {sma50:,.1f} | 200일선 {sma200:,.1f} (1M 전 {sma200_1m_ago:,.1f}) | "
        f"종가>200일선={above_200}, 50일>200일={sma50_above_200}, 200일선 상승={sma200_rising}"
    )
    return passed, value, detail


# ─────────────────────────────────────────────────
# 통합 평가
# ─────────────────────────────────────────────────

CRITERIA_KEYS = ["C", "A", "N", "S", "L", "I", "M"]
