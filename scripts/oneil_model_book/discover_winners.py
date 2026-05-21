"""1단계 — 위너 발굴 (가격 기반, 펀더멘털 미사용).

오닐 "그레이트 위너 모델북" 방식: 사후적으로 가장 크게 오른 종목을 먼저 확정한다.
CAN SLIM 일절 미적용. 해석/판정 없음. 가격 데이터로 상승 배수만 산출.

사이클: 코스피·코스닥 지수의 2025년 이후 최저점 일자를 자동 산출 → 현재까지.
지속성 필터: 20일 이동평균 기반 "유지된 상승"으로 단발 스파이크(반짝 급등) 제외.

출력: research/oneil-model-book/winners.json
"""
import json
import sys
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # my-stock/
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from canslim_lib.fetch import fetch_stock_list, yahoo_symbol, sleep  # noqa: E402
import cyclecfg  # noqa: E402

KST = timezone(timedelta(hours=9))
OUT_DIR = cyclecfg.DIR
OUT = OUT_DIR / "winners.json"

MAX_WORKERS = 20
MIN_DAYS_IN_WINDOW = 120          # 사이클 내 최소 거래일 (데이터 충분성)
MA_WINDOW = 20                    # 지속성 판정용 이동평균
FLASH_RAW_CUTOFF = 3.0            # 이 배수 이상인데 유지 안 되면 반짝급등 후보
FLASH_SUSTAIN_RATIO = 0.5         # 유지배수 < 0.5 × 원배수 → 반짝급등 제외
JUMP_HI = 1.60                    # 1일 +60% 초과 = 한국 ±30% 제도상 불가 → 데이터/CA 의심
JUMP_LO = 0.60                    # 1일 -40% 초과 하락 동일


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


ANCHOR_DATE = cyclecfg.ANCHOR  # 사이클 앵커(저점 기준일) — cyclecfg에서 주입


def cycle_start_ts() -> int:
    """사이클 앵커일 00:00 KST unix ts (각 종목 저점 탐색 시작)."""
    return cyclecfg.anchor_ts()


def analyze(stock: dict, cycle_start_ts: int) -> dict | None:
    code, name, market = stock["code"], stock["name"], stock["market"]
    sym = yahoo_symbol(code, market)
    ch = cyclecfg.yahoo(sym)
    sleep(80)
    base = {"code": code, "name": name, "market": market}
    if not ch or not ch.get("closes"):
        return {**base, "exclude_reason": "시세조회실패"}

    ts, cl, vol = ch["timestamps"], ch["closes"], ch["volumes"]
    # 사이클 시작일 이후 구간
    w = [(t, c, v) for t, c, v in zip(ts, cl, vol) if t >= cycle_start_ts and c and c > 0]
    if len(w) < MIN_DAYS_IN_WINDOW:
        return {**base, "n_days": len(w), "exclude_reason": "데이터부족"}

    wt = [x[0] for x in w]
    wc = [x[1] for x in w]

    # 급격 점프(분할/병합/데이터 의심) 탐지: 한국 일일 ±30% 제도상 ±60%/-40% 불가
    for i in range(1, len(wc)):
        r = wc[i] / wc[i - 1]
        if r > JUMP_HI or r < JUMP_LO:
            return {
                **base, "n_days": len(w),
                "jump_date": iso(wt[i]), "jump_ratio": round(r, 3),
                "exclude_reason": "급격가격점프(분할/병합/데이터의심)",
            }

    # 사이클 내 최저 종가 → 그 이후 최고 종가 (원배수)
    tmin = min(range(len(wc)), key=lambda i: wc[i])
    trough_close = wc[tmin]
    after = wc[tmin:]
    pk_rel = max(range(len(after)), key=lambda i: after[i])
    peak_idx = tmin + pk_rel
    peak_close = wc[peak_idx]
    raw_multiple = peak_close / trough_close

    # 20일 이동평균 기반 "유지된 상승" (단발 스파이크 억제)
    ma_peak = trough_close
    ma_peak_idx = tmin
    for i in range(tmin, len(wc)):
        if i + 1 < MA_WINDOW:
            continue
        ma = sum(wc[i + 1 - MA_WINDOW:i + 1]) / MA_WINDOW
        if ma > ma_peak:
            ma_peak = ma
            ma_peak_idx = i
    sustained_multiple = ma_peak / trough_close

    rec = {
        **base,
        "n_days": len(w),
        "trough_date": iso(wt[tmin]),
        "trough_close": round(trough_close, 1),
        "peak_date": iso(wt[peak_idx]),
        "peak_close": round(peak_close, 1),
        "raw_multiple": round(raw_multiple, 3),
        "sustained_ma20_date": iso(wt[ma_peak_idx]),
        "sustained_multiple": round(sustained_multiple, 3),
        "last_close": round(wc[-1], 1),
        "exclude_reason": None,
    }
    # 반짝 급등(피크 미유지) 제외
    if raw_multiple >= FLASH_RAW_CUTOFF and sustained_multiple < FLASH_SUSTAIN_RATIO * raw_multiple:
        rec["exclude_reason"] = "반짝급등(피크미유지)"
    return rec


def main():
    cyc = cycle_start_ts()
    print("  " + cyclecfg.banner(), file=sys.stderr)

    universe = fetch_stock_list("KOSPI") + fetch_stock_list("KOSDAQ")
    print(f"  유니버스: {len(universe)}종목 (코스피+코스닥, SPAC/REIT/ETF/우선주 제외)", file=sys.stderr)

    results = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(analyze, s, cyc) for s in universe]
        for f in concurrent.futures.as_completed(futs):
            r = f.result()
            if r:
                results.append(r)
            done += 1
            if done % 100 == 0:
                print(f"  진행 {done}/{len(universe)}", file=sys.stderr)

    valid = [r for r in results if r.get("exclude_reason") is None]
    valid.sort(key=lambda r: r["sustained_multiple"], reverse=True)
    excluded = [r for r in results if r.get("exclude_reason") is not None]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "cycle_id": cyclecfg.CYCLE_ID,
        "cycle_start_date": cyclecfg.ANCHOR,
        "cycle_anchor": cyclecfg.LABEL,
        "cycle_end_date": cyclecfg.CYCLE_END,
        "universe_count": len(universe),
        "analyzed_count": len(results),
        "valid_count": len(valid),
        "excluded_count": len(excluded),
        "method": {
            "trough": "사이클 시작일 이후 최저 종가",
            "raw_multiple": "최저 종가 → 이후 최고 종가",
            "sustained_multiple": "최저 종가 → 이후 20일 이동평균 최고치 (단발 스파이크 억제)",
            "flash_spike_excluded": f"원배수≥{FLASH_RAW_CUTOFF} 이고 유지배수<{FLASH_SUSTAIN_RATIO}×원배수",
            "jump_excluded": f"1일 종가비 >{JUMP_HI} 또는 <{JUMP_LO} (한국 ±30% 제도상 데이터/기업행위 의심)",
        },
        "ranked_valid": valid,
        "excluded": excluded,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT}", file=sys.stderr)
    print(f"유효 {len(valid)} / 제외 {len(excluded)} / 분석 {len(results)}", file=sys.stderr)
    print("\n=== 유지배수 상위 40 ===", file=sys.stderr)
    for i, r in enumerate(valid[:40], 1):
        print(f"{i:2d}. {r['name']}({r['code']},{r['market']}) "
              f"유지배수 {r['sustained_multiple']:.2f}배  원배수 {r['raw_multiple']:.2f}배  "
              f"저점 {r['trough_date']} {r['trough_close']:,.0f} → 고점 {r['peak_date']} {r['peak_close']:,.0f}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
