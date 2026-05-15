"""C 원칙 통과 종목 시총 + 일평균 거래대금 분석.

새 컷오프 후보(시총 ≥ 2,000억 + 일평균 거래대금 ≥ 30억) 대비 통과율 평가.
거래대금 = 야후 30일 일봉의 close×volume 평균.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_yahoo_chart, sleep, yahoo_symbol  # noqa: E402

CANDIDATES_PATH = Path("C:/Users/hanul/playground/my-stock/public/data/can-slim-candidates.json")

NEW_MARKET_CAP_MIN_EOK = 2000  # 2000억원
NEW_TURNOVER_MIN_EOK = 30      # 일평균 거래대금 30억원


def avg_daily_turnover_eok(code: str, market: str) -> float | None:
    """30일 일평균 거래대금(억원). close × volume 의 30일 평균."""
    sym = yahoo_symbol(code, market)
    chart = fetch_yahoo_chart(sym, range_="1mo", interval="1d")
    if not chart:
        return None
    closes = chart["closes"]
    vols = chart["volumes"]
    if len(closes) < 5:
        return None
    n = min(len(closes), 30)
    turnovers = [closes[i] * vols[i] for i in range(-n, 0)]
    avg = sum(turnovers) / len(turnovers)
    return avg / 1e8  # 원 → 억원


def main() -> None:
    d = json.load(CANDIDATES_PATH.open(encoding="utf-8"))
    print(f"파일: {CANDIDATES_PATH.name}")
    print(f"생성일: {d.get('generated_at')}, 스캔: {d.get('scanned_count')}, 평가: {d.get('evaluated_count')}")
    print(f"기존 min_price 컷오프: {d['scan_meta']['min_price']:,}원, 미달 제외: {d['scan_meta']['skipped_low_price_count']}종목")
    print()

    c_pass = [c for c in d["candidates"] if c.get("criteria", {}).get("C", {}).get("pass")]
    print(f"=== C 원칙 통과 종목: {len(c_pass)}개 ===\n")

    # 거래대금 수집
    rows = []
    for i, c in enumerate(c_pass):
        code = c["code"]
        name = c["name"]
        market = c["market"]
        cap = c["market_cap_eok"]
        price = c["current_price"]
        turnover = avg_daily_turnover_eok(code, market)
        rows.append({"code": code, "name": name, "market": market, "cap_eok": cap, "price": price, "turnover_eok": turnover})
        print(f"  [{i+1}/{len(c_pass)}] {code} {name} 시총 {cap:,.0f}억 거래대금 {turnover if turnover else 'N/A'}", flush=True)
        sleep(150)

    # 거래대금 수집 실패 = N/A로 표시
    valid = [r for r in rows if r["turnover_eok"] is not None]
    print(f"\n거래대금 수집 성공: {len(valid)}/{len(rows)}\n")

    # 시총 분포
    caps = sorted(r["cap_eok"] for r in rows)
    n = len(caps)
    print("[시총 분포] (단위: 억원)")
    print(f"  최소: {caps[0]:,.0f}")
    print(f"  25%: {caps[n//4]:,.0f}")
    print(f"  중앙: {caps[n//2]:,.0f}")
    print(f"  75%: {caps[(3*n)//4]:,.0f}")
    print(f"  최대: {caps[-1]:,.0f}")
    print(f"  평균: {sum(caps)/n:,.0f}")
    print()

    # 거래대금 분포
    tos = sorted(r["turnover_eok"] for r in valid)
    if tos:
        n2 = len(tos)
        print("[일평균 거래대금 분포 (30일)] (단위: 억원)")
        print(f"  최소: {tos[0]:,.1f}")
        print(f"  25%: {tos[n2//4]:,.1f}")
        print(f"  중앙: {tos[n2//2]:,.1f}")
        print(f"  75%: {tos[(3*n2)//4]:,.1f}")
        print(f"  최대: {tos[-1]:,.1f}")
        print(f"  평균: {sum(tos)/n2:,.1f}")
        print()

    # 신규 컷오프 적용
    pass_cap = [r for r in valid if r["cap_eok"] >= NEW_MARKET_CAP_MIN_EOK]
    pass_to = [r for r in valid if r["turnover_eok"] >= NEW_TURNOVER_MIN_EOK]
    pass_both = [r for r in valid if r["cap_eok"] >= NEW_MARKET_CAP_MIN_EOK and r["turnover_eok"] >= NEW_TURNOVER_MIN_EOK]
    print(f"[신규 컷오프 적용 = 시총 ≥ {NEW_MARKET_CAP_MIN_EOK:,}억 AND 일평균 거래대금 ≥ {NEW_TURNOVER_MIN_EOK}억]")
    print(f"  시총만 통과: {len(pass_cap)}/{len(valid)}")
    print(f"  거래대금만 통과: {len(pass_to)}/{len(valid)}")
    print(f"  둘 다 통과: {len(pass_both)}/{len(valid)}")
    print()

    print("[전체 종목 표] (시총 큰 순)")
    print(f"  {'코드':<8}{'종목명':<20}{'시총(억)':>12}{'주가(원)':>12}{'거래대금(억/일)':>18}{'신규 컷오프':>14}")
    sorted_rows = sorted(valid, key=lambda r: -r["cap_eok"])
    for r in sorted_rows:
        cap_ok = r["cap_eok"] >= NEW_MARKET_CAP_MIN_EOK
        to_ok = r["turnover_eok"] >= NEW_TURNOVER_MIN_EOK
        if cap_ok and to_ok:
            verdict = "✓ 통과"
        elif not cap_ok and not to_ok:
            verdict = "✗ 둘다탈"
        elif not cap_ok:
            verdict = "△ 시총↓"
        else:
            verdict = "△ 거대↓"
        print(f"  {r['code']:<8}{r['name']:<20}{r['cap_eok']:>12,.0f}{r['price']:>12,}{r['turnover_eok']:>17,.1f}{verdict:>14}")

    # JSON으로 저장
    out_path = Path("C:/Users/hanul/playground/my-stock/.cache/c_universe_stats.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "c_pass_count": len(c_pass),
        "rows": rows,
        "new_thresholds": {"cap_min_eok": NEW_MARKET_CAP_MIN_EOK, "turnover_min_eok": NEW_TURNOVER_MIN_EOK},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out_path}")


if __name__ == "__main__":
    main()
