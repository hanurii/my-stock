"""전 종목 시세 캐시 *증분* 갱신 — 매일 빠르게.

문제: `_universe_prices_5y.json` 은 한 번 만들면 갱신 안 됨(compute_rs
build_cache: 파일 있으면 그대로 반환) → 캐시일 고정·구버전 종목·신규
상장 누락·상폐 잔존. 매일 5년치 재수집은 느림(수 분).

해결: 종목당 **최근 ~20거래일만** 받아 기존 캐시에 이어붙임(요청 작아
빠름). 실시간 상장목록 기준이라 신규 IPO 자동 포함·상폐 자연 탈락.
액면분할/배당 소급조정은 겹침 종가 불일치로 감지 → 그 종목만 전체
재수집. 신규/이력부족/오래된 종목은 1회 전체 수집. 주1회 전체 권장.

원자적 저장(tmp→replace)으로 큰 캐시 손상 방지. 환각 금지·결손 명시.

사용:
  python refresh_universe_cache.py            # 증분(매일)
  python refresh_universe_cache.py --full     # 전체 재수집(주1회 권장)
  python refresh_universe_cache.py --limit 30 # 소규모 검증
"""
import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.fetch import (fetch_stock_list, fetch_yahoo_chart,  # noqa: E402
                               yahoo_symbol, sleep)

KST = timezone(timedelta(hours=9))
CACHE = (ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"
         / "_universe_prices_5y.json")
MAX_WORKERS = 16
FULL_HISTORY_DAYS = 6 * 365      # 신규/전체 시 수집 범위
INCR_LOOKBACK_DAYS = 30          # 증분 시 되돌아보는 창(겹침검증 포함)
STALE_GAP_DAYS = 12              # 마지막 갱신이 이보다 오래면 안전하게 전체
MISMATCH_TOL = 0.01              # 겹침 종가 상대 허용오차(>1% = 소급조정)


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def ep(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d")
               .replace(tzinfo=KST).timestamp())


def now_ep() -> int:
    return int(datetime.now(KST).timestamp()) + 2 * 86400


def fetch_full(sym):
    return fetch_yahoo_chart(sym, period1=now_ep() - FULL_HISTORY_DAYS * 86400,
                             period2=now_ep(), interval="1d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="전체 재수집")
    ap.add_argument("--limit", type=int, default=0, help="검증용 N종목")
    args = ap.parse_args()

    U = (json.loads(CACHE.read_text(encoding="utf-8"))
         if CACHE.exists() else {})
    listing = fetch_stock_list("KOSPI") + fetch_stock_list("KOSDAQ")
    if args.limit:
        listing = listing[:args.limit]
    live_codes = {s["code"] for s in listing}
    today = datetime.now(KST).strftime("%Y-%m-%d")

    stat = {"new": 0, "incr": 0, "full": 0, "mismatch_full": 0,
            "nochange": 0, "fail": 0}

    def work(s):
        code, mkt = s["code"], s["market"]
        sym = yahoo_symbol(code, mkt)
        ex = U.get(code)
        need_full = (args.full or not ex or not ex.get("d")
                     or len(ex["d"]) < 60
                     or (datetime.strptime(today, "%Y-%m-%d")
                         - datetime.strptime(ex["d"][-1], "%Y-%m-%d")).days
                     > STALE_GAP_DAYS)
        if need_full:
            ch = fetch_full(sym)
            sleep(60)
            if not ch or not ch.get("closes"):
                return code, None, ("fail" if not ex else "nochange")
            return (code, {"d": [iso(t) for t in ch["timestamps"]],
                           "c": ch["closes"]},
                    "new" if not ex else "full")
        last = ex["d"][-1]
        ch = fetch_yahoo_chart(sym, period1=ep(last) - INCR_LOOKBACK_DAYS * 86400,
                               period2=now_ep(), interval="1d")
        sleep(60)
        if not ch or not ch.get("closes"):
            return code, None, "nochange"
        nd = [iso(t) for t in ch["timestamps"]]
        nc = ch["closes"]
        pos = {dt: i for i, dt in enumerate(nd)}
        # 겹침 종가 불일치(소급조정) → 전체 재수집
        for k in range(max(0, len(ex["d"]) - 8), len(ex["d"])):
            dt = ex["d"][k]
            if dt in pos:
                a, b = ex["c"][k], nc[pos[dt]]
                if a and b and abs(a - b) / abs(a) > MISMATCH_TOL:
                    fch = fetch_full(sym)
                    sleep(60)
                    if fch and fch.get("closes"):
                        return (code, {"d": [iso(t) for t in fch["timestamps"]],
                                       "c": fch["closes"]}, "mismatch_full")
                    break
        add_d = [dt for dt in nd if dt > last]
        if not add_d:
            return code, None, "nochange"
        merged_d = ex["d"] + add_d
        merged_c = ex["c"] + [nc[pos[dt]] for dt in add_d]
        return code, {"d": merged_d, "c": merged_c}, "incr"

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as exr:
        for code, data, tag in exr.map(work, listing):
            if data:
                U[code] = data
            stat[tag] = stat.get(tag, 0) + 1
            done += 1
            if done % 300 == 0:
                print(f"  진행 {done}/{len(listing)} {stat}",
                      file=sys.stderr, flush=True)

    delisted = [c for c in U if c not in live_codes]
    tmp = CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(U, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, CACHE)

    fresh = sum(1 for s in U.values() if s.get("d") and s["d"][-1] == today)
    print(f"DONE 캐시 {len(U)}종목 | {stat} | "
          f"상장목록 {len(live_codes)} | 캐시 잔존 상폐(미갱신) {len(delisted)} | "
          f"오늘({today})자 종목 {fresh}", file=sys.stderr)


if __name__ == "__main__":
    main()
