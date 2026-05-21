#!/usr/bin/env python3
"""CAN SLIM 'S' 원칙 (Supply and Demand) — v2 점수 체계.

입력: public/data/can-slim-candidates.json (C 통과 종목 전체)
보조 입력:
  - public/data/shareholder-returns.json (DART 주주환원 데이터, 없으면 기본 25점)
출력: public/data/can-slim-s-candidates.json (60점 만점 점수와 함께 전 종목 노출)

점수:
  - 주주가치 50점 (기본 25 + 자사주 소각·연속 배당 가점, 희석 감점)
  - 부채비율 10점 (일반 산업 5단계, 금융업 5점 고정)
  - 총 60점

데이터 수집:
  - 부채비율: DART fnlttMultiAcnt (10종목/호출 bulk)
  - 금융업 판정: 종목명 패턴 (은행/보험/증권/카드/캐피탈 등)

사용법:
  python scripts/screen_canslim_s.py
  python scripts/screen_canslim_s.py --limit 20  # 디버그
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

from canslim_lib.fetch import dart_get, load_corp_code_map, resolve_corp_code  # noqa: E402
from canslim_lib.criteria import passes_c_gate  # noqa: E402
from canslim_lib.criteria_s_v2 import score_s_v2  # noqa: E402

C_INPUT = ROOT / "public" / "data" / "can-slim-candidates.json"
SR_INPUT = ROOT / "public" / "data" / "shareholder-returns.json"
OUTPUT = ROOT / "public" / "data" / "can-slim-s-candidates.json"

DART_MULTI_CHUNK = 10  # fnlttMultiAcnt 한 번에 처리할 corp_code 수
CURRENT_YEAR = datetime.now().year


# ── DART bulk 부채비율 수집 ──

def parse_amount(s: str | None) -> float | None:
    if not s or s in ("-", ""):
        return None
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def fetch_debt_ratios_bulk(corp_codes: list[str], bsns_year: str) -> dict[str, float | None]:
    """fnlttMultiAcnt 로 corp_codes 묶음 부채비율 일괄 조회.

    Returns: {corp_code: debt_ratio_pct or None}.
    debt_ratio = 부채총계 / 자본총계 × 100. CFS 우선, 없으면 OFS.
    """
    out: dict[str, float | None] = {cc: None for cc in corp_codes}
    if not corp_codes:
        return out

    joined = ",".join(corp_codes)
    items = dart_get("fnlttMultiAcnt", {
        "corp_code": joined,
        "bsns_year": bsns_year,
        "reprt_code": "11011",  # 사업보고서
    })
    if not items:
        return out

    # corp_code × (fs_div, account_nm) 으로 amount 매핑
    by_corp: dict[str, dict[tuple[str, str], float]] = {}
    for it in items:
        cc = it.get("corp_code")
        nm = (it.get("account_nm") or "").strip()
        fs = (it.get("fs_div") or "").strip()
        if nm not in ("부채총계", "자본총계"):
            continue
        amt = parse_amount(it.get("thstrm_amount"))
        if cc and amt is not None:
            by_corp.setdefault(cc, {})[(fs, nm)] = amt

    for cc in corp_codes:
        rows = by_corp.get(cc, {})
        # CFS (연결) 우선
        for fs in ("CFS", "OFS"):
            liab = rows.get((fs, "부채총계"))
            equity = rows.get((fs, "자본총계"))
            if liab is not None and equity is not None and equity != 0:
                out[cc] = round(liab / equity * 100, 2)
                break
    return out


def collect_all_debt_ratios(
    candidates: list[dict],
    corp_map: dict[str, str],
) -> dict[str, float | None]:
    """전 종목 부채비율 일괄 수집.

    Strategy:
      1) bsns_year=2024 (가장 최근 확정 사업보고서) 로 bulk 조회
      2) 누락 종목은 bsns_year=2023 으로 재시도
    Returns: {stock_code: debt_ratio_pct or None}.
    """
    print(f"\n📥 DART fnlttMultiAcnt bulk 부채비율 수집 ({len(candidates)}종목)...")

    # stock_code → corp_code 매핑 (우선주 fallback 포함)
    stock_to_corp: dict[str, str] = {}
    no_corp: list[str] = []
    for c in candidates:
        sc = c["code"]
        cc, _ = resolve_corp_code(sc, corp_map)
        if cc:
            stock_to_corp[sc] = cc
        else:
            no_corp.append(sc)

    if no_corp:
        print(f"  ⚠ corp_code 매핑 실패 {len(no_corp)}종목: {', '.join(no_corp[:10])}{'...' if len(no_corp)>10 else ''}")

    corp_to_stocks: dict[str, list[str]] = {}
    for sc, cc in stock_to_corp.items():
        corp_to_stocks.setdefault(cc, []).append(sc)

    corp_codes = list(corp_to_stocks.keys())

    debt_by_corp: dict[str, float | None] = {}

    # Year fallback: 가장 최근 확정 사업보고서부터
    fallback_years = [str(CURRENT_YEAR - 1), str(CURRENT_YEAR - 2)]

    for year in fallback_years:
        # 아직 미수집된 corp_code 만
        pending = [cc for cc in corp_codes if cc not in debt_by_corp or debt_by_corp[cc] is None]
        if not pending:
            break
        print(f"  · bsns_year={year} → {len(pending)}종목 조회 (chunk={DART_MULTI_CHUNK})")
        for i in range(0, len(pending), DART_MULTI_CHUNK):
            chunk = pending[i : i + DART_MULTI_CHUNK]
            res = fetch_debt_ratios_bulk(chunk, year)
            for cc, ratio in res.items():
                if ratio is not None:
                    debt_by_corp[cc] = ratio
                else:
                    debt_by_corp.setdefault(cc, None)
            done = min(i + DART_MULTI_CHUNK, len(pending))
            print(f"    [{done}/{len(pending)}] chunk 완료, 수집={sum(1 for v in debt_by_corp.values() if v is not None)}")
            time.sleep(0.2)  # rate-limit

    # stock_code 기준으로 풀어줌
    out: dict[str, float | None] = {}
    for cc, ratio in debt_by_corp.items():
        for sc in corp_to_stocks.get(cc, []):
            out[sc] = ratio
    # corp_code 없는 종목
    for sc in no_corp:
        out[sc] = None

    collected = sum(1 for v in out.values() if v is not None)
    print(f"  ✓ 부채비율 수집 완료: {collected}/{len(candidates)} ({collected/len(candidates)*100:.1f}%)")
    return out


# ── 분포 출력 ──

def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def print_score_distribution(scored: list[dict]) -> None:
    vals = [s["s_score"] for s in scored]
    if not vals:
        print("  ⚠ 점수 데이터 없음.")
        return
    s = sorted(vals)
    print(f"\n📊 S 점수 분포 ({len(vals)}종목, 60점 만점):")
    print(f"   최소  : {s[0]}")
    print(f"   25분위: {percentile(vals, 25):.1f}")
    print(f"   중앙값: {percentile(vals, 50):.1f}")
    print(f"   75분위: {percentile(vals, 75):.1f}")
    print(f"   90분위: {percentile(vals, 90):.1f}")
    print(f"   최대  : {s[-1]}")
    # 점수대 분포
    bins = [(0,15),(15,25),(25,30),(30,35),(35,40),(40,45),(45,50),(50,55),(55,61)]
    print("   대역  :")
    for lo, hi in bins:
        cnt = sum(1 for v in vals if lo <= v < hi)
        bar = "█" * int(cnt / max(vals) * 30) if vals else ""
        print(f"     [{lo:>2}~{hi-1:>2}] {cnt:>4}  {bar}")


# ── 메인 ──

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리 종목 상한 (디버그)")
    args = parser.parse_args()

    if not C_INPUT.exists():
        print(f"❌ 입력 파일 없음: {C_INPUT}")
        return 1
    c_data = json.loads(C_INPUT.read_text(encoding="utf-8"))
    all_candidates = c_data.get("candidates", [])
    total_in_json = len(all_candidates)

    # C 페이지 노출 기준 (`passesCGate`) 만족 종목만 대상.
    # 캐시된 `criteria.C.pass` 를 신뢰하지 않고 인라인 평가 — frontend cFilter.ts 와
    # 코드/로직이 항상 일치하도록 [doc-logic-sync].
    candidates = [c for c in all_candidates if passes_c_gate(c.get("criteria", {}).get("C", {}))]
    print(f"📊 C 입력: JSON {total_in_json}종목 중 passes_c_gate 통과 {len(candidates)}종목")

    if args.limit:
        candidates = candidates[: args.limit]
        print(f"  → --limit {args.limit} 적용 → {len(candidates)}개 처리")

    # shareholder-returns 로드
    sr_map: dict[str, dict] = {}
    if SR_INPUT.exists():
        sr_data = json.loads(SR_INPUT.read_text(encoding="utf-8"))
        sr_map = {s["code"]: s for s in sr_data.get("stocks", [])}
        print(f"📦 shareholder-returns: {len(sr_map)}종목 로드")
    else:
        print(f"⚠ shareholder-returns.json 없음 → 전 종목 기본 25점")

    # corp_code 매핑
    corp_map = load_corp_code_map()

    # 부채비율 bulk 수집
    debt_map = collect_all_debt_ratios(candidates, corp_map)

    # 점수 계산
    print(f"\n🧮 S 점수 계산...")
    scored: list[dict] = []
    for cand in candidates:
        code = cand["code"]
        name = cand["name"]
        sr_entry = sr_map.get(code)
        debt_ratio = debt_map.get(code)

        s = score_s_v2(
            name=name,
            induty_code=None,  # C JSON에 induty_code 없음 — 이름 패턴 사용
            sr_entry=sr_entry,
            debt_ratio=debt_ratio,
            current_year=CURRENT_YEAR,
        )

        record = {
            "code": code,
            "name": name,
            "market": cand.get("market"),
            "market_cap_eok": cand.get("market_cap_eok"),
            "current_price": cand.get("current_price"),
            "pct_from_52w_high": cand.get("pct_from_52w_high"),
            "c_grade": cand.get("grade"),
            "c_score": cand.get("score"),
            "s_score": s["s_score"],
            "shareholder_score": s["shareholder_score"],
            "debt_score": s["debt_score"],
            "is_financial": s["is_financial"],
            "debt_ratio": s["debt_ratio"],
            "debt_basis": s["debt_basis"],
            "shareholder_metrics": s["shareholder_metrics"],
            "shareholder_details": s["shareholder_details"],
            "badges": s["badges"],
        }
        scored.append(record)

    # 점수 내림차순
    scored.sort(key=lambda x: x["s_score"], reverse=True)

    # 통계
    sr_covered = sum(1 for s in scored if s["shareholder_metrics"]["has_data"])
    debt_covered = sum(1 for s in scored if s["debt_ratio"] is not None)
    financial_cnt = sum(1 for s in scored if s["is_financial"])

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "schema_version": "s-v2",
        "c_universe_count": total_in_json,           # C JSON 의 전체 스캔 universe
        "c_passed_count": len(candidates),           # passes_c_gate 통과 종목 (S 채점 대상)
        "scored_count": len(scored),
        "shareholder_covered": sr_covered,
        "debt_covered": debt_covered,
        "financial_count": financial_cnt,
        "scoring": {
            "shareholder_max": 50,
            "shareholder_base": 25,
            "debt_max": 10,
            "financial_debt_score": 5,
            "total_max": 60,
        },
        "candidates": scored,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 저장: {OUTPUT}")
    print(f"   C 입력 {len(scored)} → 전 종목 채점")
    print(f"   주주환원 데이터 보유: {sr_covered}/{len(scored)} ({sr_covered/len(scored)*100:.1f}%)")
    print(f"   부채비율 데이터 보유: {debt_covered}/{len(scored)} ({debt_covered/len(scored)*100:.1f}%)")
    print(f"   금융업: {financial_cnt}")

    print_score_distribution(scored)

    # 상위 10종목 미리보기
    print(f"\n🏆 S 점수 상위 10종목:")
    for i, s in enumerate(scored[:10], start=1):
        badges = ",".join(s["badges"]) if s["badges"] else "—"
        print(
            f"  {i:>2}. {s['code']} {s['name'][:14]:<14} "
            f"{s['s_score']:>2}점 (주주가치 {s['shareholder_score']:>2} + 부채 {s['debt_score']:>2}) "
            f"부채비율={s['debt_ratio']!s:<7} [{badges}]"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
