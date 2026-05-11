#!/usr/bin/env python3
"""CAN SLIM 'S' 원칙 (Supply and Demand) 스크리너.

입력: public/data/can-slim-n-candidates.json (N 통과 종목)
보강 입력: public/data/can-slim-a-candidates.json (시가총액 등)
출력: public/data/can-slim-s-candidates.json

격리:
- N 코드/JSON 미수정 (read-only 입력).
- C/A/N 평가 결과를 S 평가에 사용하지 않음 (글자 격리).

필터 (사용자 확정):
- 5년 내 주식분할 3회 이상 → 제외.
- 부채비율 > {TBD} → 제외 (--debt-threshold 옵션, 미지정 시 필터 안 함).

라벨 (정보 표시):
- 자사주 10%+ 매입 ("매우 큰 매입").
- 분할 1~2회 ("주식 분할 주의").
- 부채 감소 ({TBD %p} 이상 낮춤, --debt-reduction 옵션).

사용법:
  python scripts/screen_canslim_s.py
  python scripts/screen_canslim_s.py --limit 3        # 디버깅
  python scripts/screen_canslim_s.py --debt-threshold 100 --debt-reduction 20
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

from canslim_lib.fetch import (  # noqa: E402
    fetch_integration,
    load_corp_code_map,
    resolve_corp_code,
)
from canslim_lib.criteria_s import evaluate_s  # noqa: E402


N_INPUT = ROOT / "public" / "data" / "can-slim-n-candidates.json"
A_INPUT = ROOT / "public" / "data" / "can-slim-a-candidates.json"
OUTPUT = ROOT / "public" / "data" / "can-slim-s-candidates.json"


def build_market_cap_lookup() -> dict[str, dict]:
    """A JSON 의 scored_candidates 에서 code → {market_cap_eok, current_price} 매핑."""
    if not A_INPUT.exists():
        return {}
    a_data = json.loads(A_INPUT.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for s in a_data.get("scored_candidates") or []:
        out[s["code"]] = {
            "market_cap_eok": s.get("market_cap_eok"),
            "current_price": s.get("current_price"),
            "market": s.get("market"),
        }
    for c in a_data.get("candidates") or []:
        out.setdefault(c["code"], {
            "market_cap_eok": c.get("market_cap_eok"),
            "current_price": c.get("current_price"),
            "market": c.get("market"),
        })
    return out


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


def print_debt_distribution(candidates: list[dict]) -> None:
    """N 통과 종목 부채비율 분위수 출력 (TBD 컷오프 결정 참고용)."""
    vals = [
        c["criteria"]["S"]["debt_ratio_current"]
        for c in candidates
        if c["criteria"]["S"].get("debt_ratio_current") is not None
    ]
    if not vals:
        print("\n  ⚠ 부채비율 데이터 없음.")
        return
    vals_sorted = sorted(vals)
    print(f"\n📊 N 통과 {len(vals)}종목 부채비율 분포 (총부채/자기자본 × 100):")
    print(f"   최소  : {vals_sorted[0]:.1f}%")
    print(f"   25분위: {percentile(vals, 25):.1f}%")
    print(f"   중앙값: {percentile(vals, 50):.1f}%")
    print(f"   75분위: {percentile(vals, 75):.1f}%")
    print(f"   90분위: {percentile(vals, 90):.1f}%")
    print(f"   최대  : {vals_sorted[-1]:.1f}%")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리 종목 상한 (디버그)")
    parser.add_argument(
        "--debt-threshold",
        type=float,
        default=None,
        help="부채비율 컷오프 (%% 초과 시 제외). 미지정 시 필터 안 함."
    )
    parser.add_argument(
        "--debt-reduction",
        type=float,
        default=None,
        help="부채 감소 라벨 기준 (%%p 이상 감소). 미지정 시 라벨 안 함."
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="기존 JSON과 머지 (덮어쓰기 방지)"
    )
    args = parser.parse_args()

    if not N_INPUT.exists():
        print(f"❌ 입력 파일 없음: {N_INPUT}")
        return 1

    n_data = json.loads(N_INPUT.read_text(encoding="utf-8"))
    n_candidates = n_data.get("candidates", [])
    print(f"📊 N 통과 종목: {len(n_candidates)}")

    if args.limit:
        n_candidates = n_candidates[: args.limit]
        print(f"  → --limit {args.limit} 적용 → {len(n_candidates)}개 처리")

    mc_lookup = build_market_cap_lookup()
    corp_map = load_corp_code_map()

    passed: list[dict] = []
    excluded: list[dict] = []

    for idx, cand in enumerate(n_candidates, start=1):
        code = cand["code"]
        name = cand["name"]
        print(f"  [{idx}/{len(n_candidates)}] {code} {name}")

        mc_info = mc_lookup.get(code, {})
        market_cap_eok = mc_info.get("market_cap_eok") or 0
        current_price = mc_info.get("current_price") or cand.get("current_price") or 0
        market = mc_info.get("market") or cand.get("market") or ""

        # A 에 없으면 Naver 에서 보강
        if market_cap_eok == 0:
            integ = fetch_integration(code)
            if integ:
                market_cap_eok = integ.get("market_cap_eok") or 0
                if not current_price:
                    current_price = integ.get("price") or 0
            time.sleep(0.1)

        corp_code, _ = resolve_corp_code(code, corp_map)

        s_eval = evaluate_s(
            code=code,
            corp_code=corp_code,
            market_cap_eok=market_cap_eok,
            current_price=current_price,
            debt_ratio_threshold=args.debt_threshold,
            debt_reduction_threshold_pp=args.debt_reduction,
        )

        record = {
            "code": code,
            "name": name,
            "market": market,
            "market_cap_eok": market_cap_eok,
            "current_price": current_price,
            "pct_from_52w_high": cand.get("pct_from_52w_high"),
            "criteria": {"S": s_eval},
        }

        if s_eval["pass_s"]:
            passed.append(record)
            labels = []
            if s_eval["buyback_large_label"]:
                labels.append("자사주 매우 큰 매입")
            if s_eval["debt_reduction_annual_label"]:
                labels.append("연간 부채 크게 감소")
            if s_eval["debt_reduction_quarterly_label"]:
                labels.append("분기 부채 크게 감소")
            if s_eval["split_warning_label"]:
                labels.append("주식 분할 주의")
            labels_str = ", ".join(labels) if labels else "—"
            debt_str = (
                f"{s_eval['debt_ratio_current']}%"
                if s_eval["debt_ratio_current"] is not None
                else "?"
            )
            insider_str = (
                f"{s_eval['insider_pct']}%"
                if s_eval["insider_pct"] is not None
                else "?"
            )
            print(f"      ✅ 통과 · 부채 {debt_str} · 경영진 {insider_str} · 라벨: {labels_str}")
        else:
            excluded.append({
                "code": code,
                "name": name,
                "reasons": s_eval["fail_reasons"],
            })
            print(f"      ❌ 제외: {'; '.join(s_eval['fail_reasons'])}")

        time.sleep(0.3)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "n_input_count": len(n_data.get("candidates", [])),
        "s_passed_count": len(passed),
        "excluded_count": len(excluded),
        "cutoffs": {
            "debt_ratio_threshold": args.debt_threshold,
            "debt_reduction_threshold_pp": args.debt_reduction,
            "split_exclude_count": 3,
        },
        "candidates": passed,
        "excluded": excluded,
    }

    # 머지 옵션
    if args.merge and OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        existing_by_code = {c["code"]: c for c in (existing.get("candidates") or [])}
        for p in passed:
            existing_by_code[p["code"]] = p
        output["candidates"] = list(existing_by_code.values())
        output["s_passed_count"] = len(output["candidates"])
        # excluded 도 머지 (코드 기준)
        existing_excluded = {e["code"]: e for e in (existing.get("excluded") or [])}
        for e in excluded:
            existing_excluded[e["code"]] = e
        output["excluded"] = list(existing_excluded.values())
        output["excluded_count"] = len(output["excluded"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 저장: {OUTPUT}")
    print(f"   N 통과 {len(n_candidates)} → S 통과 {len(passed)} / 제외 {len(excluded)}")

    # 부채비율 분포 출력 (TBD 결정용)
    print_debt_distribution(passed + [
        {"criteria": {"S": {"debt_ratio_current": None}}}  # placeholder no-op
        for _ in excluded
    ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
