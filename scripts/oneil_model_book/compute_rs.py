"""1단계 보강 — 상대강도(RS) 점수 (오닐 'L' 핵심 변수).

각 위너의 pivot 시점 수익률을 *같은 날짜·같은 기간* 전 종목 분포와 비교한
백분위(1~99). RS 99 = 상위 1%.

- 충분(252거래일 이상): 정통 52주 RS.
- 신규상장 등 252일 미만: 보유한 거래일(상장 후)만큼의 단축 RS.
  전 종목도 *동일 기간*으로 비교 → 공정. 52주 RS와 rs_basis 로 구분.
- 20거래일 미만: 산출 불가(None) — 추정 금지.

전 종목 5년 종가를 _universe_prices_5y.json 으로 캐시.
산출 후 model_book.json 의 RS 필드를 직접 재반영(전체 재수집 불필요).
"""
import json
import sys
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from canslim_lib.fetch import fetch_stock_list, yahoo_symbol, sleep  # noqa: E402
import cyclecfg  # noqa: E402

KST = timezone(timedelta(hours=9))
DIR = cyclecfg.DIR
PIV = DIR / "pivots.json"
RANGE = "사이클창"  # cyclecfg.yahoo 사용 (앵커-2y ~ 종료)
CACHE = DIR / "_universe_prices.json"
OUT = DIR / "rs.json"
MODEL = DIR / "model_book.json"

WIN_FULL = 252        # 정통 52주 거래일
MIN_SHORT = 20        # 이보다 짧으면 RS 산출 불가 (약 1개월)
MAX_WORKERS = 20
CHOSEN_DD = 0.20


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def build_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    uni = fetch_stock_list("KOSPI") + fetch_stock_list("KOSDAQ")
    print(f"  전 종목 시세 캐시 생성({RANGE}): {len(uni)}종목", file=sys.stderr)
    out: dict[str, dict] = {}

    def fetch(s):
        ch = cyclecfg.yahoo(yahoo_symbol(s["code"], s["market"]))
        sleep(60)
        if not ch or not ch.get("closes"):
            return s["code"], None
        return s["code"], {"d": [iso(t) for t in ch["timestamps"]], "c": ch["closes"]}

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for code, data in ex.map(fetch, uni):
            if data:
                out[code] = data
            done += 1
            if done % 200 == 0:
                print(f"  진행 {done}/{len(uni)}", file=sys.stderr)
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def _idx_at(series: dict, date_str: str) -> int | None:
    d = series.get("d") or []
    for i in range(len(d) - 1, -1, -1):
        if d[i] <= date_str:
            return i
    return None


def _ret_over(series: dict, idx: int, win: int) -> float | None:
    c = series["c"]
    if idx is None or idx < win:
        return None
    base = c[idx - win]
    if not base or base <= 0 or c[idx] is None:
        return None
    return c[idx] / base - 1.0


def main():
    cache = build_cache()
    pivots = json.loads(PIV.read_text(encoding="utf-8"))["pivots"]

    results = []
    for r in pivots:
        if r.get("error"):
            results.append({"code": r["code"], "name": r["name"], "rs": None,
                            "rs_note": "pivot 오류"})
            continue
        v = next(x for x in r["variants"] if abs(x["drawdown"] - CHOSEN_DD) < 1e-6)
        pd = v["pivot_date"]
        wser = cache.get(r["code"])
        wi = _idx_at(wser, pd) if wser else None

        if wi is None or wi < MIN_SHORT:
            results.append({"code": r["code"], "name": r["name"], "pivot_date": pd,
                            "rs": None,
                            "rs_note": f"산출불가(pivot 직전 거래일 {wi or 0}<{MIN_SHORT})"})
            continue

        if wi >= WIN_FULL:
            win = WIN_FULL
            basis = "52주(252거래일)"
        else:
            win = wi  # 상장 후/캐시 보유분 전부
            basis = f"단축 {win}거래일(상장후·52주 미만)"

        wp = _ret_over(wser, wi, win)
        if wp is None:
            results.append({"code": r["code"], "name": r["name"], "pivot_date": pd,
                            "rs": None, "rs_note": "기준가 결측"})
            continue

        # 전 종목 동일 기간(win) 동일 종료일(pd) 수익률 분포
        uni = []
        for ser in cache.values():
            j = _idx_at(ser, pd)
            if j is not None and j >= win:
                p = _ret_over(ser, j, win)
                if p is not None:
                    uni.append(p)
        if len(uni) < 100:
            results.append({"code": r["code"], "name": r["name"], "pivot_date": pd,
                            "rs": None, "rs_note": "비교 표본<100",
                            "rs_universe_n": len(uni)})
            continue
        below = sum(1 for x in uni if x < wp)
        rs = max(1, min(99, round(below / len(uni) * 100)))
        results.append({
            "code": r["code"], "name": r["name"], "pivot_date": pd,
            "rs": rs,
            "winner_52w_return_pct": round(wp * 100, 1),
            "rs_window_days": win,
            "rs_basis": basis,
            "rs_universe_n": len(uni),
            "rs_src": f"전종목 {basis} 수익률 백분위",
        })

    DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "definition": "pivot일 직전 동일기간 수익률의 전종목 백분위(1~99). "
                       "252일 미만은 보유기간 단축 RS(전종목도 동일기간 비교).",
        "cache_range": RANGE,
        "rows": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    full = sum(1 for x in results if x.get("rs") is not None and x.get("rs_window_days") == WIN_FULL)
    shortn = sum(1 for x in results if x.get("rs") is not None and (x.get("rs_window_days") or 0) < WIN_FULL)
    none_n = sum(1 for x in results if x.get("rs") is None)
    print(f"RS: 52주 {full} / 단축 {shortn} / 불가 {none_n} (총 {len(results)})", file=sys.stderr)

    # model_book.json 직접 재반영 (전체 재수집 없이 RS만 갱신)
    if MODEL.exists():
        mb = json.loads(MODEL.read_text(encoding="utf-8"))
        rsm = {x["code"]: x for x in results}
        for row in mb.get("rows", []):
            x = rsm.get(row.get("code"))
            if not x:
                continue
            row["rs_score"] = x.get("rs")
            row["rs_52w_return_pct"] = x.get("winner_52w_return_pct")
            row["rs_window_days"] = x.get("rs_window_days")
            row["rs_basis"] = x.get("rs_basis")
            row["rs_src"] = x.get("rs_src") or x.get("rs_note")
        MODEL.write_text(json.dumps(mb, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"model_book.json RS 재반영 완료 ({len(mb.get('rows', []))}행)", file=sys.stderr)


if __name__ == "__main__":
    main()
