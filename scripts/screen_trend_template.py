"""Minervini 트렌드 템플레이트 스크리너 (KOSPI + KOSDAQ 전 종목).

8가지 조건은 research/oneil-model-book/trend_template.md 참고.
평가 부품은 scripts/canslim_lib/trend_template.py.

사용 예:
  # 단일 종목 디버그
  python scripts/screen_trend_template.py --ticker 005930

  # 시총 상위 50개 시범 (빠른 확인용)
  python scripts/screen_trend_template.py --limit 50 --save

  # 전체 시장 풀스캔 + JSON 저장
  python scripts/screen_trend_template.py --save

  # 과거 시점 (룩어헤드 방지) 기준
  python scripts/screen_trend_template.py --asof 2026-05-15 --save

  # RS 합격선 강화 (Minervini 실전 80+)
  python scripts/screen_trend_template.py --rs-min 80 --save
"""

from __future__ import annotations

import argparse
import bisect
import concurrent.futures
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows cp949 콘솔에서 한글/이모지 안전 출력
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib.fetch import (  # noqa: E402
    fetch_yahoo_chart,
    yahoo_symbol,
)
from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402
from canslim_lib.criteria import evaluate_m  # noqa: E402
from canslim_lib.trend_template import (  # noqa: E402
    evaluate_trend_template,
    TT_RS_MIN_DEFAULT,
    TT_LOW_MIN_PCT,
    TT_HIGH_MAX_PCT,
    TT_SMA200_RISING_LOOKBACK_DAYS,
    TT_SMA200_RISING_PREFERRED_DAYS,
    WINDOW_52W,
    SMA_WINDOW_200,
)

KST = timezone(timedelta(hours=9))
OUTPUT_PATH = ROOT / "public" / "data" / "trend-template-candidates.json"

NAVER_DAYS_BACK = 480       # ~320 거래일 → 200MA + 110 lookback 여유
YAHOO_RANGE_FALLBACK = "2y"
MAX_WORKERS = 12
MIN_CLOSES_FOR_TT = SMA_WINDOW_200   # 200일 미만이면 평가 불가
MIN_RS_COMPARISON_POOL = 100         # RS 표본 < 100 이면 RS = None


# ──────────────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────────────

def _fetch_closes(code: str, market: str) -> tuple[list[float], list[str]] | None:
    """배치 OHLCV 행렬 우선, 부족 시 야후 폴백. (closes, dates) 반환."""
    mtx = ohlcv_matrix.get_series(code, days_back=NAVER_DAYS_BACK)
    if mtx and len(mtx.get("closes") or []) >= MIN_CLOSES_FOR_TT:
        return mtx["closes"], mtx["dates"]

    sym = yahoo_symbol(code, market)
    yh = fetch_yahoo_chart(sym, YAHOO_RANGE_FALLBACK, "1d")
    if yh and len(yh.get("closes") or []) >= MIN_CLOSES_FOR_TT:
        dates = [
            datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d")
            for t in yh["timestamps"]
        ]
        return yh["closes"], dates

    # 둘 다 부족 — 그래도 가용한 만큼 반환 (orchestrator 가 데이터 부족으로 fail 처리)
    if mtx and mtx.get("closes"):
        return mtx["closes"], mtx["dates"]
    if yh and yh.get("closes"):
        dates = [
            datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d")
            for t in yh["timestamps"]
        ]
        return yh["closes"], dates
    return None


def _truncate_to_asof(closes: list[float], dates: list[str], asof: str | None) -> tuple[list[float], list[str]]:
    """asof 날짜 이후 데이터 제거. asof 가 None 이면 그대로."""
    if not asof:
        return closes, dates
    # dates 는 오름차순. asof 보다 큰 것 제거.
    idx = bisect.bisect_right(dates, asof)
    return closes[:idx], dates[:idx]


def _collect_one(stock: dict, asof: str | None) -> dict:
    """단일 종목 데이터 수집 + 조건 1-7 사전 계산 가능한 raw 정보 반환.

    return_252d_pct, win_for_rs (RS 윈도우 길이) 도 함께 저장 → Pass2 RS 계산에서 사용.
    """
    code = stock["code"]
    market = stock["market"]
    fetched = _fetch_closes(code, market)
    if not fetched:
        return {
            "code": code, "name": stock["name"], "market": market,
            "market_cap_eok": stock["market_cap_eok"],
            "ok": False, "reason": "차트 수집 실패 (네이버·야후 모두 실패)",
            "closes": None, "dates": None,
        }

    closes, dates = fetched
    closes, dates = _truncate_to_asof(closes, dates, asof)

    if len(closes) < MIN_CLOSES_FOR_TT:
        return {
            "code": code, "name": stock["name"], "market": market,
            "market_cap_eok": stock["market_cap_eok"],
            "ok": False, "reason": f"데이터 부족 (보유 일수 {len(closes)} < 200)",
            "closes": closes, "dates": dates,
        }

    return {
        "code": code, "name": stock["name"], "market": market,
        "market_cap_eok": stock["market_cap_eok"],
        "ok": True, "reason": None,
        "closes": closes, "dates": dates,
        "last_date": dates[-1] if dates else None,
        "last_close": closes[-1],
    }


# ──────────────────────────────────────────────────
# RS 백분위 계산 (단축 윈도우 지원)
# ──────────────────────────────────────────────────

def _ret_over_window(closes: list[float], win: int) -> float | None:
    """closes[-1] 기준으로 win 거래일 전 대비 수익률 (소수 비율, +0.5 = +50%)."""
    if len(closes) < win + 1:
        return None
    base = closes[-win - 1]
    if base is None or base <= 0:
        return None
    return closes[-1] / base - 1.0


def _compute_rs_for_all(raw_results: list[dict], min_pool: int = MIN_RS_COMPARISON_POOL) -> dict[str, dict]:
    """각 종목의 RS 점수(1-99) 계산. compute_rs.py 공식 그대로 따름.

    종목별 윈도우(win) = min(보유 일수 - 1, 252).
    같은 win 이상 보유한 종목만 비교 풀에 포함.
    표본 < MIN_RS_COMPARISON_POOL 이면 RS = None.

    Returns:
        {code: {"rs": int|None, "win": int, "ret_pct": float|None,
                "rs_universe_n": int, "rs_basis": str, "rs_note": str|None}}
    """
    ok_rows = [r for r in raw_results if r.get("ok") and r.get("closes")]
    if not ok_rows:
        return {}

    # 1) 각 종목 win 결정 + ret 계산 (자기 win 으로)
    own_ret: dict[str, tuple[int, float]] = {}  # code → (win, ret)
    for r in ok_rows:
        n = len(r["closes"])
        win = min(n - 1, WINDOW_52W)
        if win < 20:   # 너무 짧으면 RS 산출 보류
            continue
        ret = _ret_over_window(r["closes"], win)
        if ret is None:
            continue
        own_ret[r["code"]] = (win, ret)

    # 2) 각 종목 win 별로 비교 풀 구성 → 백분위
    # 효율: 동일 win 으로 정렬된 ret 리스트를 캐시
    ret_by_win: dict[int, list[float]] = {}
    for r in ok_rows:
        n = len(r["closes"])
        # 각 종목은 자기 win 뿐 아니라 더 짧은 win 의 비교풀에도 들어갈 수 있어야 함
        # → 즉 보유 일수가 win 이상인 종목은 win 길이 수익률을 줄 수 있다
        # 메모리 절약: 자기 win 하나만 등록하고, 비교 시 win 필요한 종목별로 동적 계산은 비용 높음.
        # 단순화: 자기 own_ret 만 RS 후보로 등록. 비교 풀도 own_ret 의 같은-or-긴 윈도우 종목으로.
        pass

    # 단순화: 자기 win 으로 비교풀 = 같은 win 의 ret 분포 (boucle 1)
    # 종목마다 다른 win 일 수 있어 풀이 작아질 수 있음.
    # 252일짜리는 풀 크기 큼, 단축은 풀 작음. 단축이 100 미만이면 None 처리.
    code_to_win: dict[str, int] = {c: v[0] for c, v in own_ret.items()}
    for c, (win, ret) in own_ret.items():
        ret_by_win.setdefault(win, []).append(ret)

    # sort 한 번
    sorted_by_win: dict[int, list[float]] = {
        w: sorted(rs) for w, rs in ret_by_win.items()
    }

    out: dict[str, dict] = {}
    for r in ok_rows:
        code = r["code"]
        if code not in own_ret:
            out[code] = {"rs": None, "win": 0, "ret_pct": None,
                         "rs_universe_n": 0,
                         "rs_basis": "산출불가",
                         "rs_note": f"보유 일수 너무 짧음 (n={len(r['closes'])})"}
            continue
        win, ret = own_ret[code]
        # 비교풀: 같은 win 의 ret 분포
        pool = sorted_by_win.get(win, [])
        pool_size = len(pool)
        if pool_size < min_pool:
            out[code] = {"rs": None, "win": win,
                         "ret_pct": round(ret * 100, 2),
                         "rs_universe_n": pool_size,
                         "rs_basis": f"단축 {win}거래일",
                         "rs_note": f"비교 표본 < {min_pool} (n={pool_size})"}
            continue
        # 본인보다 낮은 종목 비율 → 1-99
        below = bisect.bisect_left(pool, ret)
        rs = max(1, min(99, round(below / pool_size * 100)))
        basis = "52주(252거래일)" if win == WINDOW_52W else f"단축 {win}거래일"
        out[code] = {
            "rs": rs,
            "win": win,
            "ret_pct": round(ret * 100, 2),
            "rs_universe_n": pool_size,
            "rs_basis": basis,
            "rs_note": None,
        }
    return out


# ──────────────────────────────────────────────────
# 메인 흐름
# ──────────────────────────────────────────────────

def fetch_market_status(asof: str | None) -> dict:
    """KOSPI ^KS11 추세 판정. asof 지원."""
    ks = fetch_yahoo_chart("^KS11", "2y" if asof else "1y", "1d")
    if not ks or not ks.get("closes"):
        return {"passed": False, "value": "데이터 부족", "detail": "KOSPI 일봉 조회 실패"}
    closes = ks["closes"]
    dates = [datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d") for t in ks["timestamps"]]
    if asof:
        idx = bisect.bisect_right(dates, asof)
        closes = closes[:idx]
    if len(closes) < 220:
        return {"passed": False, "value": "데이터 부족", "detail": f"closes={len(closes)}"}
    passed, value, detail = evaluate_m(closes)
    return {"passed": passed, "value": value, "detail": detail,
            "kospi_close": round(closes[-1], 2)}


def evaluate_single(code: str, market: str | None, asof: str | None, rs_min: int) -> None:
    """단일 종목 디버그 출력."""
    # 시장 판정 (Yahoo 보조)
    if not market:
        ks = fetch_yahoo_chart(f"{code}.KS", "1mo", "1d")
        kq = fetch_yahoo_chart(f"{code}.KQ", "1mo", "1d")
        if kq and not ks:
            market = "KOSDAQ"
        else:
            market = "KOSPI"

    stub = {"code": code, "name": code, "market": market, "market_cap_eok": 0}
    raw = _collect_one(stub, asof)
    print(f"\n=== {code} ({market}) ===")
    print(f"수집 결과: ok={raw['ok']}, reason={raw['reason']}")
    if not raw["ok"]:
        return

    closes = raw["closes"]
    print(f"보유 일수: {len(closes)} (마지막 {raw['dates'][-1]})")
    # 단일 모드는 universe RS 가 없으므로 None 전달
    result = evaluate_trend_template(closes, rs=None, rs_min=rs_min)
    print(f"\n전체 통과: {result['pass']} (통과 개수 {result['passed_count']}/8)")
    print("\n[조건별 평가]")
    for k, v in result["criteria"].items():
        mark = "[O]" if v["pass"] else "[X]"
        print(f"  {k}. {mark} {v['detail']}")
    print("\n[참고값]")
    for k, v in result["extras"].items():
        print(f"  {k}: {v}")
    print("\n* 단일 종목 모드는 RS 미산출 (전체 스캔 시에만 계산)")


def run_full_scan(args: argparse.Namespace) -> None:
    """전체 스캔 → JSON 저장."""
    asof = args.asof
    rs_min = args.rs_min

    print(f"🎯 트렌드 템플레이트 스크리너 (기준일: {asof or '오늘'}, RS 합격선: {rs_min})")

    # ── 1단계: KOSPI 추세
    print("\n📊 KOSPI 추세 판정 (참고용, gate 아님)")
    market_status = fetch_market_status(asof)
    print(f"  → {market_status['value']}")
    print(f"  {market_status['detail']}")

    # ── 2단계: universe
    print("\n📋 종목 리스트 수집")
    universe = fetch_universe_with_cap(args.market)
    if args.limit:
        universe = universe[:args.limit]
        print(f"  --limit {args.limit} 적용 → {len(universe)}종목 (시총 상위)")
    else:
        kospi_n = sum(1 for u in universe if u["market"] == "KOSPI")
        kosdaq_n = sum(1 for u in universe if u["market"] == "KOSDAQ")
        print(f"  전체: {len(universe)} (KOSPI {kospi_n} / KOSDAQ {kosdaq_n})")

    # ── 3단계: 종목별 일봉 수집 (병렬)
    print(f"\n📈 일봉 수집 중 (병렬 {MAX_WORKERS}워커)...")
    start = time.time()
    raw_results: list[dict] = []
    completed = 0

    def task(stock):
        return _collect_one(stock, asof)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for r in ex.map(task, universe):
            raw_results.append(r)
            completed += 1
            if completed % 100 == 0 or completed == len(universe):
                ok = sum(1 for x in raw_results if x["ok"])
                print(f"  진행 {completed}/{len(universe)} (수집 성공 {ok})")

    elapsed = time.time() - start
    ok_count = sum(1 for r in raw_results if r["ok"])
    fail_count = len(raw_results) - ok_count
    print(f"\n  수집 완료: 성공 {ok_count} / 실패 {fail_count} ({elapsed:.1f}s)")

    # ── 4단계: RS 계산
    print(f"\n🏅 RS 점수 (1-99) 계산 중... (비교풀 최소 {args.rs_pool_min})")
    rs_map = _compute_rs_for_all(raw_results, min_pool=args.rs_pool_min)
    rs_n = sum(1 for v in rs_map.values() if v["rs"] is not None)
    print(f"  RS 산출: {rs_n}종목")

    # ── 5단계: 트렌드 템플레이트 평가 (조건 1-8 통합)
    print("\n🔍 8가지 조건 평가 중...")
    candidates: list[dict] = []
    failed_stocks: list[dict] = []
    pass_count = 0

    for r in raw_results:
        if not r["ok"]:
            failed_stocks.append({
                "code": r["code"], "name": r["name"],
                "market": r["market"], "market_cap_eok": r["market_cap_eok"],
                "reason": r["reason"],
            })
            continue
        rs_entry = rs_map.get(r["code"], {})
        rs_val = rs_entry.get("rs")
        result = evaluate_trend_template(r["closes"], rs=rs_val, rs_min=rs_min)
        cand = {
            "code": r["code"],
            "name": r["name"],
            "market": r["market"],
            "market_cap_eok": r["market_cap_eok"],
            "current_price": r["last_close"],
            "last_date": r["last_date"],
            "rs": rs_val,
            "rs_basis": rs_entry.get("rs_basis"),
            "rs_window_days": rs_entry.get("win"),
            "rs_universe_n": rs_entry.get("rs_universe_n"),
            "return_window_pct": rs_entry.get("ret_pct"),
            "rs_note": rs_entry.get("rs_note"),
            "passed_count": result["passed_count"],
            "all_pass": result["pass"],
            "criteria": result["criteria"],
            "extras": result["extras"],
        }
        candidates.append(cand)
        if result["pass"]:
            pass_count += 1

    # 정렬: 전체 통과 우선, 그 다음 RS 내림차순, 그 다음 passed_count
    def sort_key(c):
        return (
            -1 if c["all_pass"] else 0,
            -(c["rs"] or -1),
            -(c["passed_count"] or 0),
        )
    candidates.sort(key=sort_key)

    print(f"\n✨ 8개 모두 통과: {pass_count}종목")

    # ── 6단계: JSON 저장 / 콘솔 출력
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof or datetime.now(KST).strftime("%Y-%m-%d"),
        "scanned_count": len(universe),
        "evaluated_count": ok_count,
        "all_pass_count": pass_count,
        "rs_universe_n": rs_n,
        "rs_min": rs_min,
        "thresholds": {
            "low_min_pct": TT_LOW_MIN_PCT,
            "high_max_pct": TT_HIGH_MAX_PCT,
            "sma200_rising_lookback_days": TT_SMA200_RISING_LOOKBACK_DAYS,
            "sma200_rising_preferred_days": TT_SMA200_RISING_PREFERRED_DAYS,
        },
        "market_status": market_status,
        "candidates": candidates,
        "failed_stocks": failed_stocks,
    }

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n💾 저장: {OUTPUT_PATH.relative_to(ROOT)}")
        print(f"   (총 {len(candidates)}종목, 8개 통과 {pass_count}종목)")
    else:
        # 상위 20개만 콘솔 미리보기
        print("\n[8개 통과 종목 상위 20]")
        top = [c for c in candidates if c["all_pass"]][:20]
        if not top:
            print("  (없음)")
        for c in top:
            print(f"  {c['code']} {c['name']:12s} ({c['market']})"
                  f" 시총 {c['market_cap_eok']:>6}억"
                  f" 종가 {c['current_price']:>10,.0f}"
                  f" RS {c['rs']:>2}"
                  f" 5M↑={c['extras']['sma200_rising_5m_preferred']}")


def main():
    parser = argparse.ArgumentParser(description="Minervini 트렌드 템플레이트 스크리너")
    parser.add_argument("--ticker", help="단일 종목 디버그 모드 (6자리 코드)")
    parser.add_argument("--market", default="all",
                        choices=["all", "KOSPI", "KOSDAQ"],
                        help="대상 시장 (default: all)")
    parser.add_argument("--asof", default=None,
                        help="기준 날짜 YYYY-MM-DD (default: 오늘). 룩어헤드 방지용 과거 분석에 사용")
    parser.add_argument("--rs-min", type=int, default=TT_RS_MIN_DEFAULT,
                        help=f"RS 합격선 1-99 (default: {TT_RS_MIN_DEFAULT}, Minervini 책 기준)")
    parser.add_argument("--limit", type=int, default=None,
                        help="시총 상위 N 종목만 처리 (디버그/시범용)")
    parser.add_argument("--rs-pool-min", type=int, default=MIN_RS_COMPARISON_POOL,
                        help=f"RS 백분위 계산 시 비교 모집단 최소 개수 (default: {MIN_RS_COMPARISON_POOL}). "
                             f"--limit 시범 시 30 정도로 낮추면 산출됨.")
    parser.add_argument("--save", action="store_true",
                        help=f"결과를 {OUTPUT_PATH.name} 에 저장")
    args = parser.parse_args()

    if args.ticker:
        evaluate_single(args.ticker, None, args.asof, args.rs_min)
        return

    run_full_scan(args)


if __name__ == "__main__":
    main()
