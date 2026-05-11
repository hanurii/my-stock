"""L 원칙 — S 통과 종목들의 RS(상대강도) 점수 계산.

모집단: KOSPI 시총 상위 300종목.
계산: 52주(1년) 단순 수익률 → 백분위(1~99) RS 점수.
컷오프: RS ≥ 80 통과.

출력: public/data/can-slim-l-candidates.json
"""
import json
import sys
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_stock_list, fetch_yahoo_chart, yahoo_symbol

ROOT = Path(__file__).resolve().parents[1]
S_DATA = ROOT / "public" / "data" / "can-slim-s-candidates.json"
OUT = ROOT / "public" / "data" / "can-slim-l-candidates.json"
KST = timezone(timedelta(hours=9))

UNIVERSE_SIZE = 300
RS_CUTOFF = 80


def fetch_return(stock: dict) -> dict | None:
    code = stock["code"]
    market = stock["market"]
    name = stock["name"]
    symbol = yahoo_symbol(code, market)
    chart = fetch_yahoo_chart(symbol, range_="1y", interval="1d")
    if not chart or len(chart.get("closes", [])) < 200:
        return None
    closes = chart["closes"]
    first = closes[0]
    last = closes[-1]
    if first <= 0:
        return None
    return {
        "code": code,
        "name": name,
        "market": market,
        "return_1y_pct": (last - first) / first * 100,
        "current_price": last,
    }


def main() -> None:
    s_data = json.loads(S_DATA.read_text(encoding="utf-8"))
    s_candidates = s_data["candidates"]

    print(f"[1/4] KOSPI 시총 상위 {UNIVERSE_SIZE}개 모집단 수집…", file=sys.stderr)
    kospi = fetch_stock_list("KOSPI")
    universe = kospi[:UNIVERSE_SIZE]
    universe_codes = {s["code"] for s in universe}
    print(f"  → {len(universe)}개 (전체 KOSPI {len(kospi)}개 중 시총 상위)", file=sys.stderr)

    extra: list[dict] = []
    for c in s_candidates:
        if c["code"] not in universe_codes:
            extra.append({"code": c["code"], "name": c["name"], "market": c["market"]})
    if extra:
        names = ", ".join(f"{e['code']} {e['name']}" for e in extra)
        print(f"  → S 통과 종목 중 모집단 외 {len(extra)}개 추가 (RS는 보고용 추정): {names}", file=sys.stderr)

    fetch_targets = universe + extra

    print(f"[2/4] Yahoo 1y 일봉 수집 (병렬 workers=20)…", file=sys.stderr)
    returns: list[dict] = []
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(fetch_return, s) for s in fetch_targets]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            completed += 1
            if r:
                returns.append(r)
            if completed % 50 == 0:
                print(f"  진행 {completed}/{len(fetch_targets)} (성공 {len(returns)})", file=sys.stderr)
    print(f"  완료: {len(returns)}/{len(fetch_targets)} 성공", file=sys.stderr)

    pop_returns = [r for r in returns if r["code"] in universe_codes]
    sorted_pop = sorted(pop_returns, key=lambda r: r["return_1y_pct"])
    n = len(sorted_pop)
    if n < 2:
        print(f"[ERROR] 모집단 데이터 부족 ({n}개)", file=sys.stderr)
        sys.exit(1)

    print(f"[3/4] RS 백분위 계산 (유효 모집단 {n}개)…", file=sys.stderr)
    code_to_rs: dict[str, int] = {}
    code_to_ret: dict[str, float] = {r["code"]: r["return_1y_pct"] for r in returns}

    for i, r in enumerate(sorted_pop):
        rs = int(round(1 + 98 * i / (n - 1)))
        code_to_rs[r["code"]] = rs

    for r in returns:
        if r["code"] in code_to_rs:
            continue
        target = r["return_1y_pct"]
        lower = sum(1 for pr in sorted_pop if pr["return_1y_pct"] < target)
        rs = int(round(1 + 98 * lower / (n - 1)))
        code_to_rs[r["code"]] = max(1, min(99, rs))

    print(f"[4/4] S 통과 종목 RS 점수 산출…", file=sys.stderr)
    out_candidates: list[dict] = []
    for c in s_candidates:
        ret = code_to_ret.get(c["code"])
        rs = code_to_rs.get(c["code"])
        in_univ = c["code"] in universe_codes
        if ret is None or rs is None:
            out_candidates.append({
                "code": c["code"],
                "name": c["name"],
                "market": c["market"],
                "rs_score": None,
                "return_1y_pct": None,
                "current_price": c.get("current_price"),
                "a_score": c.get("a_score"),
                "in_universe": in_univ,
                "passes_l": False,
                "fail_reasons": ["Yahoo 차트 데이터 미수집"],
            })
            continue
        passes = rs >= RS_CUTOFF
        out_candidates.append({
            "code": c["code"],
            "name": c["name"],
            "market": c["market"],
            "rs_score": rs,
            "return_1y_pct": round(ret, 2),
            "current_price": c.get("current_price"),
            "a_score": c.get("a_score"),
            "in_universe": in_univ,
            "passes_l": passes,
            "fail_reasons": [] if passes else [f"RS {rs} < 컷오프 {RS_CUTOFF}"],
        })

    out_candidates.sort(key=lambda c: (c["rs_score"] is None, -(c["rs_score"] or 0)))

    passed = [c for c in out_candidates if c["passes_l"]]
    excluded = [c for c in out_candidates if not c["passes_l"]]

    result = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d"),
        "s_input_count": len(s_candidates),
        "l_passed_count": len(passed),
        "excluded_count": len(excluded),
        "universe": {
            "type": "KOSPI 시총 상위 300종목",
            "actual_size": n,
            "rs_cutoff": RS_CUTOFF,
            "return_period": "52주 단순 수익률 (1년 전 종가 대비 현재가)",
        },
        "candidates": out_candidates,
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {OUT.relative_to(ROOT)}", file=sys.stderr)
    for c in out_candidates:
        marker = "✅" if c["passes_l"] else "❌"
        rs_str = f"RS {c['rs_score']:>2}" if c["rs_score"] is not None else "RS  -"
        ret_str = f"1y {c['return_1y_pct']:+7.2f}%" if c["return_1y_pct"] is not None else "1y    -    "
        univ = "" if c["in_universe"] else "  (모집단 외)"
        print(f"  {marker} {c['code']} {c['name']:<10}: {rs_str} ({ret_str}){univ}", file=sys.stderr)


if __name__ == "__main__":
    main()
