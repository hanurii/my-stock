"""트렌드 템플레이트 통과 종목에 CAN SLIM C 원칙 점수 매기기.

입력:  public/data/trend-template-candidates.json (8개 모두 통과 종목)
출력:  public/data/trend-template-c-scored.json

C 점수·등급(강력/좋음/중립/약함) + C 게이트(5조건) 통과 여부 산출.
정렬: C 점수 내림차순.

기존 인프라 재사용:
  scripts/canslim_lib/criteria.py     ─ evaluate_c_detailed, passes_c_gate, compute_c_score
  scripts/screen_canslim.py           ─ collect_raw_data_v2 (DART + Naver + pdata)

사용 예:
  python scripts/screen_trend_template_c_score.py
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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

from canslim_lib import pdata  # noqa: E402
from canslim_lib.fetch import load_corp_code_map  # noqa: E402
from canslim_lib.criteria import (  # noqa: E402
    evaluate_c_detailed,
    passes_c_gate,
    compute_c_score,
)
from screen_canslim import collect_raw_data_v2  # noqa: E402

KST = timezone(timedelta(hours=9))
INPUT_PATH = ROOT / "public" / "data" / "trend-template-candidates.json"
OUTPUT_PATH = ROOT / "public" / "data" / "trend-template-c-scored.json"
MAX_WORKERS = 8


def evaluate_one(stock: dict, pdata_price: dict, pdata_meta: dict,
                 corp_map: dict) -> dict | None:
    """단일 종목 C 데이터 수집 + 점수 산출. None = 데이터 수집 실패."""
    code = stock["code"]
    name = stock["name"]
    market = stock["market"]
    pi = pdata_price.get(code, {})
    mi = pdata_meta.get(code)

    try:
        raw = collect_raw_data_v2(
            code, name, market, pi, mi, corp_map,
            min_price=0, min_market_cap_eok=0, min_turnover_eok=0.0,
            skip_tier2_if_c_ineligible=False,  # 전체 종목 Tier 2 강제 — 점수 정확도 우선
        )
    except Exception as e:
        return {
            "code": code, "name": name, "market": market,
            "ok": False, "reason": f"collect_raw_data_v2 예외: {type(e).__name__}: {e}",
        }

    if not raw or raw.get("_skipped_small_cap") or raw.get("_skipped_low_turnover"):
        return {
            "code": code, "name": name, "market": market,
            "ok": False, "reason": "raw 수집 실패 또는 사전 제외",
        }

    quarter_eps = raw.get("quarter_eps") or []
    quarter_sales = raw.get("quarter_sales") or []

    c_detailed = evaluate_c_detailed(quarter_eps, quarter_sales, dilution_flag=None)

    # 잠정실적 플래그
    pre_period = raw.get("preliminary_period")
    if pre_period and c_detailed.get("latest_quarter") == pre_period:
        c_detailed["latest_is_preliminary"] = True
        c_detailed["preliminary_rcept_no"] = raw.get("preliminary_rcept_no")
    else:
        c_detailed["latest_is_preliminary"] = False
        c_detailed["preliminary_rcept_no"] = None

    c_gate_pass = passes_c_gate(c_detailed)
    c_score = compute_c_score(c_detailed)

    return {
        "code": code, "name": name, "market": market,
        "ok": True,
        "market_cap_eok": stock.get("market_cap_eok"),
        "rs": stock.get("rs"),
        "trend_current_price": stock.get("current_price"),
        "c_gate_pass": c_gate_pass,
        "c_score": c_score["total"],
        "c_score_tier": c_score["tier"],
        "c_score_breakdown": c_score["breakdown"],
        "c_score_notes": c_score["notes"],
        "c_detailed": {
            "yoy_pct": c_detailed.get("yoy_pct"),
            "prev_yoy_pct": c_detailed.get("prev_yoy_pct"),
            "accel_delta_pp": c_detailed.get("accel_delta_pp"),
            "eps_accel_quality": c_detailed.get("eps_accel_quality"),
            "eps_accel_3q": c_detailed.get("eps_accel_3q"),
            "sales_yoy_pct": c_detailed.get("sales_yoy_pct"),
            "sales_accel_3q": c_detailed.get("sales_accel_3q"),
            "never_sell": c_detailed.get("never_sell"),
            "eps_new_high": c_detailed.get("eps_new_high"),
            "consecutive_decline_quarters": c_detailed.get("consecutive_decline_quarters"),
            "severe_decel": c_detailed.get("severe_decel"),
            "latest_quarter": c_detailed.get("latest_quarter"),
            "latest_eps": c_detailed.get("latest_eps"),
            "latest_is_preliminary": c_detailed.get("latest_is_preliminary"),
            "eps_yoy_history": c_detailed.get("eps_yoy_history"),
            "sales_yoy_history": c_detailed.get("sales_yoy_history"),
        },
    }


def main() -> None:
    if not INPUT_PATH.exists():
        print(f"❌ 입력 파일 없음: {INPUT_PATH}")
        print("   먼저 screen_trend_template.py --save 를 실행하세요.")
        sys.exit(1)

    print("📂 트렌드 템플레이트 결과 로드")
    src = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    src_asof = src.get("asof")
    all_pass = [c for c in src["candidates"] if c.get("all_pass")]
    print(f"  8개 통과 종목: {len(all_pass)}")
    print(f"  기준일: {src_asof}")

    if "DART_API_KEY" not in os.environ:
        print("⚠️  DART_API_KEY 환경변수 없음 — 분기 EPS/매출 보강 불가, 점수 정확도 낮아짐.")
    else:
        print(f"🔑 DART 키 로드 OK")

    # ── pdata batch preload ──
    print("\n🏛  공공데이터포털 batch preload")
    basDt = pdata._latest_available_basDt()
    print(f"  최근 영업일: {basDt}")
    pdata_price = pdata.fetch_pdata_price_info(basDt) if basDt else {}
    pdata_meta = pdata.fetch_pdata_item_info(basDt) if basDt else {}
    print(f"  price_info: {len(pdata_price)}, item_info: {len(pdata_meta)}")

    # ── DART corp_code 매핑 ──
    print("\n📦 DART corp_code 매핑 로드")
    corp_map = load_corp_code_map()
    print(f"  매핑된 상장사: {len(corp_map)}")

    # ── 병렬 수집 + 점수 산출 ──
    print(f"\n💎 C 원칙 평가 (병렬 {MAX_WORKERS}워커) 시작")
    start = time.time()
    results: list[dict] = []
    completed = 0

    def task(s):
        return evaluate_one(s, pdata_price, pdata_meta, corp_map)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for r in ex.map(task, all_pass):
            if r is not None:
                results.append(r)
            completed += 1
            if completed % 20 == 0 or completed == len(all_pass):
                ok = sum(1 for x in results if x.get("ok"))
                gate = sum(1 for x in results if x.get("c_gate_pass"))
                print(f"  진행 {completed}/{len(all_pass)} (성공 {ok}, C-게이트 통과 {gate})")

    elapsed = time.time() - start
    print(f"\n  완료 ({elapsed:.1f}s)")

    # ── 정렬: C 점수 내림차순 (게이트 통과 우선 + 점수) ──
    ok_results = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]

    def sort_key(r):
        return (
            0 if r.get("c_gate_pass") else 1,
            -(r.get("c_score") or 0.0),
            -(r.get("market_cap_eok") or 0),
        )
    ok_results.sort(key=sort_key)

    # ── 통계 ──
    tier_counts = {"강력": 0, "좋음": 0, "중립": 0, "약함": 0}
    for r in ok_results:
        t = r.get("c_score_tier")
        if t in tier_counts:
            tier_counts[t] += 1
    gate_pass_count = sum(1 for r in ok_results if r.get("c_gate_pass"))

    # ── 저장 ──
    out = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": src_asof,
        "source": "trend-template-candidates.json (8개 모두 통과 종목)",
        "input_count": len(all_pass),
        "evaluated_count": len(ok_results),
        "failed_count": len(failed),
        "c_gate_pass_count": gate_pass_count,
        "tier_distribution": tier_counts,
        "candidates": ok_results,
        "failed": failed,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 저장: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"\n📊 등급 분포: {tier_counts}")
    print(f"📊 C 게이트(5조건) 통과: {gate_pass_count}/{len(ok_results)}")


if __name__ == "__main__":
    main()
