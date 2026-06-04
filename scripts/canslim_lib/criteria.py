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
EPS_DENOMINATOR_FLOOR = 100.0  # YoY 분모 floor (원). prior 절댓값이 100원 미만이면 100원으로
                               # 간주해 near-zero 분모로 인한 YoY 폭주(예: 32000%) 억제.
SALES_DENOMINATOR_FLOOR = 10.0  # 매출 YoY 분모 floor (억). 작년 분기 매출이 10억 미만이면
                                # 10억으로 간주 (= 사실상 휴면). EPS 와 같은 폭주 방지 원리.
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
# 분기 시계열 prior 매칭 (전년 동기 정확 탐색)
# ─────────────────────────────────────────────────
# 이전엔 quarterly_eps[i-4] 식의 단순 인덱스로 prior 를 잡았으나,
# DART backfill 범위가 좁아 시계열에 구멍이 생기면 "인덱스 -4" 가 1년 전이 아니라
# 2년 전 분기를 가리키는 사고가 발생함 (예: 삼지전자 037460). 그래서 period_key
# (YYYYMM) 기준 정확 매칭으로 바꿈. prior 가 시계열에 없으면 그 시점 YoY 는 계산
# 보류(None) — 잘못된 분모로 가짜 YoY 만들지 않음.

def _yoy_prior_key(curr_key: str) -> str | None:
    """'202506' → '202206'. 형식 오류면 None."""
    if not isinstance(curr_key, str) or len(curr_key) != 6 or not curr_key[:4].isdigit():
        return None
    return f"{int(curr_key[:4]) - 1}{curr_key[4:]}"


def _find_yoy_prior(series: list[tuple[str, float]], curr_idx: int) -> int | None:
    """series[curr_idx] 의 정확한 전년 동기 위치. 없으면 None."""
    if curr_idx < 0 or curr_idx >= len(series):
        return None
    prior_key = _yoy_prior_key(series[curr_idx][0])
    if prior_key is None:
        return None
    for j in range(curr_idx - 1, -1, -1):
        if series[j][0] == prior_key:
            return j
    return None


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

    last_idx = len(quarterly_eps) - 1
    latest_key, latest_eps = quarterly_eps[last_idx]

    # 전년 동기 (period_key 기준 정확 매칭)
    yoy_idx = _find_yoy_prior(quarterly_eps, last_idx)
    if yoy_idx is None:
        return False, "데이터 부족", f"{latest_key} 의 전년 동기 ({_yoy_prior_key(latest_key)}) 가 시계열에 없음"
    yoy_key, yoy_eps = quarterly_eps[yoy_idx]

    if yoy_eps <= 0:
        if latest_eps > 0:
            return True, f"흑자전환 ({latest_eps:.0f})", f"{yoy_key} 적자→ {latest_key} 흑자 {latest_eps:.0f}원"
        return False, "양사 적자", f"{yoy_key} {yoy_eps:.0f} → {latest_key} {latest_eps:.0f}"

    growth = (latest_eps - yoy_eps) / yoy_eps * 100
    passed = growth >= C_QUARTERLY_EPS_MIN

    # 직전 분기 가속 체크 — 직전 분기는 시계열의 -2 위치 그대로 OK
    # (시계열이 시간순 정렬이고 구멍 있어도 "직전" 의미는 시계열 상 바로 이전 분기로 정의)
    accel_note = ""
    if len(quarterly_eps) >= 2:
        prev_idx = last_idx - 1
        prev_q_key, prev_q_eps = quarterly_eps[prev_idx]
        yoy_prev_idx = _find_yoy_prior(quarterly_eps, prev_idx)
        if yoy_prev_idx is not None:
            _, yoy_prev_eps = quarterly_eps[yoy_prev_idx]
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
        "eps_accel_quality": "none",
        "eps_yoy_history": [],
        "eps_accel_3q": False,
        "sales_yoy_pct": None,
        "sales_yoy_history": [],
        "sales_accel_3q": False,
        "never_sell": False,
        "eps_new_high": False,
        "consecutive_decline_quarters": 0,
        "severe_decel": False,
        "dilution_flag": dilution_flag,
    }

    if len(quarterly_eps) < 5:
        return out

    last_idx = len(quarterly_eps) - 1
    latest_key, latest_eps = quarterly_eps[last_idx]
    out["latest_quarter"] = latest_key
    out["latest_eps"] = latest_eps

    # 전년 동기 (period_key 정확 매칭)
    yoy_idx = _find_yoy_prior(quarterly_eps, last_idx)
    yoy_eps = quarterly_eps[yoy_idx][1] if yoy_idx is not None else None

    # YoY % 계산: 절댓값 분모 공식 + floor 적용 (분모 |prior| 이 너무 작으면 EPS_DENOMINATOR_FLOOR
    # 로 대체해 32000% 같은 폭주 억제). 단 현재 분기가 적자(latest_eps <= 0)면 C 부적격이므로 None 유지.
    if latest_eps > 0 and yoy_eps is not None and yoy_eps != 0:
        denom = max(abs(yoy_eps), EPS_DENOMINATOR_FLOOR)
        yoy = (latest_eps - yoy_eps) / denom * 100
        out["yoy_pct"] = round(yoy, 2)

    # 직전 분기 YoY (가속 비교용)
    if len(quarterly_eps) >= 2:
        prev_idx = last_idx - 1
        _, prev_q_eps = quarterly_eps[prev_idx]
        yoy_prev_idx = _find_yoy_prior(quarterly_eps, prev_idx)
        if yoy_prev_idx is not None:
            _, yoy_prev_eps = quarterly_eps[yoy_prev_idx]
            if prev_q_eps > 0 and yoy_prev_eps != 0:
                denom = max(abs(yoy_prev_eps), EPS_DENOMINATOR_FLOOR)
                prev_yoy = (prev_q_eps - yoy_prev_eps) / denom * 100
                out["prev_yoy_pct"] = round(prev_yoy, 2)
                if out["yoy_pct"] is not None:
                    out["accel_delta_pp"] = round(out["yoy_pct"] - prev_yoy, 2)
                    if prev_yoy > 0 and out["yoy_pct"] <= prev_yoy / 3:
                        out["severe_decel"] = True

    # 연속 감소 분기 — 정확한 전년 동기 비교만 누적, prior 못 찾으면 streak 중단
    decline_streak = 0
    for i in range(last_idx, max(last_idx - 8, -1), -1):
        prior_idx = _find_yoy_prior(quarterly_eps, i)
        if prior_idx is None:
            break
        _, curr = quarterly_eps[i]
        _, prior = quarterly_eps[prior_idx]
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
        last_s_idx = len(quarterly_sales) - 1
        latest_sales_key, latest_sales = quarterly_sales[last_s_idx]
        yoy_s_idx = _find_yoy_prior(quarterly_sales, last_s_idx)
        if yoy_s_idx is not None:
            _, yoy_sales = quarterly_sales[yoy_s_idx]
            if yoy_sales > 0:
                denom = max(yoy_sales, SALES_DENOMINATOR_FLOOR)
                out["sales_yoy_pct"] = round((latest_sales - yoy_sales) / denom * 100, 2)

    # 가속 판정 헬퍼 — strict 단조 가속만 인정.
    # 최근 3분기 YoY 가 a < b < c 로 점차 빨라지고 최신이 양수여야 가속.
    # 중간 dip 이 있는 케이스(예: +34% → −0.2% → +292%)는 "마지막이 폭발"하더라도
    # 점진 가속이 아니므로 제외. 폭발 자체는 eps_accel_quality(mild/strong/explosive)
    # 가 Δ 크기로 별도 포착하므로 누락 우려 없음 (2026-05-21 폭발 예외 제거).
    def _is_accel(history: list[tuple[str, float]]) -> bool:
        if len(history) < 3:
            return False
        last3 = [v for _, v in history[-3:]]
        return last3[-1] > 0 and last3[0] < last3[1] < last3[2]

    # EPS 분기별 YoY 추세 (최근 5분기 — 정확한 전년 동기 매칭만 사용)
    # 최소 5분기 데이터로 1개 YoY 점 표시 (가속 판정은 _is_accel 이 3점 미만이면 False 반환).
    # 적자 분기도 포함 (절댓값 분모 공식으로 적자 심화/감소/턴어라운드 모두 의미 있음).
    # prior 못 찾는 분기는 history 에서 빠짐 (잘못된 분모로 가짜 YoY 만들지 않음).
    if len(quarterly_eps) >= 5:
        eps_hist: list[tuple[str, float]] = []
        # 최신 5분기까지 (구멍 있어도 가능한 점만 수집)
        for i in range(last_idx, max(last_idx - 5, -1), -1):
            prior_idx = _find_yoy_prior(quarterly_eps, i)
            if prior_idx is None:
                continue
            curr_key, curr = quarterly_eps[i]
            _, prior = quarterly_eps[prior_idx]
            if prior != 0:
                denom = max(abs(prior), EPS_DENOMINATOR_FLOOR)
                eps_hist.append((curr_key, round((curr - prior) / denom * 100, 2)))
        eps_hist.reverse()
        out["eps_yoy_history"] = eps_hist
        out["eps_accel_3q"] = _is_accel(eps_hist)

    # EPS 가속 폭발도 단계 — O'Neil 원전 #3 (가장 중요한 원칙) 정량화.
    # YoY 자체가 절댓값 분모 공식이라 적자→흑자 턴어라운드도 큰 Δ 로
    # 자연 변환됨 → 별도 'recovery' 분기 없이 delta 만으로 단순 분류.
    # (한국 기업의 1년 폭발 흑자전환 케이스를 explosive 로 흡수, 2026-05-20)
    yoy = out["yoy_pct"]
    prev_yoy = out["prev_yoy_pct"]
    delta = out["accel_delta_pp"]
    if yoy is not None and prev_yoy is not None and delta is not None:
        if delta > 100:
            out["eps_accel_quality"] = "explosive"
        elif delta > 25:
            out["eps_accel_quality"] = "strong"
        elif delta > 0:
            out["eps_accel_quality"] = "mild"

    # 매출 분기별 YoY 추세 (최근 5분기 — 정확한 전년 동기 매칭만 사용)
    if quarterly_sales and len(quarterly_sales) >= 5:
        sales_hist: list[tuple[str, float]] = []
        last_s_idx = len(quarterly_sales) - 1
        for i in range(last_s_idx, max(last_s_idx - 5, -1), -1):
            prior_idx = _find_yoy_prior(quarterly_sales, i)
            if prior_idx is None:
                continue
            curr_key, curr = quarterly_sales[i]
            _, prior = quarterly_sales[prior_idx]
            if prior > 0:
                denom = max(prior, SALES_DENOMINATOR_FLOOR)
                sales_hist.append((curr_key, round((curr - prior) / denom * 100, 2)))
        sales_hist.reverse()
        out["sales_yoy_history"] = sales_hist
        out["sales_accel_3q"] = _is_accel(sales_hist)

    # '절대 매도 금지': 매출 + EPS 모두 3분기 가속
    out["never_sell"] = bool(out["sales_accel_3q"] and out["eps_accel_3q"])

    return out


def passes_c_gate(c_detailed: dict) -> bool:
    """C 페이지 노출 게이트 — frontend `src/app/stocks/canslim/lib/cFilter.ts`
    의 `passesCGate()` 와 *반드시 동일* 한 5조건을 평가.

    [doc-logic-sync] 이 함수와 TS 버전은 항상 동기화. 한쪽 변경 시 양쪽 반영.

    5조건 (모두 AND):
      1) yoy_pct ≥ 25
      2) 매출 동반: sales_yoy_pct ≥ 25  OR  sales_accel_3q
      3) EPS 가속 중: eps_accel_quality ∈ {mild, strong, explosive}  OR  eps_accel_3q
      4) consecutive_decline_quarters < 2
      5) NOT severe_decel

    Args:
      c_detailed: `evaluate_c_detailed()` 반환 dict.
    """
    yoy = c_detailed.get("yoy_pct")
    if yoy is None or yoy < C_QUARTERLY_EPS_MIN:
        return False

    sales_yoy = c_detailed.get("sales_yoy_pct")
    sales_accel_3q = bool(c_detailed.get("sales_accel_3q"))
    sales_accompany = (sales_yoy is not None and sales_yoy >= 25) or sales_accel_3q
    if not sales_accompany:
        return False

    q = c_detailed.get("eps_accel_quality")
    quality_accel = q in ("mild", "strong", "explosive")
    accelerating = bool(c_detailed.get("eps_accel_3q")) or quality_accel
    if not accelerating:
        return False

    if (c_detailed.get("consecutive_decline_quarters") or 0) >= 2:
        return False
    if c_detailed.get("severe_decel"):
        return False
    return True


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
# C 충족도 점수 (0~100, 4축)
# ─────────────────────────────────────────────────
# 문서 IMPL_canslim_c_page.md 의 점수 체계 정의를 코드로 옮긴 것.
# 1단계 필터 통과 종목 사이의 우선순위 산출용.

C_AXIS_MAX = {
    "yoy": 42,
    "accel": 38,
    "sales": 20,
}
# 경영진 평가는 A 원칙(ROE) 에서 다룸 — C 스코어에서 제거 (2026-05-21).
# 제거된 7점은 ① YoY 에 +3, ② 가속 에 +3, ③ 매출 에 +1 로 분산.


def _score_c_yoy(yoy: float | None) -> tuple[int, str]:
    """축 ① 분기 EPS YoY 폭 (0~42점)."""
    if yoy is None:
        return 0, "데이터 부족"
    if yoy >= 100:
        return 42, f"+{yoy:.1f}% (≥+100%)"
    if yoy >= 70:
        return 39, f"+{yoy:.1f}% (+70~+100%)"
    if yoy >= 40:
        return 33, f"+{yoy:.1f}% (+40~+70%)"
    if yoy >= 30:
        return 26, f"+{yoy:.1f}% (+30~+40%)"
    if yoy >= 25:
        return 18, f"+{yoy:.1f}% (+25~+30%, 오닐 권장 하한)"
    return 0, f"+{yoy:.1f}% (<+25%, 컷오프 미달)"


def _score_c_accel(
    quality: str | None,
    accel_3q: bool,
    accel_delta_pp: float | None = None,
) -> tuple[float, str]:
    """축 ② EPS 가속 폭. 기본 0~38점 + 폭발 가속 100%p 초과분 보너스 (cap 없음).

    배점:
      - base: explosive 34 / strong 28 / mild 15 / 가속 없음 0
      - 3분기 단조 가속(a < b < c) 시 +4 (base+bonus 가 38 을 넘으면 38 로 cap)
      - 폭발 가속(Δ > 100%p) 한정 추가 보너스: 100%p 초과분에 대해 100 단위마다 +0.5
        (예: Δ=200%p → +0.5, Δ=300%p → +1.0, Δ=500%p → +2.0). 이 보너스는 38점 cap 을
        초과 가능 — 의도적 (사용자 정의, 2026-05-21). Δ 가 극단적으로 크면 축 ② 합계가
        축 ① 42점을 넘어설 수 있음.
    """
    base = 0
    label = "가속 없음"
    if quality == "explosive":
        base, label = 34, "🔥 폭발 가속"
    elif quality == "strong":
        base, label = 28, "▲▲ 강력 가속"
    elif quality == "mild":
        base, label = 15, "▲ 가속"
    bonus_3q = 4 if accel_3q else 0
    capped_base = min(38, base + bonus_3q)

    extra = 0.0
    if quality == "explosive" and accel_delta_pp is not None and accel_delta_pp > 100:
        increments = int((accel_delta_pp - 100) // 100)
        extra = increments * 0.5

    total = float(capped_base) + extra

    parts = [label]
    if accel_3q:
        parts.append(f"3분기 단조 (+{bonus_3q})")
    if extra > 0:
        parts.append(f"가속폭 +{extra:.1f} (Δ {accel_delta_pp:.0f}%p)")
    note = " · ".join(parts)
    return total, note


def _score_c_sales(
    sales_yoy: float | None,
    sales_accel_3q: bool,
    never_sell: bool,
) -> tuple[int, str]:
    """축 ③ 매출 가속 (0~20점). 누적 가산, 캡 20."""
    score = 0
    parts: list[str] = []
    if sales_yoy is not None and sales_yoy >= 25:
        score += 11
        parts.append(f"분기 매출 +{sales_yoy:.1f}% (≥+25%, 11)")
    elif sales_yoy is not None:
        parts.append(f"분기 매출 +{sales_yoy:.1f}% (<+25%, 0)")
    else:
        parts.append("분기 매출 데이터 없음 (0)")
    if sales_accel_3q:
        score += 6
        parts.append("3분기 단조 가속 (+6)")
    if never_sell:
        score += 3
        parts.append("⛔ 매출+EPS 동시 3분기 가속 (+3)")
    score = min(20, score)
    return score, " · ".join(parts)


def compute_c_score(c_detailed: dict, management_quality: str | None = None) -> dict:
    """C 원칙 3축 점수화 (0~100, 폭발 가속 보너스 시 100+ 가능).

    Args:
      c_detailed: evaluate_c_detailed() 결과 dict.
      management_quality: (deprecated) 경영진은 A 원칙(ROE) 에서 평가. C 스코어에서 제거 — 시그니처는
        호환을 위해 유지하지만 무시.

    Returns:
      {
        "total": float 0~100+,
        "breakdown": {"yoy": int, "accel": float, "sales": int},
        "notes": {...},
        "tier": "강력" | "좋음" | "중립" | "약함",
      }
    """
    del management_quality  # 의도적 무시 (2026-05-21 — A 원칙 ROE 로 이전)

    yoy = c_detailed.get("yoy_pct")
    quality = c_detailed.get("eps_accel_quality")
    accel_3q = bool(c_detailed.get("eps_accel_3q"))
    sales_yoy = c_detailed.get("sales_yoy_pct")
    sales_accel_3q = bool(c_detailed.get("sales_accel_3q"))
    never_sell = bool(c_detailed.get("never_sell"))

    accel_delta_pp = c_detailed.get("accel_delta_pp")

    yoy_score, yoy_note = _score_c_yoy(yoy)
    accel_score, accel_note = _score_c_accel(quality, accel_3q, accel_delta_pp)
    sales_score, sales_note = _score_c_sales(sales_yoy, sales_accel_3q, never_sell)

    total = yoy_score + accel_score + sales_score

    if total >= 80:
        tier = "강력"
    elif total >= 70:
        tier = "좋음"
    elif total >= 50:
        tier = "중립"
    else:
        tier = "약함"

    return {
        "total": total,
        "breakdown": {
            "yoy": yoy_score,
            "accel": accel_score,
            "sales": sales_score,
        },
        "notes": {
            "yoy": yoy_note,
            "accel": accel_note,
            "sales": sales_note,
        },
        "tier": tier,
    }


# ─────────────────────────────────────────────────
# 통합 평가
# ─────────────────────────────────────────────────

CRITERIA_KEYS = ["C", "A", "N", "S", "L", "I", "M"]
