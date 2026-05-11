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
from canslim_lib.criteria_a import evaluate_a_detailed, evaluate_turnaround_detailed  # noqa: E402


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
    """page.tsx 의 main 필터와 동일 — C 노출 조건 검사."""
    yoy = criteria_c.get("yoy_pct")
    if yoy is None:
        return False
    if yoy < C_QUARTERLY_EPS_THRESHOLD:
        return False
    sales_yoy = criteria_c.get("sales_yoy_pct")
    sales_accel = criteria_c.get("sales_accel_3q", False)
    sales_pass = (sales_yoy is not None and sales_yoy >= C_SALES_THRESHOLD) or sales_accel
    return sales_pass


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
    for idx, cand in enumerate(c_passed, start=1):
        code = cand["code"]
        name = cand["name"]
        print(f"  [{idx}/{len(c_passed)}] {code} {name}")

        corp_code, _ = resolve_corp_code(code, corp_map)

        # 1) 연간 EPS·ROE
        ann = fetch_annual(code)
        annual_eps = fetch_annual_eps_extended(code, corp_code)
        annual_roe = get_row_values(ann, "ROE") if ann else []
        # CPS — Naver 미제공, v1 에서는 미수집
        annual_cps: list[tuple[str, float]] = []

        # 2) 산업 코드
        induty_code = fetch_dart_industry_code(corp_code) if corp_code else None

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
            if t_detail["turnaround_pass"]:
                badges_str = ", ".join(t_detail["badges"]) if t_detail["badges"] else "—"
                print(f"      🔄 턴어라운드 · 연 YoY {t_detail['latest_annual_yoy']}% · {t_detail['two_quarter_surge_detail']} · 배지: {badges_str}")
                turnaround_results.append({
                    "code": code,
                    "name": name,
                    "market": cand["market"],
                    "market_cap_eok": cand["market_cap_eok"],
                    "current_price": cand["current_price"],
                    "criteria_turnaround": t_detail,
                    "criteria_c_summary": c_summary,
                })
            else:
                main_reason = a_detail["fail_reasons"][0] if a_detail["fail_reasons"] else "?"
                t_reason = t_detail["fail_reasons"][0] if t_detail["fail_reasons"] else "?"
                print(f"      → 미통과: 메인({main_reason}) / 턴어라운드({t_reason})")

        time.sleep(0.3)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "c_input_count": len(c_passed),
        "a_passed_count": len(a_results),
        "turnaround_count": len(turnaround_results),
        "candidates": a_results,
        "turnaround_candidates": turnaround_results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 저장: {OUTPUT}")
    print(f"   C 노출 {len(c_passed)} → A 메인 {len(a_results)} + 턴어라운드 {len(turnaround_results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
