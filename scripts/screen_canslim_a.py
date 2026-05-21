#!/usr/bin/env python3
"""CAN SLIM 'A' 원칙 (Annual Earnings) 스크리너 — v2 점수 체계.

입력: public/data/can-slim-candidates.json (C 통과 종목)
출력: public/data/can-slim-a-candidates.json (3트랙 분류 + 점수)

핵심 변화 (v1 → v2)
-------------------
- "메인 통과 / 미통과" 이분법 제거. 모든 종목이 점수를 받음.
- 3트랙 (정통 A · 턴어라운드 · 신규상장) 각 50점 만점.
- 단일 candidates 배열, 점수 내림차순 정렬.
- 마진은 점수에서 제외 (별도 라벨로 노출).
- 경기민감은 정보용 라벨만, 점수 영향 없음.

사용법:
  python scripts/screen_canslim_a.py
  python scripts/screen_canslim_a.py --limit 10
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
    evaluate_a_v2,
)


INPUT = ROOT / "public" / "data" / "can-slim-candidates.json"
OUTPUT = ROOT / "public" / "data" / "can-slim-a-candidates.json"

# C 페이지 노출 조건 (page.tsx 의 USER_C_THRESHOLD + 매출 동반과 동일)
C_QUARTERLY_EPS_THRESHOLD = 25.0
C_SALES_THRESHOLD = 25.0


# ────────────────────────────────────────────────────────
# DART 헬퍼
# ────────────────────────────────────────────────────────


def fetch_dart_annual_eps(corp_code: str, year: int) -> float | None:
    """DART 사업보고서(11011) 연간 단일 EPS."""
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


def fetch_dart_annual_pretax_margin(corp_code: str, year: int) -> float | None:
    """DART 사업보고서 세전 마진율 = (법인세비용차감전이익 / 매출액) × 100."""
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
            if pretax_val is None and any(k in nm for k in (
                "법인세비용차감전순이익", "법인세비용차감전이익",
                "법인세차감전순이익", "법인세차감전이익", "법인세차감전계속사업이익",
            )):
                pretax_val = v
            if sales_val and pretax_val:
                break
        if sales_val and pretax_val and sales_val > 0:
            return round(pretax_val / sales_val * 100, 2)
    return None


def fetch_dart_industry_code(corp_code: str) -> str | None:
    """DART company.json — induty_code (KSIC)."""
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


# ────────────────────────────────────────────────────────
# C 노출 필터 + 데이터 수집
# ────────────────────────────────────────────────────────


def passes_c_main(criteria_c: dict) -> bool:
    """src/app/stocks/canslim/lib/cFilter.ts 의 passesCGate 와 동일."""
    yoy = criteria_c.get("yoy_pct")
    if yoy is None or yoy < C_QUARTERLY_EPS_THRESHOLD:
        return False
    sales_yoy = criteria_c.get("sales_yoy_pct")
    sales_accel = criteria_c.get("sales_accel_3q", False)
    sales_pass = (sales_yoy is not None and sales_yoy >= C_SALES_THRESHOLD) or sales_accel
    if not sales_pass:
        return False
    quality = criteria_c.get("eps_accel_quality")
    eps_accel_3q = criteria_c.get("eps_accel_3q", False)
    quality_accel = quality in ("mild", "strong", "explosive")
    if not (eps_accel_3q or quality_accel):
        return False
    if (criteria_c.get("consecutive_decline_quarters") or 0) >= 2:
        return False
    if criteria_c.get("severe_decel"):
        return False
    return True


def collect_quarterly_eps_tuples(code: str, corp_code: str | None) -> list[tuple[str, float]]:
    """분기 EPS tuple 시계열 (period_key, eps)."""
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    if not corp_code:
        return quarter_eps

    if quarter_eps:
        latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else datetime.now().year
    else:
        latest_year = datetime.now().year

    dart_combined: list[tuple[str, float]] = []
    for delta in range(0, 5):
        year = latest_year - delta
        items = fetch_dart_quarterly_eps_history(corp_code, year)
        if items:
            dart_combined.extend(items)
        time.sleep(0.1)
    if dart_combined:
        quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_combined)
    return quarter_eps


def fetch_annual_eps_extended(code: str, corp_code: str | None) -> list[tuple[str, float]]:
    """연간 EPS — Naver 우선 + 부족 시 DART 사업보고서 보강 (최대 4년)."""
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


# ────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────


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

    candidates: list[dict] = []
    for idx, cand in enumerate(c_passed, start=1):
        code = cand["code"]
        name = cand["name"]
        print(f"  [{idx}/{len(c_passed)}] {code} {name}")

        corp_code, _ = resolve_corp_code(code, corp_map)

        # 1) 연간 EPS·ROE
        ann = fetch_annual(code)
        annual_eps = fetch_annual_eps_extended(code, corp_code)
        annual_roe = get_row_values(ann, "ROE") if ann else []

        # 2) 산업 코드
        induty_code = fetch_dart_industry_code(corp_code) if corp_code else None

        # 3) 세전 마진율 (최근 사업연도)
        pretax_margin = None
        if corp_code and annual_eps:
            latest_year_str = annual_eps[-1][0][:4] if annual_eps[-1][0][:4].isdigit() else None
            if latest_year_str:
                pretax_margin = fetch_dart_annual_pretax_margin(corp_code, int(latest_year_str))

        # 4) 분기 EPS 시계열 (안정성 + TTM)
        quarterly_eps_tuples = collect_quarterly_eps_tuples(code, corp_code)
        prelim_quarter = cand["criteria"]["C"].get("latest_quarter")
        prelim_eps_value = cand["criteria"]["C"].get("latest_eps")
        prelim_is_p = cand["criteria"]["C"].get("latest_is_preliminary", False)
        if prelim_is_p and prelim_quarter and prelim_eps_value is not None:
            if not any(p == prelim_quarter for p, _ in quarterly_eps_tuples):
                quarterly_eps_tuples = sorted(
                    list(quarterly_eps_tuples) + [(prelim_quarter, float(prelim_eps_value))]
                )
        quarterly_eps_for_stability = [v for _, v in quarterly_eps_tuples]

        # 5) TTM 처리 — 최근 분기가 결산 이후면 annual_eps 마지막에 TTM 추가
        annual_eps_for_a = list(annual_eps)
        annual_last_period = annual_eps[-1][0] if annual_eps else "000000"
        evaluation_basis = f"{annual_last_period[:4]} 사업보고서 결산"
        ttm_eps = None
        ttm_period = None
        if len(quarterly_eps_tuples) >= 4:
            ttm_eps = round(sum(v for _, v in quarterly_eps_tuples[-4:]), 2)
            ttm_period = quarterly_eps_tuples[-1][0]
            if ttm_period > annual_last_period:
                annual_eps_for_a = list(annual_eps) + [(f"TTM_{ttm_period}", ttm_eps)]
                if prelim_is_p and prelim_quarter == ttm_period:
                    evaluation_basis = f"{ttm_period} TTM (잠정실적 포함)"
                else:
                    evaluation_basis = f"{ttm_period} TTM"

        # 6) 분기 YoY history (C JSON 재사용)
        latest_qy = cand["criteria"]["C"].get("yoy_pct")
        eps_yoy_history_raw = cand["criteria"]["C"].get("eps_yoy_history") or []
        quarterly_eps_yoy_history: list[tuple[str, float]] = [
            (str(p), float(v)) for p, v in eps_yoy_history_raw
        ]
        sales_yoy_history_raw = cand["criteria"]["C"].get("sales_yoy_history") or []
        sales_yoy_history: list[tuple[str, float]] = [
            (str(p), float(v)) for p, v in sales_yoy_history_raw
        ]

        # 7) v2 평가
        result = evaluate_a_v2(
            annual_eps=annual_eps_for_a,
            annual_roe=annual_roe,
            quarterly_eps_yoy_history=quarterly_eps_yoy_history,
            sales_yoy_history=sales_yoy_history,
            latest_quarter_yoy=latest_qy,
            induty_code=induty_code,
            quarterly_eps_for_stability=quarterly_eps_for_stability,
            pretax_margin=pretax_margin,
        )

        # 결과 + C 요약 + 시장 메타 합치기
        entry = {
            "code": code,
            "name": name,
            "market": cand["market"],
            "market_cap_eok": cand["market_cap_eok"],
            "current_price": cand["current_price"],
            "evaluation_basis": evaluation_basis,
            "ttm_eps": ttm_eps,
            "ttm_period": ttm_period,
            "criteria_c_summary": {
                "yoy_pct": cand["criteria"]["C"].get("yoy_pct"),
                "latest_quarter": cand["criteria"]["C"].get("latest_quarter"),
                "sales_yoy_pct": cand["criteria"]["C"].get("sales_yoy_pct"),
            },
            **result,
        }
        candidates.append(entry)

        track = result["track"]
        score = result["score"]
        grade = result["grade"]
        margin_lbl = result["margin_label"]
        track_label = result["track_label"]
        if track == "unclassified":
            reason_str = result.get("fail_reasons", [""])[0] if result.get("fail_reasons") else "분류 불가"
            print(f"      [분류 불가] 0점 · {reason_str}")
        else:
            print(
                f"      [{track_label}] {score}점 ({grade}) · "
                f"ROE {result['raw'].get('latest_roe')}% · 마진 {margin_lbl}"
            )

        time.sleep(0.3)

    # 동점 시 수익성 점수 → 종목 코드 사전순 tiebreak
    candidates.sort(
        key=lambda c: (
            -c["score"],
            -c["axis_breakdown"].get("profitability", 0),
            c["code"],
        )
    )

    track_counts = {
        "orthodox": sum(1 for c in candidates if c["track"] == "orthodox"),
        "turnaround_orthodox": sum(
            1 for c in candidates
            if c["track"] == "turnaround" and not c["is_preliminary"]
        ),
        "turnaround_preliminary": sum(
            1 for c in candidates
            if c["track"] == "turnaround" and c["is_preliminary"]
        ),
        "new_listing": sum(1 for c in candidates if c["track"] == "new_listing"),
        "unclassified": sum(1 for c in candidates if c["track"] == "unclassified"),
    }
    unclassified_count = track_counts["unclassified"]

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "schema_version": 2,
        "c_input_count": len(c_passed),
        "track_counts": track_counts,
        "candidates": candidates,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 저장: {OUTPUT}")
    print(f"   C 노출 {len(c_passed)} → 분류 {len(candidates)} (정통 {track_counts['orthodox']} · "
          f"턴어라운드 {track_counts['turnaround_orthodox']} · "
          f"예비 {track_counts['turnaround_preliminary']} · "
          f"신규상장 {track_counts['new_listing']} · "
          f"분류불가 {unclassified_count})")

    if candidates:
        print("\n   점수 상위 10:")
        for c in candidates[:10]:
            print(
                f"     {c['score']:>3}점 [{c['track_label']:<14}] {c['grade']:<3} "
                f"{c['name']:14} ROE {c['raw'].get('latest_roe')}% · 마진 {c['margin_label']}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
