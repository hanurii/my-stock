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
    fetch_dart_quarterly_sales_history,
    fetch_integration,
    fetch_majorstock_holding,
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
    min_price: int = 0,
) -> dict | None:
    """1차 패스: 종목별 원시 데이터 수집. RS는 아직 계산하지 않음."""
    ig = fetch_integration(code)
    if not ig:
        return None
    market_cap = ig["market_cap_eok"]
    if market_cap < 500:
        return {"_skipped_small_cap": True, "market_cap_eok": market_cap}

    if min_price > 0:
        price_val = ig.get("price") or 0
        if price_val < min_price:
            return {"_skipped_low_price": True, "price": price_val}

    ann = fetch_annual(code)
    qtr = fetch_quarter(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    annual_roe = get_row_values(ann, "ROE") if ann else []
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    quarter_sales = get_row_values(qtr, "매출액") if qtr else []

    # DART 분기 EPS 보강:
    #  - 과거 보강: Naver 최근 5분기에 빠진 옛 분기 (Naver latest_year-1 의 Q1/Q2/Q3)
    #  - 최신 확정: 현재년도 Q1 분기보고서가 공시된 경우 컨센서스 → 확정값으로 갱신
    #  - 잠정실적: 분기보고서 미공시이지만 잠정실적 발표된 분기 추가 (latest_is_preliminary 플래그)
    # 우선주(예: 005935 삼성전자우)는 corp_map 직접 매칭 없으므로 보통주(005930) corp_code 로 fallback.
    preliminary_period: str | None = None
    preliminary_rcept_no: str | None = None
    corp_code, common_code = resolve_corp_code(code, corp_map)
    if corp_code and quarter_eps:
        from datetime import datetime
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

    # Yahoo 가격 데이터 — N/L/M 원칙에만 필요. 부족해도 C/A/S/I 평가는 가능하므로
    # 통째 제외하지 않고 빈 chart 로 진행 (글자별 평가 함수가 내부에서 데이터 부족 처리).
    chart = fetch_yahoo_chart(yahoo_symbol(code, market), "1y", "1d")
    if not chart:
        chart = {"closes": [], "volumes": [], "timestamps": []}

    # 기관 보유율 (DART) — 우선주 케이스에서도 보통주 corp_code 사용
    institutional = fetch_majorstock_holding(corp_code) if corp_code else None

    # 12개월 수익률 (RS 백분위 계산용, 가격 데이터 부족 시 0)
    closes = chart["closes"]
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
        "current_price": int(ig["price"]) if ig["price"] else (int(chart["closes"][-1]) if chart.get("closes") else 0),
        "criteria": criteria_out,
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
                        help="현재가가 이 KRW 미만이면 DART 호출 전에 스킵 (default 0 = 비활성)")
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
    if args.offset:
        universe = universe[args.offset:]
        print(f"  → 시총 {args.offset + 1}위부터 (offset {args.offset})")
    if args.limit:
        universe = universe[: args.limit]
    print(f"  → 평가 대상 {len(universe)}종목 (시장: {args.market}, offset {args.offset}, limit {args.limit or '없음'})")

    # ── Pass 1: 원시 데이터 수집 (12M 수익률 포함) ──
    print(f"\n🔬 Pass 1: 원시 데이터 수집 ({len(universe)}종목)\n")
    raw_data: list[dict] = []
    fail = 0
    skipped_low_price = 0
    skipped_small_cap = 0
    start = time.time()

    failed_stocks: list[dict] = []
    for i, s in enumerate(universe):
        err_msg = ""
        try:
            raw = collect_raw_data(s["code"], s["name"], s["market"], corp_map,
                                   min_price=args.min_price)
        except Exception as e:
            raw = None
            err_msg = repr(e)
        if raw and raw.get("_skipped_small_cap"):
            skipped_small_cap += 1
        elif raw and raw.get("_skipped_low_price"):
            skipped_low_price += 1
        elif raw:
            raw_data.append(raw)
        else:
            fail += 1
            failed_stocks.append({"code": s["code"], "name": s["name"], "market": s["market"], "error": err_msg or "fetch_integration None (Naver 응답 없음)"})
        if (i + 1) % 25 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(universe) - i - 1) / rate if rate > 0 else 0
            print(f"  ... {i + 1}/{len(universe)} 수집 ({rate:.1f}/s, ETA {eta / 60:.1f}분)")

    print(f"\n  Pass 1 완료: 평가 진입 {len(raw_data)}개")
    print(f"    🪙 시총 500억 미만 제외: {skipped_small_cap}종목")
    if args.min_price:
        print(f"    💰 최소가 {args.min_price:,}원 미만 제외: {skipped_low_price}종목")
    print(f"    ❌ 진짜 실패(Naver 데이터 X): {fail}종목")
    if failed_stocks:
        print("  실패 종목:")
        for fs in failed_stocks:
            print(f"    - {fs['code']} {fs['name']} ({fs['market']}): {fs['error']}")

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
            "scanned_count": len(universe),
            "evaluated_count": len(candidates_final),
            "scan_meta": {
                "offset": args.offset,
                "limit": args.limit,
                "market": args.market,
                "merged": args.merge,
                "min_price": args.min_price,
                "skipped_low_price_count": skipped_low_price,
                "skipped_small_cap_count": skipped_small_cap,
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
