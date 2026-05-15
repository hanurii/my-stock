"""N 평가 — 자동 정량 (52w 신고가) 새로 수집 + 기존 수동 commentary 보존.

1. fetch_n_prices.py 로직 인라인 (A 80+ 종목 → Yahoo 52w high)
2. 기존 can-slim-n-candidates.json 의 n_commentary 매핑 추출
3. 머지 후 저장
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
A_DATA = ROOT / "public" / "data" / "can-slim-a-candidates.json"
N_DATA = ROOT / "public" / "data" / "can-slim-n-candidates.json"
KST = timezone(timedelta(hours=9))


def main() -> None:
    a = json.loads(A_DATA.read_text(encoding="utf-8"))
    a80 = [c for c in a.get("scored_candidates", []) if c.get("a_score", 0) >= 80]
    a80.sort(key=lambda c: -c["a_score"])
    print(f"A 80+ 입력: {len(a80)}개", file=sys.stderr)

    # 기존 commentary 추출
    existing = {}
    if N_DATA.exists():
        n_old = json.loads(N_DATA.read_text(encoding="utf-8"))
        for c in n_old.get("candidates", []):
            if c.get("n_commentary"):
                existing[c["code"]] = c["n_commentary"]
    print(f"기존 commentary 보존: {len(existing)}개", file=sys.stderr)

    out = []
    for c in a80:
        code = c["code"]
        market = c.get("market", "KOSPI")
        sym = yahoo_symbol(code, market)
        chart = fetch_yahoo_chart(sym, range_="1y", interval="1d")
        if not chart or not chart["closes"]:
            print(f"  [WARN] {code} {c['name']} — Yahoo 데이터 없음", file=sys.stderr)
            continue

        closes = chart["closes"]
        ts = chart["timestamps"]
        high = max(closes)
        high_idx = closes.index(high)
        high_date = datetime.fromtimestamp(ts[high_idx], tz=KST).strftime("%Y-%m-%d")
        cur = closes[-1]
        cur_date = datetime.fromtimestamp(ts[-1], tz=KST).strftime("%Y-%m-%d")
        pct = (cur - high) / high * 100

        # 기존 코멘트 보존, 없으면 빈 객체 스켈레톤 (UI null guard 회피용 일관 스키마)
        commentary = existing.get(code) or {
            "summary": None,
            "new_product": None,
            "new_management": None,
            "new_high_reason": None,
            "sources": [],
            "researched_at": None,
        }
        entry = {
            "code": code,
            "name": c["name"],
            "market": market,
            "a_score": c["a_score"],
            "a_score_tier": c.get("a_score_tier"),
            "current_price": round(cur, 2),
            "current_date": cur_date,
            "high_52w": round(high, 2),
            "high_52w_date": high_date,
            "pct_from_52w_high": round(pct, 2),
            "data_points": len(closes),
            "n_commentary": commentary,
        }
        out.append(entry)
        commentary_status = "✓ 기존" if entry["n_commentary"] else "✗ 신규(코멘트 필요)"
        print(f"  {code} {c['name']:<20} {cur:>10,.0f} / 52w高 {high:>10,.0f}  {pct:+6.2f}%  [{commentary_status}]", file=sys.stderr)

    # 저장
    out.sort(key=lambda c: c["pct_from_52w_high"], reverse=True)  # 신고가 가까운 순
    n_json = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d"),
        "input_track": "A 충족도 점수 ≥ 80 (정통)",
        "a_input_total": len(a80),
        "n_count": len(out),
        "data_sources": {
            "auto_quantitative": "Yahoo Finance 1y daily (52w high, current price)",
            "manual_qualitative": "Claude — 한국 언론·DART·IR 검색으로 new_product / new_management / new_high_reason 작성",
        },
        "candidates": out,
    }
    N_DATA.write_text(json.dumps(n_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {N_DATA}", file=sys.stderr)
    has_content = lambda nc: nc and any(nc.get(k) for k in ("summary", "new_product", "new_management", "new_high_reason"))
    print(
        f"  자동 정량: {len(out)}개 / 수동 commentary 보존: {sum(1 for o in out if has_content(o['n_commentary']))}개 / 빈 스켈레톤(코멘트 미작성): {sum(1 for o in out if not has_content(o['n_commentary']))}개",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
