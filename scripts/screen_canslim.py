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
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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
    fetch_dart_quarterly_eps_history,
    fetch_integration,
    fetch_majorstock_holding,
    fetch_quarter,
    fetch_stock_list,
    fetch_yahoo_chart,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    yahoo_symbol,
)
from canslim_lib.criteria import (  # noqa: E402
    A_ROE_MIN,
    C_QUARTERLY_EPS_MIN,
    A_ANNUAL_EPS_MIN,
    CRITERIA_KEYS,
    I_COMBINED_HOLDING_MIN,
    L_RS_MIN,
    N_HIGH_PROXIMITY_MAX,
    S_VOLUME_SURGE_MIN,
    evaluate_a,
    evaluate_c,
    evaluate_c_detailed,
    evaluate_i,
    evaluate_l,
    evaluate_m,
    evaluate_n,
    evaluate_s,
)
from canslim_lib.score import compute_score  # noqa: E402

OUTPUT = ROOT / "public" / "data" / "can-slim-candidates.json"


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


def collect_raw_data(
    code: str,
    name: str,
    market: str,
    corp_map: dict[str, str],
) -> dict | None:
    """1차 패스: 종목별 원시 데이터 수집. RS는 아직 계산하지 않음."""
    ig = fetch_integration(code)
    if not ig:
        return None
    market_cap = ig["market_cap_eok"]
    if market_cap < 500:
        return None

    ann = fetch_annual(code)
    qtr = fetch_quarter(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    annual_roe = get_row_values(ann, "ROE") if ann else []
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    quarter_sales = get_row_values(qtr, "매출액") if qtr else []

    # DART 분기 EPS 보강:
    #  - 과거 보강: Naver 최근 5분기에 빠진 옛 분기 (Naver latest_year-1 의 Q1/Q2/Q3)
    #  - 최신 확정: 현재년도 Q1 분기보고서가 공시된 경우 컨센서스 → 확정값으로 갱신
    corp_code = corp_map.get(code)
    if corp_code and quarter_eps:
        from datetime import datetime
        current_year = datetime.now().year
        naver_latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else current_year
        dart_combined: list[tuple[str, float]] = []
        # 과거 보강 (latest_year - 1)
        old = fetch_dart_quarterly_eps_history(corp_code, naver_latest_year - 1)
        if old:
            dart_combined.extend(old)
        # 최신 확정 (current_year, naver보다 앞서면)
        if current_year >= naver_latest_year:
            new = fetch_dart_quarterly_eps_history(corp_code, current_year)
            if new:
                dart_combined.extend(new)
        if dart_combined:
            quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_combined)

    chart = fetch_yahoo_chart(yahoo_symbol(code, market), "1y", "1d")
    if not chart or len(chart["closes"]) < 200:
        return None

    # 기관 보유율 (DART) — 키 없거나 매핑 없으면 None
    corp_code = corp_map.get(code)
    institutional = fetch_majorstock_holding(corp_code) if corp_code else None

    # 12개월 수익률 (RS 백분위 계산용)
    closes = chart["closes"]
    twelve_m_return = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0.0

    return {
        "code": code,
        "name": name,
        "market": market,
        "ig": ig,
        "annual_eps": annual_eps,
        "annual_roe": annual_roe,
        "quarter_eps": quarter_eps,
        "quarter_sales": quarter_sales,
        "chart": chart,
        "institutional": institutional,
        "twelve_m_return": twelve_m_return,
    }


def evaluate_with_rs(
    raw: dict,
    kospi_closes: list[float],
    market_passed: bool,
    universe_returns: list[float] | None = None,
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

    criteria_out = {
        k: {"pass": r[0], "value": r[1], "detail": r[2]}
        for k, r in results.items()
    }
    criteria_out["C"].update(c_detailed)

    return {
        "code": raw["code"],
        "name": raw["name"],
        "market": raw["market"],
        "score": score,
        "grade": grade,
        "passed_count": passed_count,
        "market_cap_eok": int(ig["market_cap_eok"]),
        "per": ig["per"],
        "pbr": ig["pbr"],
        "dividend_yield": ig["dividend_yield"],
        "foreign_ownership": ig["foreign_ownership"],
        "institutional_pct": inst_pct,
        "institutional_trend": inst_trend,
        "twelve_m_return": round(raw["twelve_m_return"], 2),
        "current_price": int(ig["price"]) if ig["price"] else int(chart["closes"][-1]),
        "criteria": criteria_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CAN SLIM 한국 시장 스크리너 (한국 보정판)")
    parser.add_argument("--limit", type=int, default=0, help="시총 상위 N개만 평가")
    parser.add_argument("--market", choices=["all", "kospi", "kosdaq"], default="all", help="대상 시장")
    parser.add_argument("--market-only", action="store_true", help="시장 추세(M)만 판정")
    parser.add_argument("--ticker", help="단일 종목 코드만 평가")
    parser.add_argument("--save", action="store_true", help="결과 JSON 저장")
    args = parser.parse_args()

    print("🎯 CAN SLIM 스크리너 (한국 보정판 v1)\n")
    print(f"  임계값: C +{C_QUARTERLY_EPS_MIN}%, A +{A_ANNUAL_EPS_MIN}%/ROE {A_ROE_MIN}%+, "
          f"N -{N_HIGH_PROXIMITY_MAX}%, S +{S_VOLUME_SURGE_MIN}%, L RS{L_RS_MIN}+, I {I_COMBINED_HOLDING_MIN}%+\n")

    market_state, kospi_closes = fetch_market_state()

    if args.market_only:
        print(f"\n  최종: {market_state['verdict']}")
        print(f"  세부: {market_state['detail']}")
        return

    # corp_code 매핑 (기관 데이터용)
    print("📦 DART corp_code 매핑 로드...")
    corp_map = load_corp_code_map()
    print(f"  {len(corp_map)}개 상장사 매핑")

    # 단일 종목 모드
    if args.ticker:
        code = args.ticker
        market = "KOSPI"
        ch_ks = fetch_yahoo_chart(f"{code}.KS", "1mo", "1d")
        ch_kq = fetch_yahoo_chart(f"{code}.KQ", "1mo", "1d")
        if ch_kq and not ch_ks:
            market = "KOSDAQ"

        raw = collect_raw_data(code, code, market, corp_map)
        if not raw:
            print(f"  {code}: 데이터 수집 실패")
            return
        result = evaluate_with_rs(raw, kospi_closes, market_state["passed"], None)
        _print_one(result)
        return

    # 전체 스캔: 2-pass
    print("\n📋 종목 리스트 수집...")
    if args.market in ("all", "kospi"):
        kospi = fetch_stock_list("KOSPI")
        print(f"  KOSPI: {len(kospi)}")
    else:
        kospi = []
    if args.market in ("all", "kosdaq"):
        kosdaq = fetch_stock_list("KOSDAQ")
        print(f"  KOSDAQ: {len(kosdaq)}")
    else:
        kosdaq = []

    universe = kospi + kosdaq
    if args.limit:
        universe = universe[: args.limit]
        print(f"  → 상위 {len(universe)}개로 제한 (시장: {args.market})")

    # ── Pass 1: 원시 데이터 수집 (12M 수익률 포함) ──
    print(f"\n🔬 Pass 1: 원시 데이터 수집 ({len(universe)}종목)\n")
    raw_data: list[dict] = []
    fail = 0
    start = time.time()

    for i, s in enumerate(universe):
        try:
            raw = collect_raw_data(s["code"], s["name"], s["market"], corp_map)
        except Exception:
            raw = None
        if raw:
            raw_data.append(raw)
        else:
            fail += 1
        if (i + 1) % 25 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(universe) - i - 1) / rate if rate > 0 else 0
            print(f"  ... {i + 1}/{len(universe)} 수집 ({rate:.1f}/s, ETA {eta / 60:.1f}분)")

    print(f"\n  Pass 1 완료: 수집 {len(raw_data)}개, 실패 {fail}")

    # ── Pass 2: universe 백분위 RS + 점수화 ──
    universe_returns = [r["twelve_m_return"] for r in raw_data]
    print(f"\n📈 Pass 2: RS 백분위 계산 + 점수화 (universe {len(universe_returns)}개)\n")

    results = []
    for raw in raw_data:
        try:
            r = evaluate_with_rs(raw, kospi_closes, market_state["passed"], universe_returns)
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
        out = {
            "generated_at": today_iso(),
            "scanned_count": len(universe),
            "evaluated_count": len(results),
            "market_status": {
                "kospi_trend_verdict": market_state["verdict"],
                "passed": market_state["passed"],
                "value": market_state["value"],
                "detail": market_state["detail"],
                "kospi_close": market_state.get("kospi_close"),
            },
            "candidates": results,
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
