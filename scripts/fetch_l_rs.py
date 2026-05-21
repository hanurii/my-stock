"""L 원칙 v3 — C 페이지 노출 종목들의 RS(상대강도) 점수 계산.

입력: C 페이지 노출 종목 (`can-slim-candidates.json` 중 `passes_c_gate()` 통과).
       — `src/app/stocks/canslim/lib/cFilter.ts` 의 `passesCGate()` 와 동일 로직.
모집단: KOSPI 시총 상위 300종목.
계산: 52주(1년) 단순 수익률 → 백분위(1~99) RS 점수 = L 점수.
컷오프 없음 (v3): 모든 평가 가능 종목을 점수와 함께 노출.

A 점수: 별도 `can-slim-a-candidates.json` 에서 코드별 lookup (동점 정렬 보조).

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
C_DATA = ROOT / "public" / "data" / "can-slim-candidates.json"
A_DATA = ROOT / "public" / "data" / "can-slim-a-candidates.json"
OUT = ROOT / "public" / "data" / "can-slim-l-candidates.json"
KST = timezone(timedelta(hours=9))

UNIVERSE_SIZE = 300

# C 페이지 노출 게이트 (src/app/stocks/canslim/lib/cFilter.ts 의 passesCGate 포팅).
USER_C_THRESHOLD = 25


def passes_c_gate(cr: dict) -> bool:
    """C 페이지에 실제로 노출되는 종목인지 판정. cFilter.ts:passesCGate 와 동일."""
    yoy = cr.get("yoy_pct")
    if yoy is None or yoy < USER_C_THRESHOLD:
        return False
    sales_yoy = cr.get("sales_yoy_pct")
    sales_accel_3q = cr.get("sales_accel_3q", False)
    sales_accompany = (sales_yoy is not None and sales_yoy >= 25) or sales_accel_3q
    if not sales_accompany:
        return False
    q = cr.get("eps_accel_quality")
    eps_accel_3q = cr.get("eps_accel_3q", False)
    quality_accel = q in ("mild", "strong", "explosive")
    if not (eps_accel_3q or quality_accel):
        return False
    if cr.get("consecutive_decline_quarters", 0) >= 2:
        return False
    if cr.get("severe_decel", False):
        return False
    return True


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
    c_data = json.loads(C_DATA.read_text(encoding="utf-8"))
    c_passed = [c for c in c_data["candidates"] if passes_c_gate(c.get("criteria", {}).get("C", {}))]
    print(f"[0/4] C 페이지 노출 종목 {len(c_passed)}개 로드 (passes_c_gate)", file=sys.stderr)

    a_score_by_code: dict[str, int] = {}
    if A_DATA.exists():
        a_data = json.loads(A_DATA.read_text(encoding="utf-8"))
        for c in a_data.get("candidates", []):
            score = c.get("score")
            if score is not None:
                a_score_by_code[c["code"]] = int(score)
        print(f"  → A 점수 lookup {len(a_score_by_code)}개 로드", file=sys.stderr)

    print(f"[1/4] KOSPI 시총 상위 {UNIVERSE_SIZE}개 모집단 수집…", file=sys.stderr)
    kospi = fetch_stock_list("KOSPI")
    universe = kospi[:UNIVERSE_SIZE]
    universe_codes = {s["code"] for s in universe}
    print(f"  → {len(universe)}개 (전체 KOSPI {len(kospi)}개 중 시총 상위)", file=sys.stderr)

    extra: list[dict] = []
    for c in c_passed:
        if c["code"] not in universe_codes:
            extra.append({"code": c["code"], "name": c["name"], "market": c["market"]})
    if extra:
        print(f"  → C 통과 종목 중 모집단 외 {len(extra)}개 추가 (RS는 보고용 추정)", file=sys.stderr)

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

    print(f"[4/4] C 통과 종목 L 점수 산출…", file=sys.stderr)
    out_candidates: list[dict] = []
    for c in c_passed:
        ret = code_to_ret.get(c["code"])
        rs = code_to_rs.get(c["code"])
        in_univ = c["code"] in universe_codes
        a_score = a_score_by_code.get(c["code"])

        if ret is None or rs is None:
            # 데이터 부족 종목은 RS 0 점으로 처리 (랭킹 합산 시 0점 기여).
            # data_missing_reason 으로 UI 에서 별도 표시 가능.
            out_candidates.append({
                "code": c["code"],
                "name": c["name"],
                "market": c["market"],
                "rs_score": 0,
                "return_1y_pct": None,
                "current_price": c.get("current_price"),
                "a_score": a_score,
                "in_universe": in_univ,
                "data_missing_reason": "Yahoo 차트 데이터 미수집 (일봉 < 200일)",
            })
            continue

        out_candidates.append({
            "code": c["code"],
            "name": c["name"],
            "market": c["market"],
            "rs_score": rs,
            "return_1y_pct": round(ret, 2),
            "current_price": c.get("current_price"),
            "a_score": a_score,
            "in_universe": in_univ,
            "data_missing_reason": None,
        })

    # 정렬: 1차 RS 내림차순, 2차 A 점수 내림차순, 3차 코드 사전순. RS 0 (데이터 없음) 은 자연히 최하단.
    out_candidates.sort(key=lambda c: (
        -(c["rs_score"] or 0),
        -(c["a_score"] or 0),
        c["code"],
    ))

    evaluated = [c for c in out_candidates if c["data_missing_reason"] is None]
    data_missing = [c for c in out_candidates if c["data_missing_reason"] is not None]

    result = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d"),
        "schema_version": "v3",
        "c_input_count": len(c_passed),
        "l_evaluated_count": len(evaluated),
        "data_missing_count": len(data_missing),
        "universe": {
            "type": "KOSPI 시총 상위 300종목",
            "actual_size": n,
            "return_period": "52주 단순 수익률 (1년 전 종가 대비 현재가)",
            "scoring": "백분위 1~99 (컷오프 없음 — RS 가 곧 L 점수)",
        },
        "candidates": out_candidates,
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {OUT.relative_to(ROOT)}", file=sys.stderr)
    print(f"  C 입력 {len(c_passed)}개 → L 평가 {len(evaluated)}개 + 데이터 없음 {len(data_missing)}개", file=sys.stderr)

    top_n = 20
    print(f"\n상위 {top_n}:", file=sys.stderr)
    for c in evaluated[:top_n]:
        rs_str = f"RS {c['rs_score']:>2}"
        ret_str = f"1y {c['return_1y_pct']:+7.2f}%"
        univ = "" if c["in_universe"] else "  (모집단 외)"
        a_str = f"A{c['a_score']:>2}" if c["a_score"] is not None else "A -"
        print(f"  {c['code']} {c['name']:<12}: {rs_str} {a_str} ({ret_str}){univ}", file=sys.stderr)

    if data_missing:
        print(f"\n데이터 없음 ({len(data_missing)}개, RS 0 처리):", file=sys.stderr)
        for c in data_missing:
            print(f"  {c['code']} {c['name']:<12}: {c['data_missing_reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
