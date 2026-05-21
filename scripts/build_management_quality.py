#!/usr/bin/env python3
"""경영진 품질 자동 분류 — 1단계 필터 통과 종목 대상.

명세: research/oneil-model-book/MANAGEMENT_AUTO_CLASSIFY.md

흐름:
  1) 기존 can-slim-candidates.json 에서 1단계 필터 통과 종목 추출
  2) 각 종목별 DART 공시 5년치 수집 → 시그널 매칭 → 분류
  3) public/data/management-quality.json 저장

캐싱: .cache/management_signals/<corp_code>.json (TTL 30일).
사용법:
  python scripts/build_management_quality.py
  python scripts/build_management_quality.py --force      # 캐시 무시
  python scripts/build_management_quality.py --limit 10   # 디버그
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

from canslim_lib.fetch import load_corp_code_map, resolve_corp_code  # noqa: E402
from canslim_lib.management import classify_management, fetch_management_signals  # noqa: E402

CANDIDATES_FILE = ROOT / "public" / "data" / "can-slim-candidates.json"
OUTPUT_FILE = ROOT / "public" / "data" / "management-quality.json"
CACHE_DIR = ROOT / ".cache" / "management_signals"
CACHE_TTL_DAYS = 30


def passes_filter(cr: dict) -> bool:
    """C 페이지 1단계 필터(5조건). cFilter.ts:passesCGate 와 동일 룰."""
    if cr.get("yoy_pct") is None or cr["yoy_pct"] < 25:
        return False
    sales_ok = (cr.get("sales_yoy_pct") is not None and cr["sales_yoy_pct"] >= 25) or cr.get("sales_accel_3q")
    if not sales_ok:
        return False
    q = cr.get("eps_accel_quality")
    if q not in ("mild", "strong", "explosive") and not cr.get("eps_accel_3q"):
        return False
    if cr.get("consecutive_decline_quarters", 0) >= 2:
        return False
    if cr.get("severe_decel"):
        return False
    return True


def cache_path(corp_code: str) -> Path:
    return CACHE_DIR / f"{corp_code}.json"


def load_cached_signals(corp_code: str, force: bool = False) -> dict | None:
    if force:
        return None
    p = cache_path(corp_code)
    if not p.exists():
        return None
    age_days = (time.time() - p.stat().st_mtime) / 86400
    if age_days > CACHE_TTL_DAYS:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_cached_signals(corp_code: str, signals: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(corp_code).write_text(json.dumps(signals, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="시그널 캐시 무시하고 새로 수집")
    parser.add_argument("--limit", type=int, default=0, help="디버그용 — 처음 N종목만 처리")
    args = parser.parse_args()

    if not CANDIDATES_FILE.exists():
        print(f"❌ {CANDIDATES_FILE.relative_to(ROOT)} 없음. 먼저 screen_canslim.py 실행 필요.")
        return

    data = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    print(f"📄 평가 종목: {len(cands)}")

    targets = [c for c in cands if passes_filter(c.get("criteria", {}).get("C", {}))]
    print(f"🎯 1단계 필터 통과: {len(targets)}종목")

    if args.limit:
        targets = targets[: args.limit]
        print(f"   → 디버그: 처음 {args.limit}종목만")

    print("\n📦 DART corp_code 매핑 로드...")
    corp_map = load_corp_code_map()
    if not corp_map:
        print("❌ corp_code 매핑 실패 (DART_API_KEY 확인 필요)")
        return
    print(f"   {len(corp_map)}개 매핑")

    print(f"\n🔬 시그널 수집 (캐시 TTL {CACHE_TTL_DAYS}일, force={args.force})")
    results: dict[str, dict] = {}
    quality_counts = {"excellent": 0, "professional": 0, "poor": 0}
    fail_count = 0
    cache_hit = 0
    start = time.time()

    for i, c in enumerate(targets):
        code = c["code"]
        name = c["name"]
        corp_code, _ = resolve_corp_code(code, corp_map)
        if not corp_code:
            fail_count += 1
            continue

        cached = load_cached_signals(corp_code, force=args.force)
        if cached:
            signals = cached
            cache_hit += 1
        else:
            try:
                signals = fetch_management_signals(corp_code, years=5)
                save_cached_signals(corp_code, signals)
            except Exception as e:
                print(f"  ⚠️  {code} {name}: {e}")
                fail_count += 1
                continue

        classified = classify_management(signals)
        results[code] = {
            "name": name,
            "corp_code": corp_code,
            "quality": classified["quality"],
            "total_score": classified["total_score"],
            "score_breakdown": classified["score_breakdown"],
            "signals": classified["signals"],
            "evidence": classified["evidence"],
        }
        quality_counts[classified["quality"]] += 1

        if (i + 1) % 25 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(targets) - i - 1) / rate if rate > 0 else 0
            print(f"  ... {i + 1}/{len(targets)} 처리 ({rate:.1f}/s, ETA {eta:.0f}초, cache hit {cache_hit})")

    print(f"\n✅ 완료: {len(results)}종목 (실패 {fail_count}, cache hit {cache_hit})")
    print(f"   분포: 우수 {quality_counts['excellent']} · 전문 {quality_counts['professional']} · 저조 {quality_counts['poor']}")

    out = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "rule_version": "v1",
        "rule_doc": "research/oneil-model-book/MANAGEMENT_AUTO_CLASSIFY.md",
        "target_universe": "C 페이지 1단계 필터 통과 종목",
        "target_count": len(targets),
        "classified_count": len(results),
        "quality_distribution": quality_counts,
        "stocks": results,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 저장 완료: {OUTPUT_FILE.relative_to(ROOT)}")

    # 상위·하위 샘플 출력
    sorted_results = sorted(results.items(), key=lambda kv: kv[1]["total_score"], reverse=True)
    print("\n🏆 점수 상위 10")
    for code, info in sorted_results[:10]:
        s = info["signals"]
        print(f"  [{info['quality']:<12}] {info['total_score']:>+5.1f}  {info['name']:<14} ({code})  "
              f"소각{s['buyback_cancel_count']}/매입{s['buyback_acquire_count']}/증자{s['rights_issue_count']}/CB{s['cb_bw_count']}/CEO{s['ceo_change_count']}/감사{s['audit_issue_count']}")

    print("\n📉 점수 하위 10")
    for code, info in sorted_results[-10:]:
        s = info["signals"]
        print(f"  [{info['quality']:<12}] {info['total_score']:>+5.1f}  {info['name']:<14} ({code})  "
              f"소각{s['buyback_cancel_count']}/매입{s['buyback_acquire_count']}/증자{s['rights_issue_count']}/CB{s['cb_bw_count']}/CEO{s['ceo_change_count']}/감사{s['audit_issue_count']}")


if __name__ == "__main__":
    main()
