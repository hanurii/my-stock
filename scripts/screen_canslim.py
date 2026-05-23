#!/usr/bin/env python3
"""CAN SLIM 한국 시장 스크리너 — 한국 보정판 v1.

윌리엄 오닐의 7기준(C/A/N/S/L/I/M)을 코스피+코스닥에 적용해 점수화.
한국 보정: ROE 17→15, 거래량 surge 50→30, L은 universe 백분위 RS, I는 외인+기관 합산.

사용법:
  python scripts/screen_canslim.py                  # 전체 스캔
  python scripts/screen_canslim.py --limit 50       # 시총 상위 50개만
  python scripts/screen_canslim.py --market-only    # 시장 추세(M)만
  python scripts/screen_canslim.py --ticker 005930  # 단일 종목 리포트
  python scripts/screen_canslim.py --save           # JSON 저장
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    # line_buffering=True: 파이프/리다이렉트시에도 print()마다 flush → 진행 로그 실시간 노출
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
    """프로젝트 루트의 .env 파일에서 환경변수 주입 (이미 설정된 키는 보존)."""
    import os
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from canslim_lib.fetch import (  # noqa: E402
    fetch_annual,
    fetch_dart_annual_financials,
    fetch_dart_quarterly_eps_history,
    fetch_dart_quarterly_sales_history,
    fetch_integration,
    fetch_majorstock_holding,
    fetch_naver_day_chart,
    fetch_preliminary_quarter,
    fetch_quarter,
    fetch_stock_list,
    fetch_yahoo_chart,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    resolve_corp_code,
    yahoo_symbol,
)
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402
from canslim_lib import pdata, stock_cache  # noqa: E402
from canslim_lib.criteria import (  # noqa: E402
    A_ROE_MIN,
    C_QUARTERLY_EPS_MIN,
    A_ANNUAL_EPS_MIN,
    CRITERIA_KEYS,
    I_COMBINED_HOLDING_MIN,
    L_RS_MIN,
    N_HIGH_PROXIMITY_MAX,
    S_VOLUME_SURGE_MIN,
    compute_c_score,
    evaluate_a,
    evaluate_c,
    evaluate_c_detailed,
    evaluate_i,
    evaluate_l,
    evaluate_m,
    evaluate_n,
    evaluate_s,
    passes_c_gate,
)
from canslim_lib.score import compute_score  # noqa: E402

OUTPUT = ROOT / "public" / "data" / "can-slim-candidates.json"
WATCHLIST_FILE = ROOT / "public" / "data" / "watchlist.json"
MANAGEMENT_QUALITY_FILE = ROOT / "public" / "data" / "management-quality.json"


def load_watchlist_management() -> dict[str, str]:
    """{code: management_quality} 매핑 로드.

    우선순위:
      1. public/data/management-quality.json — DART 공시 자동 분류 (1단계 필터 통과 종목)
      2. public/data/watchlist.json — 사람 라벨링 (저평가 배당주 워치리스트)
    1순위가 우선 적용되고, 그 외 종목은 2순위로 보충.
    C 점수 축 ④ (경영진 7점) 산출에 사용. 둘 다 없으면 0점.
    """
    out: dict[str, str] = {}

    # 2순위 — 워치리스트 (사람 라벨링)
    if WATCHLIST_FILE.exists():
        try:
            wl = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
            for s in wl.get("stocks", []):
                code = s.get("code")
                mq = s.get("management_quality")
                if code and mq:
                    out[code] = mq
        except Exception:
            pass

    # 1순위 — 자동 분류 (덮어쓰기)
    if MANAGEMENT_QUALITY_FILE.exists():
        try:
            mq_data = json.loads(MANAGEMENT_QUALITY_FILE.read_text(encoding="utf-8"))
            for code, info in mq_data.get("stocks", {}).items():
                q = info.get("quality")
                if q:
                    out[code] = q
        except Exception:
            pass

    return out


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def fetch_market_state(verbose: bool = True) -> tuple[dict, list[float]]:
    """KOSPI 추세 판정 + closes 반환."""
    if verbose:
        print("📊 시장 추세(M) 판정: KOSPI ^KS11 1년 종가 조회...")
    ks = fetch_yahoo_chart("^KS11", "1y", "1d")
    if not ks or len(ks["closes"]) < 220:
        return {"verdict": "DATA_FAIL", "passed": False, "value": "데이터 부족", "detail": ""}, []

    passed, value, detail = evaluate_m(ks["closes"])
    state = {
        "verdict": "GO" if passed else "STOP",
        "passed": passed,
        "value": value,
        "detail": detail,
        "kospi_close": ks["closes"][-1],
    }
    if verbose:
        print(f"  → {value} | {state['verdict']}")
    return state, ks["closes"]


def _is_period_recent(period_key: str, months_back: int = 6) -> bool:
    """period_key 가 (now - months_back) 이후인지. 형식 YYYYMM."""
    if len(period_key) != 6 or not period_key[:4].isdigit() or not period_key[4:].isdigit():
        return False
    py = int(period_key[:4])
    pm = int(period_key[4:])
    now = datetime.now()
    delta_months = (now.year - py) * 12 + (now.month - pm)
    return 0 <= delta_months <= months_back


def _light_c_eligible(quarter_eps: list[tuple[str, float]]) -> bool:
    """Tier 2 게이트 — Naver-only 데이터로 C gate 통과 가능성 사전 판단.

    Returns False = "C gate 통과 불가 확정 → DART backfill·잠정실적·5%룰 스킵 안전".
    Returns True  = "통과 가능성 있음 → Tier 2 진행 필요".

    엄격 보수 — false negative (실제 C 통과 가능 종목을 스킵) 를 피하기 위해
    아래 모든 조건이 충족된 경우에만 False 반환:
      1) Naver 5분기 이상 보유
      2) Naver 최신 분기가 최근 4개월 이내 (그 이상이면 DART 가 새 분기 보유 가능성 ↑.
         한국 분기보고서 마감 45일 + Naver 업데이트 lag 2~4주 = 약 2~3개월 이내라면
         새 분기가 아직 없을 가능성. 4개월 이상이면 다음 분기 마감 지났을 가능성 高.)
      3) 최신 EPS > 0 (적자면 잠정실적 흑자전환 가능성 보존)
      4) yoy_eps != 0 (분모 0 모호 케이스 보존)
      5) latest_yoy < 25% (C gate 임계 미달)
    """
    if len(quarter_eps) < 5:
        return True

    latest_period, latest_eps = quarter_eps[-1]
    _, yoy_eps = quarter_eps[-5]

    if not _is_period_recent(latest_period, months_back=4):
        return True
    if latest_eps <= 0:
        return True
    if yoy_eps == 0:
        return True

    denom = max(abs(yoy_eps), 100.0)  # EPS_DENOMINATOR_FLOOR
    latest_yoy = (latest_eps - yoy_eps) / denom * 100
    return latest_yoy >= 25.0


def collect_raw_data(
    code: str,
    name: str,
    market: str,
    corp_map: dict[str, str],
    min_price: int = 0,
    min_market_cap_eok: int = 0,
    min_turnover_eok: float = 30.0,
    skip_tier2_if_c_ineligible: bool = True,
) -> dict | None:
    """1차 패스: 종목별 원시 데이터 수집. RS는 아직 계산하지 않음.

    오닐 $20 룰의 한국 적용 (v2): 절대가 컷오프 대신 시총 + 거래대금 두 축 사용.
      - 시총 ≥ 2,000억원 (default) — 기관이 들어올 수 있는 사이즈
      - 일평균 거래대금 ≥ 30억원 (30일, default) — 기관 진입/이탈 가능한 유동성
    min_price (구 컷오프) 는 backward-compat 용으로 남겨두지만 default 0 = 비활성.

    2-tier fetch (2026-05-21):
      - Tier 1: Naver integration + Yahoo 1y + Naver annual/quarter (모든 종목)
      - Tier 2: DART 분기 EPS·매출 backfill + 잠정실적 + 5%룰 (C gate 가능성 있는 종목만)
      Naver-only 5분기로 latest_yoy < 25% 확정된 종목은 Tier 2 전면 스킵.
      skip_tier2_if_c_ineligible=False 면 항상 Tier 2 진행 (기존 동작).
    """
    # ─── Tier 1: Naver + Yahoo (모든 종목) ─────────────────────
    ig = fetch_integration(code)
    if not ig:
        return None
    market_cap = ig["market_cap_eok"]
    if market_cap < min_market_cap_eok:
        return {"_skipped_small_cap": True, "market_cap_eok": market_cap}

    if min_price > 0:
        price_val = ig.get("price") or 0
        if price_val < min_price:
            return {"_skipped_low_price": True, "price": price_val}

    # Yahoo 1y 일봉 (거래대금 체크 + N/L/M 원칙 평가에 모두 사용)
    chart = fetch_yahoo_chart(yahoo_symbol(code, market), "1y", "1d")
    if not chart:
        chart = {"closes": [], "volumes": [], "timestamps": []}

    # 30일 일평균 거래대금 (억원). Yahoo 일시 실패로 chart 비면 컷오프 skip
    # (false negative 방지 — Yahoo 응답 부재를 거래대금 미달로 처리하지 않는다)
    closes = chart["closes"]
    volumes = chart["volumes"]
    chart_valid = bool(closes and volumes and len(closes) >= 5)
    if chart_valid:
        n_days = min(len(closes), 30)
        turnover_sum = sum(closes[i] * volumes[i] for i in range(-n_days, 0))
        avg_turnover_eok = turnover_sum / n_days / 1e8
    else:
        avg_turnover_eok = 0.0

    if chart_valid and min_turnover_eok > 0 and avg_turnover_eok < min_turnover_eok:
        return {
            "_skipped_low_turnover": True,
            "market_cap_eok": market_cap,
            "turnover_eok": avg_turnover_eok,
        }

    ann = fetch_annual(code)
    qtr = fetch_quarter(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    annual_roe = get_row_values(ann, "ROE") if ann else []
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    quarter_sales = get_row_values(qtr, "매출액") if qtr else []

    # ─── Tier 2 게이트 ────────────────────────────────────────
    do_tier2 = (not skip_tier2_if_c_ineligible) or _light_c_eligible(quarter_eps)
    tier2_skipped = not do_tier2

    # ─── Tier 2: DART backfill + 잠정실적 + 5%룰 (선별 종목만) ──
    # DART 분기 EPS 보강:
    #  - 과거 보강: Naver 최근 5분기에 빠진 옛 분기 (Naver latest_year-1 의 Q1/Q2/Q3)
    #  - 최신 확정: 현재년도 Q1 분기보고서가 공시된 경우 컨센서스 → 확정값으로 갱신
    #  - 잠정실적: 분기보고서 미공시이지만 잠정실적 발표된 분기 추가 (latest_is_preliminary 플래그)
    # 우선주(예: 005935 삼성전자우)는 corp_map 직접 매칭 없으므로 보통주(005930) corp_code 로 fallback.
    preliminary_period: str | None = None
    preliminary_rcept_no: str | None = None
    institutional = None
    corp_code: str | None = None
    common_code: str | None = None

    if do_tier2:
        corp_code, common_code = resolve_corp_code(code, corp_map)
        if corp_code and quarter_eps:
            current_year = datetime.now().year
            naver_latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else current_year
            dart_eps_combined: list[tuple[str, float]] = []
            dart_sales_combined: list[tuple[str, float]] = []
            # 과거 보강 (latest_year - 1)
            eps_old = fetch_dart_quarterly_eps_history(corp_code, naver_latest_year - 1)
            sales_old = fetch_dart_quarterly_sales_history(corp_code, naver_latest_year - 1)
            if eps_old:
                dart_eps_combined.extend(eps_old)
            if sales_old:
                dart_sales_combined.extend(sales_old)
            # 최신 확정 (current_year, naver보다 앞서면)
            if current_year >= naver_latest_year:
                eps_new = fetch_dart_quarterly_eps_history(corp_code, current_year)
                sales_new = fetch_dart_quarterly_sales_history(corp_code, current_year)
                if eps_new:
                    dart_eps_combined.extend(eps_new)
                if sales_new:
                    dart_sales_combined.extend(sales_new)
            if dart_eps_combined:
                quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_eps_combined)
            if dart_sales_combined:
                # 단위 정규화: Naver 매출은 억원 단위(예: 19542 = 1.95조), DART는 원 단위(예: 1.95조 = 1,954,200,000,000)
                # 머지 전 DART 값을 억원으로 환산 (÷10^8)
                dart_sales_eok = [(p, v / 1e8) for p, v in dart_sales_combined]
                quarter_sales = merge_naver_dart_quarters(quarter_sales, dart_sales_eok)

            # 잠정실적 보강: 분기보고서가 아직 안 나온 분기를 잠정실적으로 채움
            # 방식: 최신 분기(quarter_eps[-1])의 다음 분기 잠정실적 검색
            # EPS = 당기순이익(원) / 발행주식수 (= 시가총액 / 주가)
            if quarter_eps:
                last_period = quarter_eps[-1][0]  # YYYYMM
                if len(last_period) == 6 and last_period[:4].isdigit():
                    last_year = int(last_period[:4])
                    last_q = int(last_period[4:]) // 3
                    # 다음 분기 계산
                    next_q = last_q + 1
                    next_year = last_year
                    if next_q > 4:
                        next_q = 1
                        next_year += 1
                    # 잠정실적 fetch
                    pre = fetch_preliminary_quarter(corp_code, next_year, next_q)
                    if pre and pre["revenue_eok"] > 0 and pre["net_income_eok"] != 0:
                        # 발행주식수 계산:
                        #  - 1순위: annual_net_income / annual_EPS (Naver EPS 산정 기준과 동일,
                        #    자사주·우선주 가중평균 반영)
                        #  - 2순위(fallback): 시총 / 주가 (우선주 케이스에선 보통주)
                        shares = None
                        annual_ni_rows = get_row_values(ann, "당기순이익") if ann else []
                        if annual_ni_rows and annual_eps:
                            ni_latest = annual_ni_rows[-1][1]  # 억원 단위
                            eps_latest = annual_eps[-1][1]
                            if ni_latest > 0 and eps_latest > 0:
                                # shares = NI(원) / EPS(원) = NI(억) × 1e8 / EPS
                                shares = ni_latest * 1e8 / eps_latest
                        if shares is None:
                            if common_code:
                                parent_ig = fetch_integration(common_code) or {}
                                price = parent_ig.get("price") or 0
                                market_cap_eok = parent_ig.get("market_cap_eok") or 0
                            else:
                                price = ig.get("price") or 0
                                market_cap_eok = ig.get("market_cap_eok") or 0
                            if price > 0 and market_cap_eok > 0:
                                shares = market_cap_eok * 1e8 / price
                        if shares and shares > 0:
                            preliminary_eps = pre["net_income_eok"] * 1e8 / shares
                            quarter_eps = quarter_eps + [(pre["period_key"], preliminary_eps)]
                            quarter_sales = quarter_sales + [(pre["period_key"], pre["revenue_eok"])]
                            preliminary_period = pre["period_key"]
                            preliminary_rcept_no = pre["rcept_no"]

        # 기관 보유율 (DART) — 우선주 케이스에서도 보통주 corp_code 사용
        institutional = fetch_majorstock_holding(corp_code) if corp_code else None

    # 12개월 수익률 (RS 백분위 계산용, 가격 데이터 부족 시 0)
    twelve_m_return = (closes[-1] - closes[0]) / closes[0] * 100 if closes and closes[0] > 0 else 0.0

    return {
        "code": code,
        "name": name,
        "market": market,
        "ig": ig,
        "annual_eps": annual_eps,
        "annual_roe": annual_roe,
        "quarter_eps": quarter_eps,
        "quarter_sales": quarter_sales,
        "preliminary_period": preliminary_period,
        "preliminary_rcept_no": preliminary_rcept_no,
        "chart": chart,
        "institutional": institutional,
        "twelve_m_return": twelve_m_return,
        "avg_turnover_eok_30d": round(avg_turnover_eok, 2),
        "tier2_skipped": tier2_skipped,
    }


# ─────────────────────────────────────────────────────────────────────────
# collect_raw_data_v2 — 하이브리드 (Naver + DART)
#   - 시세/시총/거래량: pdata (공공데이터포털)
#   - OHLCV + 외인: api.stock.naver.com (별개 host, rate limit 분리)
#   - 연간 EPS/ROE/매출: Naver fetch_annual (1 호출, 다년치 한번에)
#   - 분기 EPS/매출: Naver fetch_quarter (1 호출, 5분기) + DART backfill (캐시 hit이면 free)
#   - 잠정실적/5%룰: DART (대안 없음)
#   기존 collect_raw_data 와 동일한 반환 shape 유지 → evaluate_with_rs 변경 불필요
#
# DART 호출 양: 종목당 잠정 1 + 5%룰 1 + 분기 backfill (캐시 활용) = 일일 운영 시 ~3 호출
# ─────────────────────────────────────────────────────────────────────────

def collect_raw_data_v2(
    code: str,
    name: str,
    market: str,
    price_info: dict,
    item_info: dict | None,
    corp_map: dict[str, str],
    min_price: int = 0,
    min_market_cap_eok: int = 0,
    min_turnover_eok: float = 30.0,
    skip_tier2_if_c_ineligible: bool = True,
) -> dict | None:
    """v2.1: 하이브리드 (Naver fetch_annual/quarter + DART backfill/잠정/5%룰).

    Args:
      price_info: pdata.fetch_pdata_price_info(basDt)[code] — 시세/시총/거래량/상장주식수
      item_info: pdata.fetch_pdata_item_info(basDt)[code] — crno/법인명 (None 가능)
      corp_map: DART corp_code 매핑 (resolve_corp_code 용 — 우선주 fallback)
    """
    # ─── 1) 시총 / 가격 컷오프 (pdata 사용) ─────────────────
    if not price_info:
        return None
    market_cap = price_info.get("market_cap_eok") or 0
    if market_cap < min_market_cap_eok:
        return {"_skipped_small_cap": True, "market_cap_eok": market_cap}

    current_price = price_info.get("clpr") or 0
    if min_price > 0 and current_price > 0 and current_price < min_price:
        return {"_skipped_low_price": True, "price": current_price}

    # ─── 2) api.stock.naver.com day chart (OHLCV + 외인 시계열) ──
    chart_raw = fetch_naver_day_chart(code, days_back=400)
    if not chart_raw:
        chart = {"closes": [], "volumes": [], "timestamps": [], "foreign_rates": []}
    else:
        chart = chart_raw

    closes = chart["closes"]
    volumes = chart["volumes"]
    chart_valid = bool(closes and volumes and len(closes) >= 5)

    # ─── 3) 30일 평균 거래대금 컷오프 ─────────────────────
    if chart_valid:
        n_days = min(len(closes), 30)
        turnover_sum = sum(closes[i] * volumes[i] for i in range(-n_days, 0))
        avg_turnover_eok = turnover_sum / n_days / 1e8
    else:
        avg_turnover_eok = price_info.get("trPrc_eok") or 0.0

    if chart_valid and min_turnover_eok > 0 and avg_turnover_eok < min_turnover_eok:
        return {
            "_skipped_low_turnover": True,
            "market_cap_eok": market_cap,
            "turnover_eok": avg_turnover_eok,
        }

    # ─── 4) 외국인지분율 (마지막 유효값) ──────────────────
    foreign_ownership = 0.0
    if chart.get("foreign_rates"):
        for r in reversed(chart["foreign_rates"]):
            if r is not None:
                foreign_ownership = r
                break

    # ─── 5) corp_code resolve ────────────────────────────
    corp_code, common_code = resolve_corp_code(code, corp_map)

    # ─── 6) Naver fetch_annual — 연간 EPS/ROE/매출/순이익 (1회 호출, 다년치) ──
    current_year = datetime.now().year
    ann = fetch_annual(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    annual_roe = get_row_values(ann, "ROE") if ann else []
    annual_ni_rows = get_row_values(ann, "당기순이익") if ann else []
    # 잠정실적 발행주식수 계산용 (key: period, value: 억원)
    annual_ni_eok: dict[str, float] = {p: v for p, v in annual_ni_rows}

    # ─── 7) Naver fetch_quarter (5분기) — 분기 EPS/매출 ──
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    quarter_sales = get_row_values(qtr, "매출액") if qtr else []

    # ─── 7-1) DART 분기 backfill (캐시 hit 시 무료, miss 시 호출) ──
    # Naver 5분기 부족분 보강 + Q1 마감 후 최신 분기 확정값 추가
    # cached 무료라 자유롭게 호출, miss 시에만 DART hit
    if corp_code and quarter_eps:
        naver_latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else current_year
        dart_eps_combined: list[tuple[str, float]] = []
        dart_sales_combined: list[tuple[str, float]] = []
        # 과거 보강 (Naver latest_year - 1) + 최신 확정 (current_year)
        years_to_fetch = {naver_latest_year - 1}
        if current_year >= naver_latest_year:
            years_to_fetch.add(current_year)
        for yr in years_to_fetch:
            eps_y = fetch_dart_quarterly_eps_history(corp_code, yr)
            sales_y = fetch_dart_quarterly_sales_history(corp_code, yr)
            if eps_y:
                dart_eps_combined.extend(eps_y)
            if sales_y:
                dart_sales_combined.extend(sales_y)
        if dart_eps_combined:
            quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_eps_combined)
        if dart_sales_combined:
            # DART 매출 단위 정규화: 원 → 억원
            dart_sales_eok = [(p, v / 1e8) for p, v in dart_sales_combined]
            quarter_sales = merge_naver_dart_quarters(quarter_sales, dart_sales_eok)

    # ─── 8) Tier 2 게이트 (잠정실적 + 5%룰 호출 여부 결정) ──
    do_tier2 = (not skip_tier2_if_c_ineligible) or _light_c_eligible(quarter_eps)
    tier2_skipped = not do_tier2

    # ─── 9) (Tier 2) 잠정실적 보강 ────────────────────────
    preliminary_period: str | None = None
    preliminary_rcept_no: str | None = None
    if do_tier2 and corp_code and quarter_eps:
        last_period = quarter_eps[-1][0]
        if len(last_period) == 6 and last_period[:4].isdigit():
            last_year = int(last_period[:4])
            last_q = int(last_period[4:]) // 3
            next_q = last_q + 1
            next_year = last_year
            if next_q > 4:
                next_q = 1
                next_year += 1
            pre = fetch_preliminary_quarter(corp_code, next_year, next_q)
            if pre and pre.get("revenue_eok", 0) > 0 and pre.get("net_income_eok", 0) != 0:
                # 발행주식수 계산:
                #  1순위: DART annual NI / EPS (자사주·우선주 가중평균 반영)
                #  2순위: pdata lstgStCnt
                shares = None
                if annual_eps:
                    latest_yk = annual_eps[-1][0]
                    eps_latest = annual_eps[-1][1]
                    ni_latest = annual_ni_eok.get(latest_yk)
                    if ni_latest and eps_latest and ni_latest > 0 and eps_latest > 0:
                        shares = ni_latest * 1e8 / eps_latest
                if shares is None:
                    shares = price_info.get("lstgStCnt")
                if shares and shares > 0:
                    preliminary_eps = pre["net_income_eok"] * 1e8 / shares
                    quarter_eps.append((pre["period_key"], preliminary_eps))
                    quarter_sales.append((pre["period_key"], pre["revenue_eok"]))
                    quarter_eps.sort()
                    quarter_sales.sort()
                    preliminary_period = pre["period_key"]
                    preliminary_rcept_no = pre["rcept_no"]

    # ─── 10) (Tier 2) 5%룰 institutional ───────────────────
    institutional = fetch_majorstock_holding(corp_code) if (do_tier2 and corp_code) else None

    # ─── 11) PER 계산 (UI 표시용) ──────────────────────────
    # Naver fetch_integration 안 쓰므로 PBR/배당수익률은 미산정 (점수 산정엔 무관)
    per: float | None = None
    if current_price and annual_eps:
        eps_latest = annual_eps[-1][1]
        if eps_latest > 0:
            per = round(current_price / eps_latest, 2)

    # ─── 12) ig dict (legacy 호환) ────────────────────────
    ig = {
        "market_cap_eok": market_cap,
        "per": per,
        "pbr": None,  # Naver integration 미사용 → 미산정 (점수 무관)
        "dividend_yield": 0.0,
        "foreign_ownership": foreign_ownership,
        "price": current_price or 0,
    }

    # ─── 13) 12M 수익률 ───────────────────────────────────
    twelve_m_return = (closes[-1] - closes[0]) / closes[0] * 100 if closes and closes[0] > 0 else 0.0

    return {
        "code": code,
        "name": name,
        "market": market,
        "ig": ig,
        "annual_eps": annual_eps,
        "annual_roe": annual_roe,
        "quarter_eps": quarter_eps,
        "quarter_sales": quarter_sales,
        "preliminary_period": preliminary_period,
        "preliminary_rcept_no": preliminary_rcept_no,
        "chart": chart,
        "institutional": institutional,
        "twelve_m_return": twelve_m_return,
        "avg_turnover_eok_30d": round(avg_turnover_eok, 2),
        "tier2_skipped": tier2_skipped,
    }


def evaluate_with_rs(
    raw: dict,
    kospi_closes: list[float],
    market_passed: bool,
    universe_returns: list[float] | None = None,
    management_map: dict[str, str] | None = None,
) -> dict:
    """2차 패스: 7기준 평가 + 점수화. universe_returns가 있으면 RS 백분위 사용."""
    ig = raw["ig"]
    chart = raw["chart"]
    inst = raw["institutional"]
    inst_pct = inst["institutional_pct"] if inst else None
    inst_trend = inst["recent_trend"] if inst else None

    results = {
        "C": evaluate_c(raw["quarter_eps"]),
        "A": evaluate_a(raw["annual_eps"], raw["annual_roe"]),
        "N": evaluate_n(chart["closes"]),
        "S": evaluate_s(chart["volumes"], ig["market_cap_eok"]),
        "L": evaluate_l(chart["closes"], kospi_closes, universe_returns),
        "I": evaluate_i(ig["foreign_ownership"], inst_pct, inst_trend),
        "M": (
            market_passed,
            "시장 추세 통과" if market_passed else "시장 추세 미통과",
            "(전체 시장 판정 결과 적용)",
        ),
    }

    score, passed_count, grade = compute_score(results)

    c_detailed = evaluate_c_detailed(
        raw["quarter_eps"],
        raw.get("quarter_sales"),
        dilution_flag=None,
    )
    # 잠정실적이 최신 분기로 들어와 있다면 latest_is_preliminary 플래그
    pre_period = raw.get("preliminary_period")
    if pre_period and c_detailed.get("latest_quarter") == pre_period:
        c_detailed["latest_is_preliminary"] = True
        c_detailed["preliminary_rcept_no"] = raw.get("preliminary_rcept_no")
    else:
        c_detailed["latest_is_preliminary"] = False
        c_detailed["preliminary_rcept_no"] = None

    criteria_out = {
        k: {"pass": r[0], "value": r[1], "detail": r[2]}
        for k, r in results.items()
    }
    criteria_out["C"].update(c_detailed)
    # C.pass 는 프론트 `passesCGate` (src/app/stocks/canslim/lib/cFilter.ts) 와
    # 반드시 동일한 5조건 게이트 결과로 통일. evaluate_c() 의 단순 pass 와 다름.
    # [doc-logic-sync] 동기화 깨지면 페이지 노출 종목과 백엔드 pass 가 어긋남.
    criteria_out["C"]["pass"] = passes_c_gate(c_detailed)

    # C 4축 점수 부착 (1단계 필터 통과 종목 간 우선순위 산출용).
    # 경영진 품질은 워치리스트 매핑이 있는 종목에만 점수 부여, 미등록은 0점.
    mgmt_quality = (management_map or {}).get(raw["code"])
    c_score_result = compute_c_score(c_detailed, mgmt_quality)

    # 52주 신고점 대비 현재가 비율 (%). 음수면 신고점 아래 (-15.0 = 15% 아래).
    pct_from_52w_high: float | None = None
    closes = chart.get("closes") or []
    if closes:
        window = closes[-252:] if len(closes) >= 252 else closes
        high_52w = max(window)
        latest_close = closes[-1]
        if high_52w > 0:
            pct_from_52w_high = round((latest_close / high_52w - 1) * 100, 2)

    return {
        "code": raw["code"],
        "name": raw["name"],
        "market": raw["market"],
        "score": score,
        "grade": grade,
        "passed_count": passed_count,
        "market_cap_eok": int(ig["market_cap_eok"]),
        "avg_turnover_eok_30d": raw.get("avg_turnover_eok_30d", 0.0),
        "per": ig["per"],
        "pbr": ig["pbr"],
        "dividend_yield": ig["dividend_yield"],
        "foreign_ownership": ig["foreign_ownership"],
        "institutional_pct": inst_pct,
        "institutional_trend": inst_trend,
        "twelve_m_return": round(raw["twelve_m_return"], 2),
        "current_price": int(ig["price"]) if ig["price"] else (int(chart["closes"][-1]) if chart.get("closes") else 0),
        "pct_from_52w_high": pct_from_52w_high,
        "criteria": criteria_out,
        "c_score": c_score_result["total"],
        "c_score_tier": c_score_result["tier"],
        "c_score_breakdown": c_score_result["breakdown"],
        "c_score_notes": c_score_result["notes"],
        "management_quality": mgmt_quality,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CAN SLIM 한국 시장 스크리너 (한국 보정판)")
    parser.add_argument("--limit", type=int, default=0, help="시총 상위 N개만 평가")
    parser.add_argument("--offset", type=int, default=0, help="시총 상위 offset+1 위부터 평가 시작 (default 0)")
    parser.add_argument("--market", choices=["all", "kospi", "kosdaq"], default="all", help="대상 시장")
    parser.add_argument("--market-only", action="store_true", help="시장 추세(M)만 판정")
    parser.add_argument("--ticker", help="단일 종목 코드만 평가")
    parser.add_argument("--save", action="store_true", help="결과 JSON 저장")
    parser.add_argument("--merge", action="store_true", help="기존 JSON candidates에 머지 (offset > 0 일 때 유용)")
    parser.add_argument("--min-price", type=int, default=0,
                        help="(레거시) 현재가가 이 KRW 미만이면 스킵. 오닐 $20 룰의 한국 적용은 --min-cap + --min-turnover 사용 권장")
    parser.add_argument("--min-cap", type=int, default=0,
                        help="시가총액 최소 (억원, default 0 = 컷오프 없음). "
                             "검증 결과 2,000억 default 컷오프가 C-통과 종목 83개(시총 < 2,000억)를 사전 제외해 "
                             "A등급 1개, B등급 13개, C 점수 90+ 강력 tier 7개가 누락됐음. 컷오프 제거가 합리적.")
    parser.add_argument("--min-turnover", type=float, default=30.0,
                        help="일평균 거래대금 최소 (억원, 30일, default 30) — 오닐 $20 룰의 한국 적용 (기관 유동성)")
    parser.add_argument("--worker", type=int, default=None,
                        help="병렬 작업자 인덱스 (0-base). --workers-total 과 함께 사용. universe[worker::workers_total] 슬라이스를 Pass 1 만 처리하고 .cache/canslim_worker_NN.json 에 저장.")
    parser.add_argument("--workers-total", type=int, default=None,
                        help="총 작업자 수. 모든 워커가 같은 값을 써야 universe 가 빠짐없이 분배됨.")
    parser.add_argument("--reduce", action="store_true",
                        help="모든 .cache/canslim_worker_*.json 캐시를 병합 후 Pass 2 + 최종 JSON 저장. 항상 --save 처럼 동작.")
    parser.add_argument("--no-cache", action="store_true",
                        help="종목별 캐시 비활성화 (모든 종목을 새로 fetch)")
    parser.add_argument("--cache-ttl-hours", type=float, default=24.0,
                        help="종목 캐시 유효 시간(시간). 0 = 영구")
    parser.add_argument("--clear-cache", action="store_true",
                        help="시작 전에 모든 종목 캐시 삭제")
    parser.add_argument("--no-tier2-skip", action="store_true",
                        help="C 부적격 종목에도 DART backfill·잠정실적·5%%룰 호출 (기존 동작). "
                             "default: Naver-only 데이터로 C gate 통과 불가 확정 종목은 DART 전면 스킵.")
    parser.add_argument("--legacy-v1", action="store_true",
                        help="m.stock.naver.com 기반 v1 collect_raw_data 사용 (legacy/rollback). "
                             "default: v2 — pdata + api.stock.naver.com + DART 일원화 (m.stock.naver.com 호출 0).")
    args = parser.parse_args()

    if args.clear_cache:
        n = stock_cache.clear()
        print(f"🗑  종목 캐시 {n}개 삭제됨")

    # 워치리스트 경영진 품질 매핑 (C 점수 축 ④ 산출용)
    management_map = load_watchlist_management()
    if management_map:
        print(f"👥 워치리스트 경영진 매핑: {len(management_map)}종목")

    is_worker = args.worker is not None and args.workers_total is not None
    is_reduce = args.reduce

    # DART rate limit (분당 1000 IP 합산) — 워커 모드면 워커별 cap 분할
    # CANSLIM_DART_RATE_LIMIT 환경변수 미설정 시에만 자동 분할
    if is_worker and "CANSLIM_DART_RATE_LIMIT" not in os.environ:
        per_worker = max(50, 800 // args.workers_total)
        os.environ["CANSLIM_DART_RATE_LIMIT"] = str(per_worker)
        print(f"⚙️  DART rate limit: 워커당 {per_worker}/분 (총 {per_worker * args.workers_total}/분, 서버 한도 1000/분)")

    print("🎯 CAN SLIM 스크리너 (한국 보정판 v1)\n")
    print(f"  임계값: C +{C_QUARTERLY_EPS_MIN}%, A +{A_ANNUAL_EPS_MIN}%/ROE {A_ROE_MIN}%+, "
          f"N -{N_HIGH_PROXIMITY_MAX}%, S +{S_VOLUME_SURGE_MIN}%, L RS{L_RS_MIN}+, I {I_COMBINED_HOLDING_MIN}%+\n")

    market_state, kospi_closes = fetch_market_state()

    if args.market_only:
        print(f"\n  최종: {market_state['verdict']}")
        print(f"  세부: {market_state['detail']}")
        return

    cache_dir = ROOT / ".cache"

    # ─────────────────────────────────────────────
    # REDUCE 모드: 워커 캐시 병합 → Pass 2 → 최종 JSON
    # ─────────────────────────────────────────────
    if is_reduce:
        worker_files = sorted(cache_dir.glob("canslim_worker_*.json"))
        if not worker_files:
            print("❌ .cache/canslim_worker_*.json 캐시 없음. 먼저 --worker 모드로 수집하세요.")
            return
        print(f"\n🔀 Reduce: {len(worker_files)}개 워커 캐시 병합")
        raw_data: list[dict] = []
        failed_stocks: list[dict] = []
        skipped_small_cap = 0
        skipped_low_price = 0
        skipped_low_turnover = 0
        tier2_skipped_count = 0
        for f in worker_files:
            try:
                chunk = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  ⚠️ {f.name} 로드 실패: {e}")
                continue
            raw_data.extend(chunk.get("raw_data", []))
            failed_stocks.extend(chunk.get("failed_stocks", []))
            skipped_small_cap += chunk.get("skipped_small_cap", 0)
            skipped_low_price += chunk.get("skipped_low_price", 0)
            skipped_low_turnover += chunk.get("skipped_low_turnover", 0)
            tier2_skipped_count += chunk.get("tier2_skipped_count", 0)
            print(f"  {f.name}: raw {len(chunk.get('raw_data', []))} / fail {len(chunk.get('failed_stocks', []))}")
        print(f"\n  병합 결과: raw {len(raw_data)} / 실패 {len(failed_stocks)}")
        print(f"    🪙 시총 미만 제외: {skipped_small_cap}")
        print(f"    💧 거래대금 미만 제외: {skipped_low_turnover}")
        if tier2_skipped_count:
            print(f"    ⏩ Tier 2 스킵 (C 부적격 확정): {tier2_skipped_count}")
        args.save = True
        # universe 의 scanned_count 는 raw + 실패 + 제외 합으로 근사
        universe_size_estimate = len(raw_data) + len(failed_stocks) + skipped_small_cap + skipped_low_price + skipped_low_turnover
        fail = len(failed_stocks)
        # Pass 1 건너뛰고 Pass 2 로 점프 (아래 ‘Pass 2’ 블록과 합쳐 흐름)
        _reduce_path = True
    else:
        _reduce_path = False
        universe_size_estimate = 0
        fail = 0
        raw_data = []
        failed_stocks = []
        skipped_small_cap = 0
        skipped_low_price = 0
        skipped_low_turnover = 0
        tier2_skipped_count = 0

    # corp_code 매핑 (워커·단일 종목·풀 스캔에서만 필요. reduce 는 건너뜀.)
    if not _reduce_path:
        print("📦 DART corp_code 매핑 로드...")
        corp_map = load_corp_code_map()
        print(f"  {len(corp_map)}개 상장사 매핑")
    else:
        corp_map = {}

    # 단일 종목 모드
    if args.ticker:
        code = args.ticker
        market = "KOSPI"
        ch_ks = fetch_yahoo_chart(f"{code}.KS", "1mo", "1d")
        ch_kq = fetch_yahoo_chart(f"{code}.KQ", "1mo", "1d")
        if ch_kq and not ch_ks:
            market = "KOSDAQ"

        # 단일 종목 모드: 사용자가 명시한 종목이므로 항상 Tier 2 전체 fetch
        if args.legacy_v1:
            raw = collect_raw_data(code, code, market, corp_map, skip_tier2_if_c_ineligible=False)
        else:
            basDt = pdata._latest_available_basDt()
            pi = pdata.fetch_pdata_price_info(basDt).get(code, {}) if basDt else {}
            mi = pdata.fetch_pdata_item_info(basDt).get(code) if basDt else None
            raw = collect_raw_data_v2(code, code, market, pi, mi, corp_map, skip_tier2_if_c_ineligible=False)
        if not raw:
            print(f"  {code}: 데이터 수집 실패")
            return
        result = evaluate_with_rs(raw, kospi_closes, market_state["passed"], None, management_map)
        _print_one(result)
        return

    # 전체 스캔 또는 워커 슬라이스: 2-pass (reduce 모드는 이 블록 건너뜀)
    if not _reduce_path:
        # ── v2 모드: pdata batch preload (1회 호출로 전체 종목 시세/시총/메타) ──
        pdata_price: dict = {}
        pdata_meta: dict = {}
        if not args.legacy_v1:
            print("\n🏛  공공데이터포털 batch preload (getStockPriceInfo + getItemInfo)")
            basDt = pdata._latest_available_basDt()
            if basDt:
                print(f"  최근 영업일: {basDt}")
                pdata_price = pdata.fetch_pdata_price_info(basDt)
                pdata_meta = pdata.fetch_pdata_item_info(basDt)
                print(f"  price_info: {len(pdata_price)}종목, item_info: {len(pdata_meta)}종목")
            else:
                print("  ⚠️ pdata 응답 실패 — legacy v1 모드로 fallback")
                args.legacy_v1 = True

        print("\n📋 종목 리스트 수집 (pykrx + 시총 동봉)...")
        universe = fetch_universe_with_cap(args.market)
        kospi_n = sum(1 for u in universe if u["market"] == "KOSPI")
        kosdaq_n = sum(1 for u in universe if u["market"] == "KOSDAQ")
        print(f"  전체: {len(universe)} (KOSPI {kospi_n} / KOSDAQ {kosdaq_n})")

        # universe 에 시총이 포함돼 있으므로 Pass 1 진입 전 미리 컷오프 — 루프 자체가 짧아짐.
        # (collect_raw_data 의 _skipped_small_cap 분기는 안전망으로 남겨두지만
        #  여기서 빠진 종목은 Naver/Yahoo 호출조차 안 함.)
        if args.min_cap > 0:
            before = len(universe)
            universe = [u for u in universe if u["market_cap_eok"] >= args.min_cap]
            pre_skipped = before - len(universe)
            skipped_small_cap += pre_skipped
            print(f"  시총 ≥ {args.min_cap:,}억: {len(universe)} (사전 제외 {pre_skipped})")

        full_universe_size = len(universe)
        if is_worker:
            # 워커 모드: limit + offset 먼저 적용 후 interleaved 슬라이스 (universe[w::N]) — 균등 분배.
            if args.offset:
                universe = universe[args.offset:]
            if args.limit:
                universe = universe[: args.limit]
            limited_size = len(universe)
            universe = universe[args.worker::args.workers_total]
            scope = f"{limited_size}/{full_universe_size}" if (args.limit or args.offset) else f"{full_universe_size}"
            print(f"  → Worker {args.worker}/{args.workers_total}: {len(universe)}/{scope} 종목 슬라이스 "
                  f"(offset {args.offset}, limit {args.limit or '없음'})")
        else:
            if args.offset:
                universe = universe[args.offset:]
                print(f"  → 시총 {args.offset + 1}위부터 (offset {args.offset})")
            if args.limit:
                universe = universe[: args.limit]
            print(f"  → 평가 대상 {len(universe)}종목 (시장: {args.market}, offset {args.offset}, limit {args.limit or '없음'})")

        universe_size_estimate = len(universe)

        # ── Pass 1: 원시 데이터 수집 (12M 수익률 포함) ──
        print(f"\n🔬 Pass 1: 원시 데이터 수집 ({len(universe)}종목, cache {'OFF' if args.no_cache else f'TTL {args.cache_ttl_hours}h'})\n")
        start = time.time()
        cache_hit_count = 0

        def _collect(s: dict) -> dict | None:
            """v2 또는 legacy v1 호출 분기."""
            if args.legacy_v1:
                return collect_raw_data(
                    s["code"], s["name"], s["market"], corp_map,
                    min_price=args.min_price,
                    min_market_cap_eok=args.min_cap,
                    min_turnover_eok=args.min_turnover,
                    skip_tier2_if_c_ineligible=not args.no_tier2_skip,
                )
            return collect_raw_data_v2(
                s["code"], s["name"], s["market"],
                pdata_price.get(s["code"]) or {},
                pdata_meta.get(s["code"]),
                corp_map,
                min_price=args.min_price,
                min_market_cap_eok=args.min_cap,
                min_turnover_eok=args.min_turnover,
                skip_tier2_if_c_ineligible=not args.no_tier2_skip,
            )

        for i, s in enumerate(universe):
            err_msg = ""
            try:
                if not args.no_cache:
                    cached = stock_cache.get(s["code"], max_age_hours=args.cache_ttl_hours)
                    if cached is not None and args.no_tier2_skip and cached.get("tier2_skipped"):
                        # 사용자가 --no-tier2-skip 으로 전체 Tier 2 요청 — 부분 캐시 무효화
                        cached = None
                    if cached is not None:
                        raw = cached
                        cache_hit_count += 1
                    else:
                        raw = _collect(s)
                        # _skipped_* 키가 있으면 캐시 안 함 — 다른 실행의 cap/turnover 임계값에서 재평가 필요
                        if raw is not None and not any(k.startswith("_skipped") for k in raw):
                            stock_cache.put(s["code"], raw)
                else:
                    raw = _collect(s)
            except Exception as e:
                raw = None
                err_msg = repr(e)
            if raw and raw.get("_skipped_small_cap"):
                skipped_small_cap += 1
            elif raw and raw.get("_skipped_low_price"):
                skipped_low_price += 1
            elif raw and raw.get("_skipped_low_turnover"):
                skipped_low_turnover += 1
            elif raw:
                if raw.get("tier2_skipped"):
                    tier2_skipped_count += 1
                raw_data.append(raw)
            else:
                fail += 1
                failed_stocks.append({"code": s["code"], "name": s["name"], "market": s["market"], "error": err_msg or "fetch_integration None (Naver 응답 없음)"})
            if (i + 1) % 25 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(universe) - i - 1) / rate if rate > 0 else 0
                print(f"  ... {i + 1}/{len(universe)} 수집 ({rate:.1f}/s, ETA {eta / 60:.1f}분, cache hit {cache_hit_count})")

        print(f"\n  Pass 1 완료: 평가 진입 {len(raw_data)}개 (cache hit {cache_hit_count})")
        print(f"    🪙 시총 {args.min_cap:,}억 미만 제외: {skipped_small_cap}종목")
        print(f"    💧 일평균 거래대금 {args.min_turnover}억 미만 제외: {skipped_low_turnover}종목")
        if not args.no_tier2_skip:
            print(f"    ⏩ Tier 2 스킵 (C 부적격 확정): {tier2_skipped_count}종목 (DART backfill 호출 생략)")
        if args.min_price:
            print(f"    💰 (레거시) 최소가 {args.min_price:,}원 미만 제외: {skipped_low_price}종목")
        print(f"    ❌ 진짜 실패(Naver 데이터 X): {fail}종목")
        if failed_stocks:
            print("  실패 종목:")
            for fs in failed_stocks:
                print(f"    - {fs['code']} {fs['name']} ({fs['market']}): {fs['error']}")

        # 워커 모드: 캐시에 저장하고 종료 (Pass 2·--save 건너뜀)
        if is_worker:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"canslim_worker_{args.worker:02d}.json"
            cache_file.write_text(
                json.dumps({
                    "worker": args.worker,
                    "workers_total": args.workers_total,
                    "raw_data": raw_data,
                    "failed_stocks": failed_stocks,
                    "skipped_small_cap": skipped_small_cap,
                    "skipped_low_price": skipped_low_price,
                    "skipped_low_turnover": skipped_low_turnover,
                    "tier2_skipped_count": tier2_skipped_count,
                }, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"\n💾 워커 캐시 저장: {cache_file.relative_to(ROOT)}")
            print("  (모든 워커 종료 후 `python scripts/screen_canslim.py --reduce` 로 병합)")
            return

    # ── Pass 2: universe 백분위 RS + 점수화 ──
    universe_returns = [r["twelve_m_return"] for r in raw_data]
    print(f"\n📈 Pass 2: RS 백분위 계산 + 점수화 (universe {len(universe_returns)}개)\n")

    results = []
    for raw in raw_data:
        try:
            r = evaluate_with_rs(raw, kospi_closes, market_state["passed"], universe_returns, management_map)
        except Exception:
            continue
        results.append(r)
        if r["passed_count"] >= 5:
            crit = "".join("✓" if r["criteria"][k]["pass"] else "·" for k in CRITERIA_KEYS)
            print(f"  ⭐ [{r['grade']}] {r['name']:<14} {r['score']:>3}점 ({r['passed_count']}/7) [{crit}] {r['market']}")

    # 정렬
    results.sort(key=lambda r: (-r["passed_count"], -r["score"], -r["market_cap_eok"]))

    print(f"\n✅ 스캔 완료: 평가 {len(results)}, 실패 {fail}")
    print("\n🏆 Top 20:")
    for i, r in enumerate(results[:20]):
        crit = "".join("✓" if r["criteria"][k]["pass"] else "·" for k in CRITERIA_KEYS)
        print(f"  {i+1:>2}. [{r['grade']}] {r['name']:<14} {r['score']:>3}점 [{crit}] {r['market']} 시총{r['market_cap_eok']:,}억")

    if args.save:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        candidates_final = results
        if args.merge and OUTPUT.exists():
            try:
                existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
                existing_by_code = {c["code"]: c for c in existing.get("candidates", [])}
                new_by_code = {c["code"]: c for c in results}
                # 새 결과 우선, 기존에 있는 다른 code 는 유지
                existing_by_code.update(new_by_code)
                candidates_final = sorted(existing_by_code.values(), key=lambda c: (-c["passed_count"], -c["score"], -c["market_cap_eok"]))
                print(f"\n🔀 머지: 기존 {len(existing_by_code) - len(new_by_code)}개 + 신규 {len(results)}개 = {len(candidates_final)}개")
            except (json.JSONDecodeError, OSError) as e:
                print(f"\n⚠️  기존 JSON 머지 실패, 덮어씀: {e}")
        out = {
            "generated_at": today_iso(),
            "scanned_count": universe_size_estimate,
            "evaluated_count": len(candidates_final),
            "scan_meta": {
                "offset": args.offset,
                "limit": args.limit,
                "market": args.market,
                "merged": args.merge,
                "min_price": args.min_price,
                "min_cap_eok": args.min_cap,
                "min_turnover_eok": args.min_turnover,
                "skipped_low_price_count": skipped_low_price,
                "skipped_small_cap_count": skipped_small_cap,
                "skipped_low_turnover_count": skipped_low_turnover,
                "tier2_skipped_count": tier2_skipped_count,
                "tier2_skip_enabled": not args.no_tier2_skip,
            },
            "market_status": {
                "kospi_trend_verdict": market_state["verdict"],
                "passed": market_state["passed"],
                "value": market_state["value"],
                "detail": market_state["detail"],
                "kospi_close": market_state.get("kospi_close"),
            },
            "candidates": candidates_final,
            "failed_stocks": failed_stocks,
            "criteria_thresholds": {
                "version": "korea-adjusted-v1",
                "C_quarterly_eps_yoy_min": C_QUARTERLY_EPS_MIN,
                "A_annual_eps_min": A_ANNUAL_EPS_MIN,
                "A_roe_min": A_ROE_MIN,
                "N_high_proximity_max": N_HIGH_PROXIMITY_MAX,
                "S_volume_surge_min": S_VOLUME_SURGE_MIN,
                "L_rs_min": L_RS_MIN,
                "I_combined_holding_min": I_COMBINED_HOLDING_MIN,
                "korea_notes": (
                    "ROE 17→15, 거래량 surge 50→30 (한국 시장 통계 반영). "
                    "C/A 성장률·N·L·M은 원전 유지. "
                    "L은 universe 백분위 RS 정확 계산. "
                    "I는 외인소진율 + DART 5%룰 기관 합산 + 1년 추세."
                ),
            },
        }
        OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장 완료: {OUTPUT.relative_to(ROOT)}")


def _print_one(r: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {r['name']} ({r['code']}) — {r['market']}")
    print(f"  점수 {r['score']}점, 등급 {r['grade']}, 통과 {r['passed_count']}/7")
    print(f"  현재가 {r['current_price']:,}원, PER {r['per']}, PBR {r['pbr']}, 시총 {r['market_cap_eok']:,}억")
    print(f"  외인 {r['foreign_ownership']:.1f}%, 기관(5%룰) {r['institutional_pct']}, 추세 {r['institutional_trend']}, 12M {r['twelve_m_return']:+.1f}%")
    print(f"{'=' * 60}")
    for k in CRITERIA_KEYS:
        c = r["criteria"][k]
        mark = "✅" if c["pass"] else "❌"
        print(f"  {mark} {k}: {c['value']}")
        print(f"      {c['detail']}")


if __name__ == "__main__":
    main()
