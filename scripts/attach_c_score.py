#!/usr/bin/env python3
"""기존 can-slim-candidates.json 에 C 4축 점수(c_score)를 사후 부착.

워커 재수집 없이 이미 들어있는 c_detailed 필드만으로 점수를 계산해서 부착한다.
다음 번 정기 스캔(`screen_canslim.py`) 부터는 부착이 자동이라 이 스크립트는 일회성/긴급용.

사용법:
  python scripts/attach_c_score.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib.criteria import compute_c_score  # noqa: E402

CANDIDATES_FILE = ROOT / "public" / "data" / "can-slim-candidates.json"
WATCHLIST_FILE = ROOT / "public" / "data" / "watchlist.json"
MANAGEMENT_QUALITY_FILE = ROOT / "public" / "data" / "management-quality.json"


def load_watchlist_management() -> dict[str, str]:
    """우선순위: management-quality.json (자동 분류) > watchlist.json (사람 라벨)."""
    out: dict[str, str] = {}
    if WATCHLIST_FILE.exists():
        try:
            wl = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
            for s in wl.get("stocks", []):
                code = s.get("code")
                mq = s.get("management_quality")
                if code and mq:
                    out[code] = mq
        except Exception:
            pass
    if MANAGEMENT_QUALITY_FILE.exists():
        try:
            mq_data = json.loads(MANAGEMENT_QUALITY_FILE.read_text(encoding="utf-8"))
            for code, info in mq_data.get("stocks", {}).items():
                q = info.get("quality")
                if q:
                    out[code] = q
        except Exception:
            pass
    return out


def main() -> None:
    if not CANDIDATES_FILE.exists():
        print(f"❌ {CANDIDATES_FILE.relative_to(ROOT)} 없음. 먼저 screen_canslim.py 를 돌리세요.")
        return

    data = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    mgmt_map = load_watchlist_management()
    print(f"📄 candidates: {len(data.get('candidates', []))}종목 · 생성일 {data.get('generated_at')}")
    print(f"👥 watchlist 경영진 매핑: {len(mgmt_map)}종목")

    attached = 0
    no_data = 0
    tier_counts = {"강력": 0, "좋음": 0, "중립": 0, "약함": 0}
    for c in data.get("candidates", []):
        cr = c.get("criteria", {}).get("C", {})
        # c_detailed 필수 필드가 없으면 점수 미부착
        if cr.get("yoy_pct") is None:
            no_data += 1
            continue
        mq = mgmt_map.get(c.get("code"))
        r = compute_c_score(cr, mq)
        c["c_score"] = r["total"]
        c["c_score_tier"] = r["tier"]
        c["c_score_breakdown"] = r["breakdown"]
        c["c_score_notes"] = r["notes"]
        c["management_quality"] = mq
        tier_counts[r["tier"]] += 1
        attached += 1

    print(f"\n✅ 점수 부착: {attached}종목 (YoY 산출 불가로 미부착: {no_data})")
    print(f"   등급 분포: 🅐 강력 {tier_counts['강력']} · 🅑 좋음 {tier_counts['좋음']} · "
          f"🅒 중립 {tier_counts['중립']} · 🅓 약함 {tier_counts['약함']}")

    # 필터 통과(5조건) 종목 중 상위 점수 출력
    def passes_filter(cr: dict) -> bool:
        if cr.get("yoy_pct") is None or cr.get("yoy_pct") < 25:
            return False
        sales_ok = (cr.get("sales_yoy_pct") is not None and cr.get("sales_yoy_pct") >= 25) or cr.get("sales_accel_3q")
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

    passed = [c for c in data.get("candidates", []) if "c_score" in c and passes_filter(c.get("criteria", {}).get("C", {}))]
    passed.sort(key=lambda c: c["c_score"], reverse=True)
    print(f"\n🏆 1단계 필터 통과 종목: {len(passed)}개 · 점수 상위 15")
    for i, c in enumerate(passed[:15]):
        tier = c.get("c_score_tier", "—")
        b = c.get("c_score_breakdown", {})
        cr = c.get("criteria", {}).get("C", {})
        print(
            f"  {i+1:>2}. [{tier:<2}] {c['c_score']:>3}점  {c['name']:<14} ({c['code']}·{c['market']})  "
            f"YoY {cr.get('yoy_pct'):>+6.1f}%  ①{b.get('yoy'):>2}/②{b.get('accel'):>4}/③{b.get('sales'):>2}"
        )

    CANDIDATES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 저장 완료: {CANDIDATES_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
