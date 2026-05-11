#!/usr/bin/env python3
"""CAN SLIM 'A' 원칙 (Annual Earnings) 스크리너 — C 와 격리.

입력: public/data/can-slim-candidates.json (C 통과 종목)
출력: public/data/can-slim-a-candidates.json (A 메인 트랙 통과 종목)

격리 원칙:
- C 코드/JSON 미수정. C 결과를 read-only 입력으로만 사용.
- evaluate_a_detailed (canslim_lib/criteria_a.py) 호출. 기존 evaluate_a (criteria.py) 미수정.

사용법:
  python scripts/screen_canslim_a.py
  python scripts/screen_canslim_a.py --limit 10  # 디버깅 용
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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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

from canslim_lib.fetch import (  # noqa: E402
    DART_API,
    UA,
    dart_get,
    fetch_annual,
    fetch_dart_quarterly_eps_history,
    fetch_quarter,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    resolve_corp_code,
)
from canslim_lib.criteria_a import (  # noqa: E402
    evaluate_a_detailed,
    evaluate_new_listing_detailed,
    evaluate_turnaround_detailed,
)


def fetch_dart_annual_eps(corp_code: str, year: int) -> float | None:
    """DART 사업보고서(11011)에서 연간 단일 EPS 조회.

    annual report 의 thstrm_amount 는 IS 항목에서 전년 회계연도 단일 값.
    """
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": fs_div,
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


def fetch_dart_annual_roe(corp_code: str, year: int) -> float | None:
    """DART 사업보고서에서 ROE 직접 조회 — DART 표준 재무제표엔 ROE 가 없으므로 None 반환.

    Naver 가 ROE 를 제공하므로 이 helper 는 보강용 placeholder.
    """
    return None


def fetch_dart_annual_cfo(corp_code: str, year: int) -> float | None:
    """DART 사업보고서(11011) 현금흐름표에서 영업활동현금흐름 (원, 연간 단일).

    sj_div='CF' 항목 중 "영업활동" 키워드 매칭. 회사마다 명칭 변형 다수.
    """
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": fs_div,
        })
        if not items:
            continue
        for it in items:
            if it.get("sj_div") != "CF":
                continue
            nm = (it.get("account_nm") or "").replace(" ", "")
            if any(k in nm for k in (
                "영업활동현금흐름",
                "영업활동으로인한현금흐름",
                "영업활동순현금흐름",
                "영업활동에서창출된현금",
            )):
                raw = it.get("thstrm_amount")
                if raw and raw not in ("-", ""):
                    try:
                        return float(str(raw).replace(",", ""))
                    except (ValueError, TypeError):
                        continue
    return None


def fetch_dart_annual_pretax_margin(corp_code: str, year: int) -> float | None:
    """DART 사업보고서에서 세전 순이익 마진율 = (법인세비용차감전이익 / 매출액) × 100.

    매출액 / 법인세비용차감전순이익 둘 다 IS 항목. 없으면 None.
    """
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": fs_div,
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

INPUT = ROOT / "public" / "data" / "can-slim-candidates.json"
OUTPUT = ROOT / "public" / "data" / "can-slim-a-candidates.json"

# C 페이지 노출 조건 (page.tsx 의 USER_C_THRESHOLD + 매출 동반과 동일)
C_QUARTERLY_EPS_THRESHOLD = 25.0
C_SALES_THRESHOLD = 25.0


def fetch_dart_industry_code(corp_code: str) -> str | None:
    """DART company.json — induty_code (KSIC) 조회.

    company.json 응답은 list 가 아니라 단일 dict 라서 dart_get() 사용 불가, 직접 호출.
    """
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


def passes_c_main(criteria_c: dict) -> bool:
    """page.tsx 의 main 필터와 동일 — C 노출 조건 검사.

    O'Neil 원전 강화: 가속 필수 + 경고 자동 제외.
    """
    yoy = criteria_c.get("yoy_pct")
    if yoy is None or yoy < C_QUARTERLY_EPS_THRESHOLD:
        return False
    sales_yoy = criteria_c.get("sales_yoy_pct")
    sales_accel = criteria_c.get("sales_accel_3q", False)
    sales_pass = (sales_yoy is not None and sales_yoy >= C_SALES_THRESHOLD) or sales_accel
    if not sales_pass:
        return False
    # O'Neil 원전 가속화 게이트
    accel_delta = criteria_c.get("accel_delta_pp") or 0
    eps_accel_3q = criteria_c.get("eps_accel_3q", False)
    if not (eps_accel_3q or accel_delta > 0):
        return False
    # 경고 자동 제외
    if (criteria_c.get("consecutive_decline_quarters") or 0) >= 2:
        return False
    if criteria_c.get("severe_decel"):
        return False
    return True


def collect_quarterly_eps_for_stability(code: str, corp_code: str | None) -> list[float]:
    """안정성 지수 계산용 12+ 분기 EPS 시계열 수집.

    Naver 분기 (최근 5분기) + DART 과거 보강 (최대 4년 ≈ 16분기) 머지.
    """
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    if not corp_code:
        return [v for _, v in quarter_eps]

    if quarter_eps:
        latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else datetime.now().year
    else:
        latest_year = datetime.now().year

    # 과거 4년 보강 (latest_year-1 ~ latest_year-4)
    dart_combined: list[tuple[str, float]] = []
    for delta in range(1, 5):
        year = latest_year - delta
        items = fetch_dart_quarterly_eps_history(corp_code, year)
        if items:
            dart_combined.extend(items)
        time.sleep(0.1)  # rate limit 보호
    if dart_combined:
        quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_combined)
    return [v for _, v in quarter_eps]


def fetch_annual_eps_extended(code: str, corp_code: str | None) -> list[tuple[str, float]]:
    """연간 EPS — Naver 우선 + 부족하면 DART 사업보고서(11011) 직접 조회로 보강.

    Naver 연간 데이터는 보통 3-4년 제공. 5년 연속 증가 배지 평가를 위해
    부족하면 DART 사업보고서에서 과거 연도 EPS 직접 조회.
    """
    ann = fetch_annual(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    if len(annual_eps) >= 6 or not corp_code:
        return annual_eps

    have_years = {k[:4] for k, _ in annual_eps if len(k) >= 4 and k[:4].isdigit()}
    earliest_year = min(int(y) for y in have_years) if have_years else datetime.now().year
    augment: list[tuple[str, float]] = []
    for delta in range(1, 5):
        year = earliest_year - delta
        if str(year) in have_years:
            continue
        eps_val = fetch_dart_annual_eps(corp_code, year)
        if eps_val is not None:
            augment.append((f"{year}12", round(eps_val, 2)))
        time.sleep(0.15)
    combined = sorted(annual_eps + augment, key=lambda x: x[0])
    return combined


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리 종목 상한 (디버그)")
    args = parser.parse_args()

    if not INPUT.exists():
        print(f"❌ 입력 파일 없음: {INPUT}")
        print("   먼저 scripts/screen_canslim.py 를 실행해 C 결과를 생성하세요.")
        return 1

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    all_candidates = data.get("candidates", [])
    c_passed = [c for c in all_candidates if passes_c_main(c.get("criteria", {}).get("C", {}))]
    print(f"📊 C 페이지 노출 종목: {len(c_passed)} / 평가 {len(all_candidates)}")

    if args.limit:
        c_passed = c_passed[: args.limit]
        print(f"  → --limit {args.limit} 적용 → {len(c_passed)}개 처리")

    corp_map = load_corp_code_map()

    a_results: list[dict] = []
    turnaround_results: list[dict] = []
    new_listing_results: list[dict] = []
    for idx, cand in enumerate(c_passed, start=1):
        code = cand["code"]
        name = cand["name"]
        print(f"  [{idx}/{len(c_passed)}] {code} {name}")

        corp_code, _ = resolve_corp_code(code, corp_map)

        # 1) 연간 EPS·ROE
        ann = fetch_annual(code)
        annual_eps = fetch_annual_eps_extended(code, corp_code)
        annual_roe = get_row_values(ann, "ROE") if ann else []

        # 1.5) CPS — DART 사업보고서 영업CF / 발행주식수 (시가총액×1e8/주가)
        annual_cps: list[tuple[str, float]] = []
        market_cap_eok = cand.get("market_cap_eok") or 0
        current_price = cand.get("current_price") or 0
        if corp_code and market_cap_eok > 0 and current_price > 0:
            shares_outstanding = market_cap_eok * 1e8 / current_price
            if shares_outstanding > 0:
                # 최근 3년 CPS 수집 (배지·추이 표시용)
                cps_years = sorted({
                    int(k[:4]) for k, _ in annual_eps[-3:] if k[:4].isdigit()
                })
                for y in cps_years:
                    cfo = fetch_dart_annual_cfo(corp_code, y)
                    if cfo is not None:
                        cps = cfo / shares_outstanding
                        annual_cps.append((f"{y}12", round(cps, 2)))
                    time.sleep(0.1)

        # 2) 산업 코드
        induty_code = fetch_dart_industry_code(corp_code) if corp_code else None

        # 2.5) 세전 순이익 마진율 (최근 사업연도) — ROE 낮은 종목 정렬 보완용
        pretax_margin = None
        if corp_code and annual_eps:
            latest_year_str = annual_eps[-1][0][:4] if annual_eps[-1][0][:4].isdigit() else None
            if latest_year_str:
                pretax_margin = fetch_dart_annual_pretax_margin(corp_code, int(latest_year_str))

        # 3) 안정성 지수용 12+ 분기 EPS
        quarterly_eps_for_stability = collect_quarterly_eps_for_stability(code, corp_code)

        # 4) 직전 분기 YoY 와 4분기 YoY 추이 (C JSON 재사용)
        latest_qy = cand["criteria"]["C"].get("yoy_pct")
        eps_yoy_history_raw = cand["criteria"]["C"].get("eps_yoy_history") or []
        quarterly_eps_yoy_history: list[tuple[str, float]] = [
            (str(p), float(v)) for p, v in eps_yoy_history_raw
        ]

        # 5) 메인 트랙 평가
        a_detail = evaluate_a_detailed(
            annual_eps=annual_eps,
            annual_roe=annual_roe,
            annual_cps=annual_cps,
            latest_quarter_yoy=latest_qy,
            induty_code=induty_code,
            quarterly_eps_for_stability=quarterly_eps_for_stability,
        )

        # 세전 마진율 + 우선도 점수 (정렬용)
        # Tier 1 (먼저 노출): 매년 ≥25% 성장 + ROE ≥17%
        # Tier 2: 위 미충족이고 ROE 낮으면 세전 마진율로 보충
        a_detail["pretax_margin"] = pretax_margin
        growths = a_detail.get("three_year_growths") or []
        roe = a_detail.get("latest_roe") or 0
        avg = a_detail.get("three_year_avg_growth") or 0
        stellar = (growths and all(g >= 25 for g in growths))
        score = roe + avg
        if stellar and roe >= 17:
            score += 100  # Tier 1 boost
        if 25 <= roe <= 50:
            score += 15
        elif roe > 50:
            score += 10  # 50% 초과는 약간 의심
        if 12 <= roe < 17 and pretax_margin is not None:
            # 세전 마진 보충: 15% 이상이면 가산점
            score += max(0, pretax_margin - 5)
        a_detail["priority_score"] = round(score, 2)
        a_detail["stellar_growth"] = bool(stellar)
        # 정렬 우선도가 명시되도록 stellar 종목엔 배지 상단 추가
        badges = a_detail.get("badges") or []
        if stellar and roe >= 17:
            badges = ["⭐ 매년 +25% 성장"] + [b for b in badges if b != "⭐ 매년 +25% 성장"]
            a_detail["badges"] = badges

        c_summary = {
            "yoy_pct": cand["criteria"]["C"].get("yoy_pct"),
            "latest_quarter": cand["criteria"]["C"].get("latest_quarter"),
            "sales_yoy_pct": cand["criteria"]["C"].get("sales_yoy_pct"),
        }

        if a_detail["main_track_pass"]:
            badges_str = ", ".join(a_detail["badges"]) if a_detail["badges"] else "—"
            print(f"      ✅ 메인 통과 · 3Y avg {a_detail['three_year_avg_growth']}% · ROE {a_detail['latest_roe']}% · 배지: {badges_str}")
            a_results.append({
                "code": code,
                "name": name,
                "market": cand["market"],
                "market_cap_eok": cand["market_cap_eok"],
                "current_price": cand["current_price"],
                "criteria_a": a_detail,
                "criteria_c_summary": c_summary,
            })
        else:
            # 6) 메인 미충족 → 턴어라운드 트랙 평가
            t_detail = evaluate_turnaround_detailed(
                annual_eps=annual_eps,
                annual_roe=annual_roe,
                quarterly_eps_yoy_history=quarterly_eps_yoy_history,
                latest_quarter_yoy=latest_qy,
                induty_code=induty_code,
                quarterly_eps_for_stability=quarterly_eps_for_stability,
            )
            if t_detail["turnaround_pass"] or t_detail["preliminary_turnaround_pass"]:
                is_prelim = not t_detail["turnaround_pass"] and t_detail["preliminary_turnaround_pass"]
                marker = "🟡 예비 턴어라운드" if is_prelim else "🔄 턴어라운드"
                badges_str = ", ".join(t_detail["badges"]) if t_detail["badges"] else "—"
                print(f"      {marker} · 연 YoY {t_detail['latest_annual_yoy']}% · {t_detail['two_quarter_surge_detail']} · 배지: {badges_str}")
                turnaround_results.append({
                    "code": code,
                    "name": name,
                    "market": cand["market"],
                    "market_cap_eok": cand["market_cap_eok"],
                    "current_price": cand["current_price"],
                    "criteria_turnaround": t_detail,
                    "is_preliminary": is_prelim,
                    "criteria_c_summary": c_summary,
                })
            else:
                # 7) 턴어라운드도 미통과 → 신규 상장 (<3년) 트랙 평가
                # 연간 EPS 데이터 부족 (DART 보강 후에도 4년 미달) 종목 대상
                new_listing_eligible = len(annual_eps) < 4
                if new_listing_eligible:
                    sales_yoy_history_raw = cand["criteria"]["C"].get("sales_yoy_history") or []
                    sales_yoy_history: list[tuple[str, float]] = [
                        (str(p), float(v)) for p, v in sales_yoy_history_raw
                    ]
                    n_detail = evaluate_new_listing_detailed(
                        annual_eps=annual_eps,
                        quarterly_eps_yoy_history=quarterly_eps_yoy_history,
                        sales_yoy_history=sales_yoy_history,
                        induty_code=induty_code,
                        annual_roe=annual_roe,
                        quarterly_eps_for_stability=quarterly_eps_for_stability,
                    )
                    if n_detail["new_listing_pass"]:
                        badges_str = ", ".join(n_detail["badges"]) if n_detail["badges"] else "—"
                        print(f"      🆕 신규 상장 · 연 데이터 {n_detail['annual_eps_count']}년 · 분기 EPS·매출 4분기 모두 +25%+ · 배지: {badges_str}")
                        new_listing_results.append({
                            "code": code,
                            "name": name,
                            "market": cand["market"],
                            "market_cap_eok": cand["market_cap_eok"],
                            "current_price": cand["current_price"],
                            "criteria_new_listing": n_detail,
                            "criteria_c_summary": c_summary,
                        })
                        time.sleep(0.3)
                        continue
                main_reason = a_detail["fail_reasons"][0] if a_detail["fail_reasons"] else "?"
                t_reason = t_detail["fail_reasons"][0] if t_detail["fail_reasons"] else "?"
                print(f"      → 미통과: 메인({main_reason}) / 턴어라운드({t_reason})")

        time.sleep(0.3)

    pure_count = sum(1 for t in turnaround_results if not t.get("is_preliminary"))
    prelim_count = sum(1 for t in turnaround_results if t.get("is_preliminary"))
    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "c_input_count": len(c_passed),
        "a_passed_count": len(a_results),
        "turnaround_count": pure_count,
        "preliminary_turnaround_count": prelim_count,
        "new_listing_count": len(new_listing_results),
        "candidates": a_results,
        "turnaround_candidates": turnaround_results,
        "new_listing_candidates": new_listing_results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 저장: {OUTPUT}")
    print(f"   C 노출 {len(c_passed)} → A 메인 {len(a_results)} + 턴어라운드 {pure_count} + 예비 {prelim_count} + 신규상장 {len(new_listing_results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
