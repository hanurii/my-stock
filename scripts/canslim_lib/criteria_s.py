"""CAN SLIM 'S' 원칙 (Supply and Demand) 평가.

격리 원칙 (`feedback_canslim_letter_isolation`):
- C/A/N 데이터·게이트 미사용. S 자체 데이터만 사용.

수집 항목 (사용자 확정 컷오프):
1. 발행주식수 (시총/주가 추계) + 유통물량 비율 (추계)
2. 최고 경영진 보유 % (DART majorstock 최대주주+특수관계인 합산)
3. 자사주 매입 최근 3년 (DART list.json report_nm 필터)
4. 부채비율 (Naver 분기/연간 "부채비율" 행)
5. 부채 추세 (5분기 + 3년)
6. 주식 분할 최근 5년 (DART list.json "주식분할" 필터)

필터 / 라벨:
- 필터(제외): 5년 내 분할 3회 이상.
- 필터(TBD): 부채비율 > {N 통과 분포 분석 후}.
- 라벨: 자사주 10%+ 매입, 분할 1~2회 주의, 부채 감소 (기준값 TBD).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from canslim_lib.fetch import (
    NAVER_API,
    NAVER_HEADERS,
    _http_get_json,
    dart_get,
    fetch_annual,
    fetch_quarter,
    get_row_values,
)


# ── 금융기관 식별 (부채비율 컷오프 면제) ──
# KSIC 대분류 K = 금융 및 보험업
#   64 = 금융업 (은행·신탁·자산운용)
#   65 = 보험 및 연금업
#   66 = 금융 및 보험 관련 서비스업 (증권·선물중개)
# 금융기관은 사업 구조상 고객 예수금·RP 등이 부채로 잡혀 800~1,200%가 정상 수준.
# 책의 "감당 못할 빚 금지" 원칙은 제조업·서비스업 기준이라 그대로 적용 불가.
FINANCIAL_KSIC_PREFIXES = ("64", "65", "66")


def is_financial_industry(induty_code: str | None) -> bool:
    if not induty_code or len(induty_code) < 2:
        return False
    return induty_code[:2] in FINANCIAL_KSIC_PREFIXES


# ── 부채비율 (Naver 재무표) ──

def fetch_debt_ratio_series(code: str) -> dict[str, list[tuple[str, float]]]:
    """Naver 분기/연간 재무표에서 "부채비율" 행 추출.

    Returns:
      {
        "quarterly": [(period_key, value), ...],   # 최근 5~8분기
        "annual": [(period_key, value), ...],       # 최근 3~5년
      }
    부채비율은 Naver 표준 정의(총부채/자기자본 × 100, %).
    """
    out: dict[str, list[tuple[str, float]]] = {"quarterly": [], "annual": []}
    q = fetch_quarter(code)
    if q:
        out["quarterly"] = get_row_values(q, "부채비율")
    a = fetch_annual(code)
    if a:
        out["annual"] = get_row_values(a, "부채비율")
    return out


def compute_debt_reduction_label(
    quarterly: list[tuple[str, float]],
    annual: list[tuple[str, float]],
    threshold_pp: float | None,
) -> dict[str, Any]:
    """부채 감소 라벨 평가 — 분기·연간 2개 라벨 독립.

    라벨 (각각 독립 부여):
      - "연간 부채 크게 감소": 최근 2~3년간 연간 부채비율을 threshold_pp %p 이상 낮춤.
      - "분기 부채 크게 감소": 최근 5분기간 분기 부채비율을 threshold_pp %p 이상 낮춤.

    threshold_pp 미지정 시 두 라벨 모두 False.
    delta = oldest - latest. 양수면 부채 감소.
    """
    result = {
        "annual_delta": None,
        "quarterly_delta": None,
        "annual_label": False,
        "quarterly_label": False,
        "applies": False,  # 호환용 — 둘 중 하나라도 True 면 True
    }
    if annual and len(annual) >= 2:
        recent_3 = annual[-3:]
        delta = recent_3[0][1] - recent_3[-1][1]
        result["annual_delta"] = round(delta, 2)
    if quarterly and len(quarterly) >= 2:
        recent_5q = quarterly[-5:]
        delta = recent_5q[0][1] - recent_5q[-1][1]
        result["quarterly_delta"] = round(delta, 2)
    if threshold_pp is None:
        return result
    if result["annual_delta"] is not None and result["annual_delta"] >= threshold_pp:
        result["annual_label"] = True
    if result["quarterly_delta"] is not None and result["quarterly_delta"] >= threshold_pp:
        result["quarterly_label"] = True
    result["applies"] = result["annual_label"] or result["quarterly_label"]
    return result


# ── 경영진 지분 (DART majorstock — 5%룰 대량보유) ──

def fetch_insider_holdings_pct(corp_code: str) -> float | None:
    """DART majorstock (5%룰 대량보유 공시) 에서 최대주주+특수관계인 최종 보유율 합산.

    DART majorstock 응답:
      repror: 보고자명
      stkrt: 보유 비율 (%)
      rcept_dt: 보고일자 YYYYMMDD
    각 보고자의 가장 최근 보고 기준 합산.
    경영진(대표이사) 단독 지분이 아닌 "최대주주 및 특수관계인" 합산 — 한국 시장 보정.
    """
    items = dart_get("majorstock", {"corp_code": corp_code})
    if items is None or not items:
        return None
    by_reporter: dict[str, dict[str, Any]] = {}
    for it in items:
        reporter = (it.get("repror") or "").strip()
        if not reporter:
            continue
        rcept_dt = (it.get("rcept_dt") or "").strip()
        try:
            stkrt = float((it.get("stkrt") or "0").replace(",", ""))
        except (ValueError, AttributeError):
            stkrt = 0.0
        existing = by_reporter.get(reporter)
        if existing is None or rcept_dt > existing["rcept_dt"]:
            by_reporter[reporter] = {"rcept_dt": rcept_dt, "stkrt": stkrt}
    total = sum(r["stkrt"] for r in by_reporter.values())
    return round(total, 2)


# ── 자사주 매입 공시 3년 (DART list.json) ──

def fetch_buyback_disclosures_3y(corp_code: str) -> list[dict[str, Any]]:
    """DART list.json 에서 최근 3년 자기주식취득 관련 공시 조회.

    공시 종류 (report_nm 키워드):
      - "자기주식취득결정"
      - "자기주식취득신탁계약체결결정"
      - "자기주식취득결과보고서"

    Returns: [{"date": "YYYY-MM-DD", "report_nm": str, "rcept_no": str}, ...] 최신순.
    """
    today = datetime.now()
    three_years_ago = today - timedelta(days=365 * 3)
    bgn_de = three_years_ago.strftime("%Y%m%d")
    end_de = today.strftime("%Y%m%d")

    out: list[dict[str, Any]] = []
    page_no = 1
    while True:
        items = dart_get("list", {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": "100",
            "page_no": str(page_no),
        })
        if not items:
            break
        for it in items:
            nm = (it.get("report_nm") or "").strip()
            # "기재정정" 제외 (원본과 중복)
            if "자기주식취득" in nm and "기재정정" not in nm and "[기재정정]" not in nm:
                rdt = (it.get("rcept_dt") or "").strip()
                date_iso = f"{rdt[:4]}-{rdt[4:6]}-{rdt[6:8]}" if len(rdt) == 8 else rdt
                out.append({
                    "date": date_iso,
                    "report_nm": nm,
                    "rcept_no": (it.get("rcept_no") or "").strip(),
                })
        if len(items) < 100:
            break
        page_no += 1
        if page_no > 5:  # 안전 한도
            break
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def fetch_treasury_stock_pct(corp_code: str, year: int) -> float | None:
    """DART tesstkAcqsDsposSttus 사업보고서 정기공시 — 자기주식 보유 비율.

    Returns: 발행주식수 대비 자기주식 보유 비율 (%) 또는 None.
    11011=사업보고서, 11013=1Q, 11012=반기, 11014=3Q.
    가장 최신 정기보고서 우선.
    """
    for reprt_code in ("11011", "11014", "11012", "11013"):
        items = dart_get("tesstkAcqsDsposSttus", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
        })
        if not items:
            continue
        total_treasury = 0.0
        total_shares = 0.0
        for it in items:
            try:
                # stock_knd 가 "보통주" 인 항목만 (우선주 제외)
                if "보통주" not in (it.get("stock_knd") or ""):
                    continue
                bsis_qy = (it.get("bsis_qy") or "0").replace(",", "")  # 기초수량
                trmend_qy = (it.get("trmend_qy") or "0").replace(",", "")  # 기말수량
                total_treasury += float(trmend_qy or bsis_qy)
            except (ValueError, AttributeError):
                continue
        if total_treasury > 0:
            # 발행주식수는 별도 API 또는 시총/주가로 추계 — 호출 측에서 비율 계산하도록 raw 만 반환
            return total_treasury
    return None


# ── 주식 분할 공시 5년 (DART list.json) ──

def fetch_stock_splits_5y(corp_code: str) -> list[dict[str, Any]]:
    """DART list.json 에서 최근 5년 주식분할 관련 공시 조회.

    공시 종류 (report_nm 키워드): "주식분할", "액면분할".

    Returns: [{"date": "YYYY-MM-DD", "report_nm": str}, ...] 최신순.
    """
    today = datetime.now()
    five_years_ago = today - timedelta(days=365 * 5)
    bgn_de = five_years_ago.strftime("%Y%m%d")
    end_de = today.strftime("%Y%m%d")

    out: list[dict[str, Any]] = []
    page_no = 1
    while True:
        items = dart_get("list", {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": "100",
            "page_no": str(page_no),
        })
        if not items:
            break
        for it in items:
            nm = (it.get("report_nm") or "").strip()
            # "주식분할결정", "액면분할결정", "주식분할" 등 매칭
            # "주식병합" 제외 (병합은 별개)
            if ("주식분할" in nm or "액면분할" in nm) and "병합" not in nm:
                rdt = (it.get("rcept_dt") or "").strip()
                date_iso = f"{rdt[:4]}-{rdt[4:6]}-{rdt[6:8]}" if len(rdt) == 8 else rdt
                out.append({
                    "date": date_iso,
                    "report_nm": nm,
                    "rcept_no": (it.get("rcept_no") or "").strip(),
                })
        if len(items) < 100:
            break
        page_no += 1
        if page_no > 5:
            break
    # "결정" 공시만 count, 정정공시는 제외 (원본 + 기재정정이 같은 결정이라 중복)
    decisions = [
        d for d in out
        if "결정" in d["report_nm"]
        and "기재정정" not in d["report_nm"]
        and "[기재정정]" not in d["report_nm"]
    ]
    # 같은 날짜의 중복 공시도 정리 (안전)
    seen_dates: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for d in decisions:
        if d["date"] not in seen_dates:
            seen_dates.add(d["date"])
            deduped.append(d)
    deduped.sort(key=lambda x: x["date"], reverse=True)
    return deduped


# ── S 평가 메인 함수 ──

def evaluate_s(
    code: str,
    corp_code: str | None,
    market_cap_eok: float,
    current_price: float,
    *,
    induty_code: str | None = None,  # KSIC. '64·65·66' prefix면 부채비율 컷오프 면제
    debt_ratio_threshold: float | None = None,  # None 이면 필터 미적용
    debt_reduction_threshold_pp: float | None = None,  # None 이면 라벨 미적용
) -> dict[str, Any]:
    """S 원칙 평가. 데이터 수집 + 라벨·필터 계산.

    Returns:
      {
        "shares_outstanding": float|None,
        "insider_pct": float|None,
        "float_ratio_estimated": float|None,  # 1 - insider_pct/100 추계
        "buyback_3y": list[dict],
        "buyback_count_3y": int,
        "buyback_large_label": bool,
        "treasury_stock_pct_estimated": float|None,
        "debt_ratio_current": float|None,
        "debt_ratio_quarterly": list[tuple[str, float]],
        "debt_ratio_annual": list[tuple[str, float]],
        "debt_reduction": dict,
        "debt_reduction_label": bool,
        "splits_5y": list[dict],
        "splits_5y_count": int,
        "split_warning_label": bool,  # 1~2회
        "split_exclude": bool,         # 3회+ 필터링
        "debt_ratio_excessive": bool,  # TBD 컷오프 초과 시 True
        "pass_s": bool,                # 모든 필터 통과 여부
        "fail_reasons": list[str],
      }
    """
    result: dict[str, Any] = {
        "shares_outstanding": None,
        "insider_pct": None,
        "float_ratio_estimated": None,
        "buyback_3y": [],
        "buyback_count_3y": 0,
        "buyback_large_label": False,
        "treasury_stock_pct_estimated": None,
        "debt_ratio_current": None,
        "debt_ratio_quarterly": [],
        "debt_ratio_annual": [],
        "debt_reduction": {
            "applies": False,
            "annual_delta": None,
            "quarterly_delta": None,
            "annual_label": False,
            "quarterly_label": False,
        },
        "debt_reduction_annual_label": False,
        "debt_reduction_quarterly_label": False,
        "debt_reduction_label": False,  # 호환 — 둘 중 하나라도 True 면 True
        "splits_5y": [],
        "splits_5y_count": 0,
        "split_warning_label": False,
        "split_exclude": False,
        "debt_ratio_excessive": False,
        "is_financial": False,
        "induty_code": induty_code,
        "badges": [],
        "pass_s": True,
        "fail_reasons": [],
    }

    is_financial = is_financial_industry(induty_code)
    result["is_financial"] = is_financial
    if is_financial:
        result["badges"].append("금융기관")

    # 1) 발행주식수 추계 (시총·주가)
    if market_cap_eok > 0 and current_price > 0:
        result["shares_outstanding"] = round(market_cap_eok * 1e8 / current_price)

    # 2) 부채비율 (Naver)
    debt = fetch_debt_ratio_series(code)
    result["debt_ratio_quarterly"] = debt["quarterly"]
    result["debt_ratio_annual"] = debt["annual"]
    if debt["quarterly"]:
        result["debt_ratio_current"] = debt["quarterly"][-1][1]
    elif debt["annual"]:
        result["debt_ratio_current"] = debt["annual"][-1][1]

    # 부채 감소 라벨 (분기·연간 2개 독립)
    reduction = compute_debt_reduction_label(
        debt["quarterly"], debt["annual"], debt_reduction_threshold_pp,
    )
    result["debt_reduction"] = reduction
    result["debt_reduction_annual_label"] = reduction["annual_label"]
    result["debt_reduction_quarterly_label"] = reduction["quarterly_label"]
    result["debt_reduction_label"] = reduction["applies"]

    # 부채비율 과도 필터 — 금융기관(KSIC '64·65·66' prefix)은 면제
    if (
        debt_ratio_threshold is not None
        and result["debt_ratio_current"] is not None
        and not is_financial
    ):
        if result["debt_ratio_current"] > debt_ratio_threshold:
            result["debt_ratio_excessive"] = True
            result["pass_s"] = False
            result["fail_reasons"].append(
                f"부채비율 {result['debt_ratio_current']}% > 컷오프 {debt_ratio_threshold}%"
            )

    # 3) DART 의존 항목 — corp_code 있어야
    if corp_code:
        # 경영진 지분 (5%룰 대량보유 합산)
        result["insider_pct"] = fetch_insider_holdings_pct(corp_code)
        if result["insider_pct"] is not None:
            float_ratio = max(0.0, 100.0 - result["insider_pct"])
            result["float_ratio_estimated"] = round(float_ratio, 2)
        time.sleep(0.1)

        # 자사주 매입 공시 3년
        buybacks = fetch_buyback_disclosures_3y(corp_code)
        # "결정" 만 count (결과 보고는 중복)
        decisions = [b for b in buybacks if "결정" in b["report_nm"]]
        result["buyback_3y"] = decisions
        result["buyback_count_3y"] = len(decisions)
        time.sleep(0.1)

        # 자기주식 보유 추계 (가장 최근 사업연도)
        current_year = datetime.now().year
        for y in (current_year, current_year - 1):
            treasury_qy = fetch_treasury_stock_pct(corp_code, y)
            if treasury_qy and result["shares_outstanding"]:
                pct = treasury_qy / result["shares_outstanding"] * 100
                result["treasury_stock_pct_estimated"] = round(pct, 2)
                # 자사주 10% 이상 보유 → "매우 큰 매입" 라벨
                if pct >= 10.0:
                    result["buyback_large_label"] = True
                break
            time.sleep(0.1)

        # 주식 분할 5년
        splits = fetch_stock_splits_5y(corp_code)
        result["splits_5y"] = splits
        result["splits_5y_count"] = len(splits)
        if 1 <= len(splits) <= 2:
            result["split_warning_label"] = True
        elif len(splits) >= 3:
            result["split_exclude"] = True
            result["pass_s"] = False
            result["fail_reasons"].append(
                f"최근 5년 주식분할 {len(splits)}회 (3회 이상 제외)"
            )

    return result
