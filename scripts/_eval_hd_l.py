"""특정 종목의 L 원칙 단독 평가 (cascading 필터와 별개).

S 미통과 등으로 can-slim-l-candidates.json 에 없는 종목 RS 점수를 알고 싶을 때 사용.
사용법: python3 _eval_hd_l.py [code] [name] [market]
       (인자 생략 시 HD현대중공업 기본값)
"""
import sys
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_stock_list, fetch_yahoo_chart, yahoo_symbol

TARGET_CODE = sys.argv[1] if len(sys.argv) > 1 else "329180"
TARGET_NAME = sys.argv[2] if len(sys.argv) > 2 else "HD현대중공업"
TARGET_MARKET = sys.argv[3] if len(sys.argv) > 3 else "KOSPI"
UNIVERSE_SIZE = 300
RS_CUTOFF = 80


def fetch_return(stock: dict) -> dict | None:
    code = stock["code"]
    market = stock["market"]
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
        "name": stock["name"],
        "return_1y_pct": (last - first) / first * 100,
        "current_price": last,
    }


def main() -> None:
    print(f"[1/3] KOSPI 시총 상위 {UNIVERSE_SIZE}개 모집단 수집…", file=sys.stderr)
    kospi = fetch_stock_list("KOSPI")
    universe = kospi[:UNIVERSE_SIZE]
    print(f"  → {len(universe)}개", file=sys.stderr)

    in_univ = any(s["code"] == TARGET_CODE for s in universe)
    targets = list(universe)
    if not in_univ:
        targets.append({"code": TARGET_CODE, "name": TARGET_NAME, "market": TARGET_MARKET})

    print(f"[2/3] Yahoo 1y 일봉 수집 (workers=20)…", file=sys.stderr)
    returns: list[dict] = []
    universe_codes = {s["code"] for s in universe}
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(fetch_return, s) for s in targets]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            completed += 1
            if r:
                returns.append(r)
            if completed % 50 == 0:
                print(f"  진행 {completed}/{len(targets)} (성공 {len(returns)})", file=sys.stderr)
    print(f"  완료: 성공 {len(returns)}/{len(targets)}", file=sys.stderr)

    pop = [r for r in returns if r["code"] in universe_codes]
    pop_sorted = sorted(pop, key=lambda r: r["return_1y_pct"])
    n = len(pop_sorted)
    if n < 2:
        print(f"[ERROR] 모집단 부족 ({n})", file=sys.stderr)
        sys.exit(1)

    print(f"[3/3] RS 백분위 산출 (유효 모집단 {n}개)…", file=sys.stderr)
    target = next((r for r in returns if r["code"] == TARGET_CODE), None)
    if not target:
        print(f"[ERROR] {TARGET_CODE} 수익률 수집 실패", file=sys.stderr)
        sys.exit(1)

    t_ret = target["return_1y_pct"]
    if target["code"] in universe_codes:
        idx = next(i for i, r in enumerate(pop_sorted) if r["code"] == TARGET_CODE)
        rs = int(round(1 + 98 * idx / (n - 1)))
    else:
        lower = sum(1 for pr in pop_sorted if pr["return_1y_pct"] < t_ret)
        rs = int(round(1 + 98 * lower / (n - 1)))
    rs = max(1, min(99, rs))

    passes = rs >= RS_CUTOFF
    rank_above = sum(1 for r in pop_sorted if r["return_1y_pct"] > t_ret)
    pop_min = pop_sorted[0]["return_1y_pct"]
    pop_max = pop_sorted[-1]["return_1y_pct"]
    pop_median = pop_sorted[n // 2]["return_1y_pct"]

    print("")
    print("=" * 60)
    print(f"  {TARGET_NAME} ({TARGET_CODE}) — L 원칙 단독 평가")
    print("=" * 60)
    print(f"  현재가:        {target['current_price']:,.0f}")
    print(f"  1년 수익률:    {t_ret:+.2f}%")
    print(f"  모집단 내 순위: {rank_above + 1} / {n} (상위 {(rank_above + 1) / n * 100:.1f}%)")
    print(f"  RS 점수:       {rs}")
    print(f"  L 판정:        {'✅ 통과 (RS ≥ 80)' if passes else f'❌ 미달 (RS {rs} < 80)'}")
    print(f"  모집단 외 보강 종목 여부: {'예 (KOSPI 시총 상위 300 외)' if not in_univ else '아니오'}")
    print("")
    print(f"  모집단(KOSPI 300, 유효 {n}개) 1년 수익률 분포")
    print(f"    최저: {pop_min:+.2f}%")
    print(f"    중간: {pop_median:+.2f}%")
    print(f"    최고: {pop_max:+.2f}%")
    print("")
    print(f"  ※ S 원칙 미통과(부채비율 180.07% > 130%)로 페이지에는 노출되지 않음.")
    print(f"     본 결과는 L 원칙 단독 점수 (cascading 필터와 별개).")


if __name__ == "__main__":
    main()
