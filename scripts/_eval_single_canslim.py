"""단일 종목 A·N·S·L 원칙 단독 평가 (cascading 필터와 별개).

A/S 미통과로 후속 JSON 에서 잘린 종목의 각 글자별 raw 점수를 보고 싶을 때 사용.

사용법: python3 _eval_single_canslim.py [code] [name] [market]
       (인자 생략 시 HD현대에너지솔루션 기본값)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import concurrent.futures
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
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

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from canslim_lib.fetch import (
    DART_API,
    UA,
    dart_get,
    fetch_annual,
    fetch_dart_quarterly_eps_history,
    fetch_integration,
    fetch_quarter,
    fetch_stock_list,
    fetch_yahoo_chart,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    resolve_corp_code,
    yahoo_symbol,
)
from canslim_lib.criteria_a import (
    evaluate_a_detailed,
    evaluate_turnaround_detailed,
    evaluate_new_listing_detailed,
    compute_a_score,
)
from canslim_lib.criteria_s import evaluate_s


# screen_canslim_a.py 의 helper 들을 inline 화 (import 시 sys.stdout 재할당 사이드이펙트 회피)
def fetch_dart_annual_eps(corp_code: str, year: int):
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        for it in items:
            if it.get("sj_div") not in ("IS", "CIS"):
                continue
            name = (it.get("account_nm") or "").replace(" ", "")
            if any(k in name for k in ("기본주당이익", "기본주당순이익", "기본및희석주당이익", "주당순이익", "기본주당손익")):
                raw = it.get("thstrm_amount")
                if raw and raw not in ("-", ""):
                    try:
                        return float(str(raw).replace(",", ""))
                    except (ValueError, TypeError):
                        continue
    return None


def fetch_dart_annual_cfo(corp_code: str, year: int):
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        for it in items:
            if it.get("sj_div") != "CF":
                continue
            nm = (it.get("account_nm") or "").replace(" ", "")
            if any(k in nm for k in ("영업활동현금흐름", "영업활동으로인한현금흐름", "영업활동순현금흐름", "영업활동에서창출된현금")):
                raw = it.get("thstrm_amount")
                if raw and raw not in ("-", ""):
                    try:
                        return float(str(raw).replace(",", ""))
                    except (ValueError, TypeError):
                        continue
    return None


def fetch_dart_annual_pretax_margin(corp_code: str, year: int):
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        sales_val = None
        pretax_val = None
        for it in items:
            if it.get("sj_div") not in ("IS", "CIS"):
                continue
            nm = (it.get("account_nm") or "").replace(" ", "")
            raw = it.get("thstrm_amount")
            if not raw or raw in ("-", ""):
                continue
            try:
                v = float(str(raw).replace(",", ""))
            except (ValueError, TypeError):
                continue
            if sales_val is None and any(k in nm for k in ("매출액", "수익(매출액)", "영업수익")):
                sales_val = v
            if pretax_val is None and any(k in nm for k in ("법인세비용차감전순이익", "법인세비용차감전이익", "법인세차감전순이익", "법인세차감전이익", "법인세차감전계속사업이익")):
                pretax_val = v
            if sales_val and pretax_val:
                break
        if sales_val and pretax_val and sales_val > 0:
            return round(pretax_val / sales_val * 100, 2)
    return None


def fetch_dart_industry_code(corp_code: str):
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return None
    url = f"{DART_API}/company.json?crtfc_key={api_key}&corp_code={corp_code}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
        return None
    if data.get("status") != "000":
        return None
    return data.get("induty_code") or None


def collect_quarterly_eps_tuples(code: str, corp_code):
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    if not corp_code:
        return quarter_eps
    if quarter_eps:
        latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else datetime.now().year
    else:
        latest_year = datetime.now().year
    dart_combined = []
    for delta in range(0, 5):
        year = latest_year - delta
        items = fetch_dart_quarterly_eps_history(corp_code, year)
        if items:
            dart_combined.extend(items)
        time.sleep(0.1)
    if dart_combined:
        quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_combined)
    return quarter_eps


def fetch_annual_eps_extended(code: str, corp_code):
    ann = fetch_annual(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    if len(annual_eps) >= 6 or not corp_code:
        return annual_eps
    have_years = {k[:4] for k, _ in annual_eps if len(k) >= 4 and k[:4].isdigit()}
    earliest_year = min(int(y) for y in have_years) if have_years else datetime.now().year
    augment = []
    for delta in range(1, 5):
        year = earliest_year - delta
        if str(year) in have_years:
            continue
        eps_val = fetch_dart_annual_eps(corp_code, year)
        if eps_val is not None:
            augment.append((f"{year}12", round(eps_val, 2)))
        time.sleep(0.15)
    return sorted(annual_eps + augment, key=lambda x: x[0])

TARGET_CODE = sys.argv[1] if len(sys.argv) > 1 else "322000"
TARGET_NAME = sys.argv[2] if len(sys.argv) > 2 else "HD현대에너지솔루션"
TARGET_MARKET = sys.argv[3] if len(sys.argv) > 3 else "KOSPI"

C_JSON = ROOT / "public" / "data" / "can-slim-candidates.json"

# L 평가용 컷오프 (fetch_l_rs.py 와 동일)
UNIVERSE_SIZE = 300
RS_CUTOFF = 80
DEBT_THRESHOLD = 130.0
DEBT_REDUCTION_PP = 20.0


def find_c_entry(code: str) -> dict | None:
    data = json.loads(C_JSON.read_text(encoding="utf-8"))
    for c in data.get("candidates", []):
        if c["code"] == code:
            return c
    return None


def evaluate_a_for_target(c_entry: dict) -> dict:
    code = c_entry["code"]
    corp_map = load_corp_code_map()
    corp_code, _ = resolve_corp_code(code, corp_map)

    ann = fetch_annual(code)
    annual_eps = fetch_annual_eps_extended(code, corp_code)
    annual_roe = get_row_values(ann, "ROE") if ann else []

    # CPS
    annual_cps: list[tuple[str, float]] = []
    market_cap_eok = c_entry.get("market_cap_eok") or 0
    current_price = c_entry.get("current_price") or 0
    if corp_code and market_cap_eok > 0 and current_price > 0:
        shares_outstanding = market_cap_eok * 1e8 / current_price
        if shares_outstanding > 0:
            cps_years = sorted({int(k[:4]) for k, _ in annual_eps[-3:] if k[:4].isdigit()})
            for y in cps_years:
                cfo = fetch_dart_annual_cfo(corp_code, y)
                if cfo is not None:
                    cps = cfo / shares_outstanding
                    annual_cps.append((f"{y}12", round(cps, 2)))
                time.sleep(0.1)

    induty_code = fetch_dart_industry_code(corp_code) if corp_code else None
    pretax_margin = None
    if corp_code and annual_eps:
        latest_year_str = annual_eps[-1][0][:4] if annual_eps[-1][0][:4].isdigit() else None
        if latest_year_str:
            pretax_margin = fetch_dart_annual_pretax_margin(corp_code, int(latest_year_str))

    quarterly_eps_tuples = collect_quarterly_eps_tuples(code, corp_code)
    prelim_quarter = c_entry["criteria"]["C"].get("latest_quarter")
    prelim_eps_value = c_entry["criteria"]["C"].get("latest_eps")
    prelim_is_p = c_entry["criteria"]["C"].get("latest_is_preliminary", False)
    if prelim_is_p and prelim_quarter and prelim_eps_value is not None:
        if not any(p == prelim_quarter for p, _ in quarterly_eps_tuples):
            quarterly_eps_tuples = sorted(
                list(quarterly_eps_tuples) + [(prelim_quarter, float(prelim_eps_value))]
            )
    quarterly_eps_for_stability = [v for _, v in quarterly_eps_tuples]

    ttm_eps = None
    ttm_period = None
    annual_eps_for_a = list(annual_eps)
    annual_last_period = annual_eps[-1][0] if annual_eps else "000000"
    if len(quarterly_eps_tuples) >= 4:
        ttm_eps = round(sum(v for _, v in quarterly_eps_tuples[-4:]), 2)
        ttm_period = quarterly_eps_tuples[-1][0]
        if ttm_period > annual_last_period:
            annual_eps_for_a = list(annual_eps) + [(f"TTM_{ttm_period}", ttm_eps)]

    latest_qy = c_entry["criteria"]["C"].get("yoy_pct")
    eps_yoy_history_raw = c_entry["criteria"]["C"].get("eps_yoy_history") or []
    quarterly_eps_yoy_history = [(str(p), float(v)) for p, v in eps_yoy_history_raw]

    a_main = evaluate_a_detailed(
        annual_eps=annual_eps_for_a,
        annual_roe=annual_roe,
        annual_cps=annual_cps,
        latest_quarter_yoy=latest_qy,
        induty_code=induty_code,
        quarterly_eps_for_stability=quarterly_eps_for_stability,
    )
    a_main["pretax_margin"] = pretax_margin
    a_main["ttm_eps"] = ttm_eps
    a_main["ttm_period"] = ttm_period

    a_score = compute_a_score(a_main)
    a_main["a_score"] = a_score

    t_detail = None
    n_detail = None
    if not a_main["main_track_pass"]:
        t_detail = evaluate_turnaround_detailed(
            annual_eps=annual_eps,
            annual_roe=annual_roe,
            quarterly_eps_yoy_history=quarterly_eps_yoy_history,
            latest_quarter_yoy=latest_qy,
            induty_code=induty_code,
            quarterly_eps_for_stability=quarterly_eps_for_stability,
        )
        if not (t_detail["turnaround_pass"] or t_detail["preliminary_turnaround_pass"]):
            if len(annual_eps) < 4:
                sales_yoy_history_raw = c_entry["criteria"]["C"].get("sales_yoy_history") or []
                sales_yoy_history = [(str(p), float(v)) for p, v in sales_yoy_history_raw]
                n_detail = evaluate_new_listing_detailed(
                    annual_eps=annual_eps,
                    quarterly_eps_yoy_history=quarterly_eps_yoy_history,
                    sales_yoy_history=sales_yoy_history,
                    induty_code=induty_code,
                    annual_roe=annual_roe,
                    quarterly_eps_for_stability=quarterly_eps_for_stability,
                )

    return {
        "main": a_main,
        "turnaround": t_detail,
        "new_listing": n_detail,
        "annual_eps": annual_eps,
        "annual_roe": annual_roe,
        "induty_code": induty_code,
    }


def evaluate_n_for_target(code: str, market: str) -> dict:
    symbol = yahoo_symbol(code, market)
    chart = fetch_yahoo_chart(symbol, range_="1y", interval="1d")
    if not chart or not chart.get("closes"):
        return {"error": "Yahoo 1y 차트 미수집"}
    closes = chart["closes"]
    last = closes[-1]
    high = max(closes)
    pct_from_high = (last - high) / high * 100
    return {
        "current_price": last,
        "high_52w": high,
        "pct_from_52w_high": round(pct_from_high, 2),
    }


def evaluate_s_for_target(c_entry: dict) -> dict:
    code = c_entry["code"]
    corp_map = load_corp_code_map()
    corp_code, _ = resolve_corp_code(code, corp_map)
    market_cap_eok = c_entry.get("market_cap_eok") or 0
    current_price = c_entry.get("current_price") or 0
    if market_cap_eok == 0:
        integ = fetch_integration(code)
        if integ:
            market_cap_eok = integ.get("market_cap_eok") or 0
            if not current_price:
                current_price = integ.get("price") or 0
    return evaluate_s(
        code=code,
        corp_code=corp_code,
        market_cap_eok=market_cap_eok,
        current_price=current_price,
        debt_ratio_threshold=DEBT_THRESHOLD,
        debt_reduction_threshold_pp=DEBT_REDUCTION_PP,
    )


def fetch_return(stock: dict) -> dict | None:
    code = stock["code"]
    market = stock["market"]
    symbol = yahoo_symbol(code, market)
    chart = fetch_yahoo_chart(symbol, range_="1y", interval="1d")
    if not chart or len(chart.get("closes", [])) < 200:
        return None
    closes = chart["closes"]
    first = closes[0]
    last = closes[-1]
    if first <= 0:
        return None
    return {
        "code": code,
        "name": stock["name"],
        "return_1y_pct": (last - first) / first * 100,
    }


def evaluate_l_for_target(code: str, name: str, market: str) -> dict:
    kospi = fetch_stock_list("KOSPI")
    universe = kospi[:UNIVERSE_SIZE]
    universe_codes = {s["code"] for s in universe}
    in_univ = code in universe_codes
    targets = list(universe)
    if not in_univ:
        targets.append({"code": code, "name": name, "market": market})

    returns: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(fetch_return, s) for s in targets]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            if r:
                returns.append(r)

    pop = [r for r in returns if r["code"] in universe_codes]
    pop_sorted = sorted(pop, key=lambda r: r["return_1y_pct"])
    n = len(pop_sorted)
    target = next((r for r in returns if r["code"] == code), None)
    if not target or n < 2:
        return {"error": "RS 산출 불가"}
    t_ret = target["return_1y_pct"]
    if code in universe_codes:
        idx = next(i for i, r in enumerate(pop_sorted) if r["code"] == code)
        rs = int(round(1 + 98 * idx / (n - 1)))
    else:
        lower = sum(1 for pr in pop_sorted if pr["return_1y_pct"] < t_ret)
        rs = int(round(1 + 98 * lower / (n - 1)))
    rs = max(1, min(99, rs))
    rank_above = sum(1 for r in pop_sorted if r["return_1y_pct"] > t_ret)
    return {
        "return_1y_pct": round(t_ret, 2),
        "rs_score": rs,
        "rank": rank_above + 1,
        "universe_size": n,
        "in_universe": in_univ,
        "passes_l": rs >= RS_CUTOFF,
        "pop_min": pop_sorted[0]["return_1y_pct"],
        "pop_median": pop_sorted[n // 2]["return_1y_pct"],
        "pop_max": pop_sorted[-1]["return_1y_pct"],
    }


def main() -> None:
    print(f"📊 {TARGET_NAME} ({TARGET_CODE}) 단독 평가\n", file=sys.stderr)

    c_entry = find_c_entry(TARGET_CODE)
    if not c_entry:
        print(f"❌ C JSON에 {TARGET_CODE} 없음. 먼저 screen_canslim.py 실행 필요", file=sys.stderr)
        sys.exit(1)
    print(f"  C 결과: pass={c_entry['criteria']['C']['pass']}, "
          f"YoY={c_entry['criteria']['C'].get('yoy_pct')}%, "
          f"매출 YoY={c_entry['criteria']['C'].get('sales_yoy_pct')}%", file=sys.stderr)

    print("\n[A] 평가…", file=sys.stderr)
    a_res = evaluate_a_for_target(c_entry)

    print("[N] 평가…", file=sys.stderr)
    n_res = evaluate_n_for_target(TARGET_CODE, TARGET_MARKET)

    print("[S] 평가…", file=sys.stderr)
    s_res = evaluate_s_for_target(c_entry)

    print("[L] KOSPI 300 모집단 수집·RS 산출…", file=sys.stderr)
    l_res = evaluate_l_for_target(TARGET_CODE, TARGET_NAME, TARGET_MARKET)

    print("\n" + "=" * 70)
    print(f"  {TARGET_NAME} ({TARGET_CODE}) — A / N / S / L 단독 평가")
    print("=" * 70)

    # A 출력
    am = a_res["main"]
    print(f"\n  [A] 연간 실적 (Annual Earnings)")
    print(f"  ─ 연간 EPS 시계열: {a_res['annual_eps']}")
    print(f"  ─ 3년 EPS 성장: {am.get('three_year_growths')}")
    print(f"  ─ 3년 평균 성장률: {am.get('three_year_avg_growth')}%")
    print(f"  ─ 최신 ROE: {am.get('latest_roe')}%")
    print(f"  ─ 산업코드(KSIC): {a_res['induty_code']} / 경기민감주: {am.get('cyclical')}")
    print(f"  ─ TTM EPS: {am.get('ttm_eps')} ({am.get('ttm_period')})")
    print(f"  ─ 메인 트랙: {'✅ 통과' if am['main_track_pass'] else '❌ 미달'}")
    if not am['main_track_pass']:
        print(f"    사유: {'; '.join(am['fail_reasons'])}")
    t = a_res["turnaround"]
    if t:
        if t["turnaround_pass"]:
            print(f"  ─ 턴어라운드 트랙: 🔄 정통 통과")
        elif t["preliminary_turnaround_pass"]:
            print(f"  ─ 턴어라운드 트랙: 🟡 예비 통과")
        else:
            print(f"  ─ 턴어라운드 트랙: ❌ 미달 — {'; '.join(t['fail_reasons'])}")
        print(f"    연 EPS YoY {t.get('latest_annual_yoy')}% / 2분기 급증: {t.get('two_quarter_surge_detail')}")
        print(f"    TTM 사상최고 ratio: {t.get('ttm_to_high_ratio')}")
    nl = a_res["new_listing"]
    if nl:
        if nl["new_listing_pass"]:
            print(f"  ─ 신규 상장 트랙: 🆕 통과 (연 데이터 {nl['annual_eps_count']}년)")
        else:
            print(f"  ─ 신규 상장 트랙: ❌ 미달 — {'; '.join(nl['fail_reasons'])}")
    print(f"  ─ A 충족도 점수: {am['a_score']['total']}점 ({am['a_score']['tier']})")
    if am.get("badges"):
        print(f"  ─ 배지: {', '.join(am['badges'])}")

    # N 출력
    print(f"\n  [N] 신고가 (52주 신고가 대비)")
    if "error" in n_res:
        print(f"  ─ {n_res['error']}")
    else:
        print(f"  ─ 현재가: {n_res['current_price']:,.0f}")
        print(f"  ─ 52주 고점: {n_res['high_52w']:,.0f}")
        print(f"  ─ 고점 대비: {n_res['pct_from_52w_high']:+.2f}%")
        print(f"  ─ ※ N 페이지 노출은 A 점수 80+ 한정. 자동 정량 컷오프 없음 (raw 값).")

    # S 출력
    print(f"\n  [S] 수급 (Supply & Demand)")
    print(f"  ─ 부채비율: {s_res.get('debt_ratio_current')}% (컷오프 {DEBT_THRESHOLD}%)")
    print(f"  ─ 부채비율 5분기 추세: {s_res.get('debt_ratio_quarterly_trend')}")
    print(f"  ─ 부채비율 3년 추세: {s_res.get('debt_ratio_annual_trend')}")
    print(f"  ─ 경영진 보유: {s_res.get('insider_pct')}%")
    print(f"  ─ 유통물량 비율: {s_res.get('float_pct')}%")
    print(f"  ─ 5년 내 주식분할: {s_res.get('split_count_5y')}회")
    print(f"  ─ 최근 3년 자사주매입 누적: {s_res.get('buyback_total_pct')}%")
    if s_res.get("buyback_large_label"):
        print(f"    🏷  자사주 매우 큰 매입")
    if s_res.get("debt_reduction_annual_label"):
        print(f"    🏷  연간 부채 크게 감소")
    if s_res.get("debt_reduction_quarterly_label"):
        print(f"    🏷  분기 부채 크게 감소")
    if s_res.get("split_warning_label"):
        print(f"    🏷  주식 분할 주의")
    print(f"  ─ 판정: {'✅ 통과' if s_res['pass_s'] else '❌ 미달'}")
    if not s_res['pass_s']:
        print(f"    사유: {'; '.join(s_res['fail_reasons'])}")

    # L 출력
    print(f"\n  [L] 주도주 (Relative Strength)")
    if "error" in l_res:
        print(f"  ─ {l_res['error']}")
    else:
        print(f"  ─ 1년 수익률: {l_res['return_1y_pct']:+.2f}%")
        print(f"  ─ 모집단 내 순위: {l_res['rank']} / {l_res['universe_size']} "
              f"(상위 {l_res['rank']/l_res['universe_size']*100:.1f}%)")
        print(f"  ─ RS 점수: {l_res['rs_score']}")
        rs_v = l_res["rs_score"]
        verdict = "✅ 통과 (RS ≥ 80)" if l_res["passes_l"] else f"❌ 미달 (RS {rs_v} < 80)"
        print(f"  ─ 판정: {verdict}")
        print(f"  ─ 모집단 분포: 최저 {l_res['pop_min']:+.1f}% / 중간 {l_res['pop_median']:+.1f}% / 최고 {l_res['pop_max']:+.1f}%")
        if not l_res['in_universe']:
            print(f"  ─ ※ KOSPI 시총 상위 {UNIVERSE_SIZE} 밖 (보강 종목)")

    # 종합 요약
    print(f"\n  ─── 종합 ───")
    a_pass = am['main_track_pass'] or (t and (t['turnaround_pass'] or t['preliminary_turnaround_pass'])) or (nl and nl['new_listing_pass'])
    a_tag = "✅" if a_pass else "❌"
    print(f"  A {a_tag} · N — (raw) · S {'✅' if s_res['pass_s'] else '❌'} · L {'✅' if l_res.get('passes_l') else '❌'}")


if __name__ == "__main__":
    main()
