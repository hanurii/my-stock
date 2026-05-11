"""N 원칙 평가용 — A 점수 80+ 종목의 52주 신고가·현재가·% 계산.

출력: stdout JSON.
사용: python scripts/fetch_n_prices.py
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol

A_DATA = Path(__file__).parent.parent / "public" / "data" / "can-slim-a-candidates.json"
KST = timezone(timedelta(hours=9))

def main() -> None:
    a = json.loads(A_DATA.read_text(encoding="utf-8"))
    scored = [c for c in a.get("scored_candidates", []) if c.get("a_score", 0) >= 80]
    scored.sort(key=lambda c: -c["a_score"])

    out = []
    for c in scored:
        code = c["code"]
        market = c.get("market", "KOSPI")
        symbol = yahoo_symbol(code, market)
        chart = fetch_yahoo_chart(symbol, range_="1y", interval="1d")
        if not chart or not chart["closes"]:
            print(f"  [WARN] {code} {c['name']} — Yahoo 데이터 없음", file=sys.stderr)
            continue

        closes = chart["closes"]
        ts = chart["timestamps"]
        high = max(closes)
        high_idx = closes.index(high)
        high_date = datetime.fromtimestamp(ts[high_idx], tz=KST).strftime("%Y-%m-%d")
        current = closes[-1]
        current_date = datetime.fromtimestamp(ts[-1], tz=KST).strftime("%Y-%m-%d")
        pct = (current - high) / high * 100

        out.append({
            "code": code,
            "name": c["name"],
            "market": market,
            "a_score": c["a_score"],
            "a_score_tier": c.get("a_score_tier"),
            "current_price": round(current, 2),
            "current_date": current_date,
            "high_52w": round(high, 2),
            "high_52w_date": high_date,
            "pct_from_52w_high": round(pct, 2),
            "data_points": len(closes),
        })
        print(f"  {code} {c['name']}: 현재 {current:.0f} / 52w高 {high:.0f} ({high_date}) → {pct:+.2f}%", file=sys.stderr)

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
