#!/usr/bin/env python3
"""CAN SLIM 'I' 원칙 (Institutional Sponsorship) 스크리너.

입력: public/data/can-slim-l-candidates.json (L 통과 종목)
출력: public/data/can-slim-i-candidates.json

격리 (feedback_canslim_letter_isolation):
- L 코드/JSON 미수정.
- C/A/N/S/L 평가 결과를 I 평가에 사용하지 않음.

게이트 (오닐: 기관 이탈 종목 제외):
1. 직전 60일 기관 순매매 음수 AND 그 전 60일도 음수 (꾸준한 이탈)
2. 5%룰 1년 누적 지분율 < -2.0%p AND 신규 진입 0건
3. 1년 내 5% 이탈 보고자 2건 이상

데이터 소스:
- DART majorstock (5%룰 보고자 시계열)
- finance.naver.com /item/frgn.nhn (일별 기관 순매매)

사용법:
    python scripts/screen_canslim_i.py
    python scripts/screen_canslim_i.py --limit 3       # 디버그
    python scripts/screen_canslim_i.py --org-pages 12  # 기관 매매 1년치 (기본 3 = 60일)
    python scripts/screen_canslim_i.py --merge         # 기존 JSON 머지
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

from canslim_lib.fetch import load_corp_code_map, resolve_corp_code, dart_get  # noqa: E402
from canslim_lib.criteria_i import (  # noqa: E402
    analyze_majorstock,
    analyze_org_flow,
    evaluate_i,
    fetch_naver_org_flow,
)


L_INPUT = ROOT / "public" / "data" / "can-slim-l-candidates.json"
OUTPUT = ROOT / "public" / "data" / "can-slim-i-candidates.json"


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


def print_distribution(entries: list[dict]) -> None:
    """L 통과 종목의 'I' 시그널 분포 출력 (컷오프 검증용)."""
    actives = [e for e in entries if "i_analysis" in e]
    if not actives:
        return
    print("\n📊 L 통과 종목 'I' 시그널 분포:")
    print("  5%룰 보고자 분포:")
    korean = [r["i_analysis"]["majorstock"]["summary"]["korean_am_count"] for r in actives]
    glob = [r["i_analysis"]["majorstock"]["summary"]["global_am_count"] for r in actives]
    pens = [r["i_analysis"]["majorstock"]["summary"]["pension_count"] for r in actives]
    print(f"    한국 운용사: 평균 {sum(korean)/len(korean):.1f}, 최대 {max(korean)}")
    print(f"    글로벌 운용사: 평균 {sum(glob)/len(glob):.1f}, 최대 {max(glob)}")
    print(f"    연기금: 평균 {sum(pens)/len(pens):.1f}, 최대 {max(pens)}")

    new_inc = [len(r["i_analysis"]["majorstock"]["summary"]["new_or_increasing_1y"]) for r in actives]
    print(f"  종합 신규 시그널(strict+추가매수+재등장): 평균 {sum(new_inc)/len(new_inc):.1f}, 최대 {max(new_inc)}")

    cum60s = [r["i_analysis"]["org_flow"]["cum_60d"] for r in actives]
    print(f"  기관 매매 60일 누적 분포 (주 단위):")
    print(f"    최소: {min(cum60s):+,}")
    print(f"    중앙: {percentile(cum60s, 50):+,.0f}")
    print(f"    최대: {max(cum60s):+,}")
    n_outflow = sum(1 for v in cum60s if v < 0)
    print(f"    음수(이탈): {n_outflow}/{len(actives)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리 종목 상한 (디버그)")
    parser.add_argument("--org-pages", type=int, default=3, help="네이버 기관 매매 페이지 수 (1페이지=~20영업일, 기본 3=~60일)")
    parser.add_argument("--merge", action="store_true", help="기존 JSON 과 머지")
    args = parser.parse_args()

    if not L_INPUT.exists():
        print(f"❌ 입력 없음: {L_INPUT}")
        return 1

    l_data = json.loads(L_INPUT.read_text(encoding="utf-8"))
    candidates = l_data.get("candidates", [])
    print(f"📊 L 통과 종목: {len(candidates)}")

    if args.limit:
        candidates = candidates[: args.limit]
        print(f"  → --limit {args.limit} 적용")

    corp_map = load_corp_code_map()
    if not corp_map:
        print("❌ DART corp_map 로드 실패")
        return 1

    # candidates: 모든 L 통과 종목 (통과/미달 단일 리스트, passes_i 플래그로 구분)
    # UI 에서 passes_i=false 행을 회색 음영 + 사유 표시로 렌더링
    all_entries: list[dict] = []

    for idx, cand in enumerate(candidates, start=1):
        code = cand["code"]
        name = cand["name"]
        corp_code, parent = resolve_corp_code(code, corp_map)
        via = f" (via 보통주 {parent})" if parent else ""
        print(f"\n[{idx}/{len(candidates)}] {code} {name}{via}")

        if not corp_code:
            print("  ⚠ corp_code 매칭 실패, 스킵")
            all_entries.append({
                "code": code, "name": name, "passes_i": False,
                "exclusion_reasons": ["corp_code 매칭 실패"],
                "warning_signals": [],
                "fetch_error": "no_corp_code",
            })
            continue

        # DART majorstock
        items = dart_get("majorstock", {"corp_code": corp_code})
        if items is None:
            print("  ⚠ DART API 실패")
            all_entries.append({
                "code": code, "name": name, "passes_i": False,
                "exclusion_reasons": ["DART API 호출 실패"],
                "warning_signals": [],
                "fetch_error": "dart_failed",
            })
            continue
        majorstock = analyze_majorstock(items)

        # 네이버 기관 매매
        print(f"  · 네이버 기관 매매 {args.org_pages * 20}영업일 수집...")
        org_rows = fetch_naver_org_flow(code, pages=args.org_pages)
        org_flow = analyze_org_flow(org_rows)

        # 평가
        verdict = evaluate_i(majorstock, org_flow)

        s = majorstock["summary"]
        print(f"  📌 5%룰: 한국운용사 {s['korean_am_count']}, 글로벌운용사 {s['global_am_count']}, 연기금 {s['pension_count']}")
        print(f"  📌 종합 신규 시그널: strict {s['strict_new_count']} / 추가매수 {s['recent_buyer_count']} / 재등장 {s['returning_count']} / 이탈 {len(s['exits_1y'])}")
        print(f"  📌 1년 누적 지분 변동: {s['total_stkrt_change_1y_pct']:+.2f}%p")
        print(f"  📌 기관 매매: 60일 {org_flow['cum_60d']:+,}주 / 직전 60일 {org_flow['cum_prev_60d']:+,}주 ({org_flow['trend_qoq']})")
        if verdict["passes_i"]:
            print(f"  ✅ 통과")
        else:
            print(f"  ❌ 제외 (회색 처리): {'; '.join(verdict['exclusion_reasons'])}")
        for w in verdict["warning_signals"]:
            print(f"  ⚠ 경고: {w}")

        entry = {
            "code": code,
            "name": name,
            "corp_code": corp_code,
            "via_parent": parent,
            "passes_i": verdict["passes_i"],
            "exclusion_reasons": verdict["exclusion_reasons"],
            "warning_signals": verdict["warning_signals"],
            "i_analysis": {
                "majorstock": majorstock,
                "org_flow": {
                    **{k: v for k, v in org_flow.items() if k != "daily"},
                    "daily": org_rows,
                },
            },
        }
        all_entries.append(entry)
        time.sleep(0.2)

    passed_count = sum(1 for e in all_entries if e.get("passes_i"))
    excluded_count = len(all_entries) - passed_count

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "l_input_count": len(candidates),
        "passed_count": passed_count,
        "excluded_count": excluded_count,
        # 단일 리스트 — UI 에서 passes_i 플래그로 통과/회색 음영 구분
        "candidates": all_entries,
    }

    if args.merge and OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        new_codes = {e["code"] for e in all_entries}
        merged = all_entries + [c for c in existing.get("candidates", []) if c["code"] not in new_codes]
        output["candidates"] = merged
        output["passed_count"] = sum(1 for e in merged if e.get("passes_i"))
        output["excluded_count"] = len(merged) - output["passed_count"]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 저장: {OUTPUT}")
    print(f"   통과: {passed_count} / 회색 처리(미달): {excluded_count}")
    print_distribution(all_entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
