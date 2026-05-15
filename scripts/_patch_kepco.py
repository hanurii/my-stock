"""한국전력(015760)만 재평가해서 can-slim-candidates.json에 머지.

원인: Yahoo 차트 일시 실패로 거래대금 0 처리 → 떨어짐.
fix 후 단일 종목 재평가.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from screen_canslim import (  # noqa: E402
    _load_dotenv,
    collect_raw_data,
    evaluate_with_rs,
    fetch_market_state,
)
from canslim_lib.fetch import load_corp_code_map  # noqa: E402

_load_dotenv()

CAND_PATH = Path("C:/Users/hanul/playground/my-stock/public/data/can-slim-candidates.json")


def main() -> None:
    print("[1] 시장 상태 조회")
    market_state, kospi_closes = fetch_market_state(verbose=False)
    print(f"  M: {market_state['verdict']}")

    print("[2] DART corp_map 로드")
    corp_map = load_corp_code_map()

    print("[3] 한국전력(015760) 단일 평가")
    raw = collect_raw_data("015760", "한국전력", "KOSPI", corp_map)
    if not raw:
        print("  ❌ 수집 실패 — Naver 응답 없음")
        return
    if raw.get("_skipped_small_cap"):
        print(f"  ❌ 시총 미달: {raw['market_cap_eok']:.0f}억")
        return
    if raw.get("_skipped_low_turnover"):
        print(f"  ❌ 거래대금 미달: {raw['turnover_eok']:.1f}억")
        return
    print(f"  ✓ 수집 성공 — 시총 {raw['ig']['market_cap_eok']:,.0f}억, 거래대금 {raw.get('avg_turnover_eok_30d', 0):.1f}억/일")

    print("[4] 기존 candidates 로드 + RS universe 추출")
    cand = json.loads(CAND_PATH.read_text(encoding="utf-8"))
    existing = cand.get("candidates", [])
    universe_returns = [c.get("twelve_m_return", 0.0) for c in existing]
    universe_returns.append(raw["twelve_m_return"])  # 한국전력 자신 포함
    print(f"  기존 candidates: {len(existing)}개")

    print("[5] RS 백분위 + 점수화")
    result = evaluate_with_rs(raw, kospi_closes, market_state["passed"], universe_returns)
    print(f"  점수: {result['score']}, 통과: {result['passed_count']}/7, 등급: {result['grade']}")
    print(f"  C 통과: {result['criteria']['C']['pass']} ({result['criteria']['C']['value']})")

    print("[6] candidates.json 머지")
    by_code = {c["code"]: c for c in existing}
    if "015760" in by_code:
        print("  기존에 있는 015760 갱신")
    else:
        print("  신규 추가")
    by_code["015760"] = result
    new_candidates = sorted(
        by_code.values(),
        key=lambda c: (-c["passed_count"], -c["score"], -c["market_cap_eok"]),
    )
    cand["candidates"] = new_candidates
    cand["evaluated_count"] = len(new_candidates)
    CAND_PATH.write_text(json.dumps(cand, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ 저장 완료 — 총 {len(new_candidates)}개")


if __name__ == "__main__":
    main()
