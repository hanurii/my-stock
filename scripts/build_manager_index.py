#!/usr/bin/env python3
"""한국 시장 운용사 보유 종목 역인덱스 빌더 (CAN SLIM 'I' 페이지 A — 운용사 관점).

목적: 종목별 DART 5%룰 보고자 → 운용사별 보유 종목 매핑으로 뒤집어
"각 운용사가 어떤 한국 종목들을 5%+ 보유하고 있는가" 인덱스 생성.

입력 모집단:
- 워치리스트 (`public/data/watchlist.json` → stocks[])
- L 통과 종목 (`public/data/can-slim-l-candidates.json` → candidates[])
- 중복 제거 후 union

처리:
- 각 종목에 DART majorstock 호출
- 보고자별로 그룹핑 (한국 자산운용사 / 글로벌 운용사 / 연기금)
- 운용사 단위 역인덱스 + 운용사 등급(fund-rankings.json) 조인

출력: `public/data/manager-portfolios.json`

사용법:
    python scripts/build_manager_index.py
    python scripts/build_manager_index.py --limit 20    # 디버그
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from collections import defaultdict
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
    classify_reporter,
    load_fund_rankings,
    lookup_manager_grade,
    normalize_manager_name,
)


WATCHLIST_INPUT = ROOT / "public" / "data" / "watchlist.json"
L_INPUT = ROOT / "public" / "data" / "can-slim-l-candidates.json"
FUND_RANKINGS = ROOT / "public" / "data" / "fund-rankings.json"
OUTPUT = ROOT / "public" / "data" / "manager-portfolios.json"


def build_universe() -> list[dict]:
    """워치리스트 + L 통과 종목 union (code 중복 제거)."""
    universe: dict[str, dict] = {}
    if WATCHLIST_INPUT.exists():
        wl = json.loads(WATCHLIST_INPUT.read_text(encoding="utf-8"))
        for s in wl.get("stocks", []):
            universe[s["code"]] = {"code": s["code"], "name": s["name"], "sector": s.get("sector"), "from_watchlist": True}
    if L_INPUT.exists():
        ld = json.loads(L_INPUT.read_text(encoding="utf-8"))
        for c in ld.get("candidates", []):
            if c["code"] in universe:
                universe[c["code"]]["from_l_pass"] = True
            else:
                universe[c["code"]] = {"code": c["code"], "name": c["name"], "from_l_pass": True}
    return list(universe.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리 종목 상한 (디버그)")
    parser.add_argument("--sleep-ms", type=int, default=150, help="DART 호출 간 sleep (rate limit)")
    args = parser.parse_args()

    universe = build_universe()
    print(f"📊 모집단: {len(universe)} 종목 (워치리스트 + L 통과)")
    if args.limit:
        universe = universe[: args.limit]
        print(f"  → --limit {args.limit} 적용")

    corp_map = load_corp_code_map()
    if not corp_map:
        print("❌ DART corp_map 로드 실패")
        return 1

    fund_rankings = load_fund_rankings(FUND_RANKINGS)
    print(f"💎 운용사 등급 데이터: 1년 {len(fund_rankings['grade_lookup_1y'])}개 / 3년 {len(fund_rankings['grade_lookup_3y'])}개")

    # 운용사 → 보유 종목 역인덱스
    # key = normalize_manager_name(name)
    manager_index: dict[str, dict] = {}

    for idx, stock in enumerate(universe, start=1):
        code = stock["code"]
        name = stock["name"]
        corp_code, parent = resolve_corp_code(code, corp_map)
        if not corp_code:
            print(f"  [{idx}/{len(universe)}] {code} {name}: corp_code 없음, 스킵")
            continue

        items = dart_get("majorstock", {"corp_code": corp_code})
        if items is None:
            print(f"  [{idx}/{len(universe)}] {code} {name}: DART API 실패")
            continue

        # 보고자별 최신 보고
        by_reporter: dict[str, list[dict]] = {}
        for it in items:
            rname = (it.get("repror") or "").strip()
            if not rname:
                continue
            by_reporter.setdefault(rname, []).append(it)

        for reporter_name, filings in by_reporter.items():
            category = classify_reporter(reporter_name)
            if category not in ("korean_am", "global_am", "pension"):
                continue
            filings_sorted = sorted(filings, key=lambda x: x.get("rcept_dt", ""))
            try:
                current_stkrt = float((filings_sorted[-1].get("stkrt") or "0").replace(",", ""))
            except (ValueError, AttributeError):
                current_stkrt = 0.0
            if current_stkrt < 5.0:
                continue  # 현재 5% 이상만 인덱스에 포함

            first_dt = filings_sorted[0].get("rcept_dt", "")
            last_dt = filings_sorted[-1].get("rcept_dt", "")
            try:
                stkrt_irds_recent = float((filings_sorted[-1].get("stkrt_irds") or "0").replace(",", ""))
            except (ValueError, AttributeError):
                stkrt_irds_recent = 0.0

            norm = normalize_manager_name(reporter_name)
            entry = manager_index.setdefault(norm, {
                "manager_name": reporter_name,
                "manager_name_normalized": norm,
                "category": category,
                "holdings": [],
            })
            entry["holdings"].append({
                "code": code,
                "name": name,
                "sector": stock.get("sector"),
                "current_stkrt": current_stkrt,
                "first_rcept_dt": first_dt,
                "last_rcept_dt": last_dt,
                "stkrt_irds_recent": stkrt_irds_recent,
                "filings": len(filings_sorted),
            })

        print(f"  [{idx}/{len(universe)}] {code} {name}: 운용사·연기금 {sum(1 for r in by_reporter if classify_reporter(r) in ('korean_am','global_am','pension'))}건")
        time.sleep(args.sleep_ms / 1000)

    # 운용사별 등급 + 보유 종목 정렬 + 요약
    today = datetime.now().strftime("%Y-%m-%d")
    one_year_ago = (datetime.now().replace(year=datetime.now().year - 1)).strftime("%Y-%m-%d")

    managers_out = []
    for norm, entry in manager_index.items():
        grades = lookup_manager_grade(entry["manager_name"], fund_rankings)
        holdings = entry["holdings"]
        holdings.sort(key=lambda h: -h["current_stkrt"])
        new_entries_1y = [h for h in holdings if h["first_rcept_dt"] >= one_year_ago]
        managers_out.append({
            "manager_name": entry["manager_name"],
            "manager_name_normalized": norm,
            "category": entry["category"],
            "grade_1y": grades["grade_1y"],
            "grade_3y": grades["grade_3y"],
            "total_holdings": len(holdings),
            "new_entries_1y_count": len(new_entries_1y),
            "holdings": holdings,
        })

    # 정렬: 카테고리(한국→글로벌→연기금) → 보유 종목 수 내림차순
    cat_order = {"korean_am": 0, "global_am": 1, "pension": 2}
    managers_out.sort(key=lambda m: (cat_order.get(m["category"], 3), -m["total_holdings"]))

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "universe_size": len(universe),
        "fund_rankings_snapshot": fund_rankings.get("snapshot_date"),
        "manager_count": len(managers_out),
        "managers": managers_out,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 저장: {OUTPUT}")
    print(f"   운용사·연기금: {len(managers_out)}개")
    # 카테고리별 요약
    by_cat = defaultdict(int)
    for m in managers_out:
        by_cat[m["category"]] += 1
    for cat, n in by_cat.items():
        print(f"   - {cat}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
