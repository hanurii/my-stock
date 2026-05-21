"""돌파일(breakout) 마커 — pivot(급등 출발 바닥)과 별개로,
base 를 위로 이탈하는 '돌파일'을 따로 찍어 그 날의 거래량·신고가를 검증.

배경: pivot 은 다수가 폴백 규칙으로 '급등 출발 바닥'에 찍힘 → 그 날의 거래량은
조용하고 가격은 신고가와 멀다. 오닐의 거래량 급증·신고가 돌파는 '돌파일'에
나타나므로, 별도 마커로 측정해야 공정.

돌파일 정의(명시): pivot 이후 ~ 고점 사이에서, 종가가
  (a) 직전 20거래일 최고 종가를 상회  AND
  (b) pivot(바닥) 종가 대비 +10% 이상   인 가장 이른 날.
없으면 fallback: pivot 이후 종가가 pivot 대비 +10% 처음 넘는 날.

측정: 돌파일 거래량/직전50일평균, 돌파일 종가/직전252일 최고(>=100=신고가 경신).
해석 없음. raw 값. model_book.json 에 breakout_* 직접 재반영.
"""
import json
import sys
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from canslim_lib.fetch import yahoo_symbol, sleep  # noqa: E402
import cyclecfg  # noqa: E402

KST = timezone(timedelta(hours=9))
DIR = cyclecfg.DIR
PIV = DIR / "pivots.json"
MODEL = DIR / "model_book.json"
OUT = DIR / "breakout.json"
CHOSEN_DD = 0.20
RES_WIN = 20          # 직전 저항(고점) 판정 거래일
BUFFER = 0.10         # 바닥 대비 최소 상승(노이즈 컷)
HIGH_WIN = 250        # 신고가 비교용 직전 거래일


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def analyze(rec: dict) -> dict:
    code, name, market = rec["code"], rec["name"], rec["market"]
    base = {"code": code, "name": name}
    if rec.get("error"):
        return {**base, "breakout_note": "pivot 오류"}
    v = next(x for x in rec["variants"] if abs(x["drawdown"] - CHOSEN_DD) < 1e-6)
    pd, peak = v["pivot_date"], rec["peak_date"]

    ch = cyclecfg.yahoo(yahoo_symbol(code, market))
    sleep(80)
    if not ch or not ch.get("closes"):
        return {**base, "breakout_note": "시세조회실패"}
    ts = [iso(t) for t in ch["timestamps"]]
    cl, vol = ch["closes"], ch["volumes"]
    n = len(cl)

    def nearest(ds):
        return min(range(n), key=lambda i: abs(
            (datetime.strptime(ts[i], "%Y-%m-%d") - datetime.strptime(ds, "%Y-%m-%d")).days))

    pi = nearest(pd)
    pk = nearest(peak)
    base_close = cl[pi]
    if base_close <= 0 or pk <= pi:
        return {**base, "breakout_note": "구간 부적합"}

    bo = None
    for i in range(pi + 1, pk + 1):
        res = max(cl[max(0, i - RES_WIN):i])          # 직전 20일 최고
        if cl[i] > res and cl[i] >= base_close * (1 + BUFFER):
            bo = i
            break
    method = "직전20일고점돌파+바닥대비10%"
    if bo is None:                                    # fallback: 바닥 대비 +10% 첫날
        for i in range(pi + 1, pk + 1):
            if cl[i] >= base_close * (1 + BUFFER):
                bo = i
                method = "폴백:바닥대비+10% 첫날"
                break
    if bo is None:
        return {**base, "pivot_date": pd, "breakout_note": "돌파 미검출(상승<10%)"}

    v50 = sum(vol[max(0, bo - 50):bo]) / max(1, len(vol[max(0, bo - 50):bo]))
    vol_x = round(vol[bo] / v50, 2) if v50 else None
    hi = max(cl[max(0, bo - HIGH_WIN):bo]) if bo > 0 else cl[bo]
    near_hi = round(cl[bo] / hi * 100, 1) if hi else None
    return {
        **base,
        "pivot_date": pd,
        "breakout_date": ts[bo],
        "breakout_close": round(cl[bo], 1),
        "breakout_method": method,
        "days_pivot_to_breakout": bo - pi,
        "gain_pivot_to_breakout_pct": round((cl[bo] / base_close - 1) * 100, 1),
        "breakout_vol_vs_50d": vol_x,
        "breakout_vs_prior_252d_high_pct": near_hi,   # >=100 이면 신고가 경신
    }


def main():
    pivots = json.loads(PIV.read_text(encoding="utf-8"))["pivots"]
    rows = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for r in ex.map(analyze, pivots):
            rows.append(r)
            done += 1
            if done % 40 == 0:
                print(f"  진행 {done}/{len(pivots)}", file=sys.stderr)

    DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "definition": __doc__.strip().splitlines()[6],
        "rows": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = [r for r in rows if r.get("breakout_vol_vs_50d") is not None]
    import statistics as st
    vx = [r["breakout_vol_vs_50d"] for r in ok]
    hh = [r["breakout_vs_prior_252d_high_pct"] for r in ok
          if r.get("breakout_vs_prior_252d_high_pct") is not None]
    if vx:
        print(f"돌파일 검출 {len(ok)}/{len(rows)}", file=sys.stderr)
        print(f"  거래량/50일: 중앙 {st.median(vx):.2f}  >=1.5배 "
              f"{sum(1 for x in vx if x>=1.5)}/{len(vx)}  >=2배 {sum(1 for x in vx if x>=2)}",
              file=sys.stderr)
        print(f"  돌파일 신고가대비: 중앙 {st.median(hh):.0f}%  >=100(경신) "
              f"{sum(1 for x in hh if x>=100)}/{len(hh)}  >=95 {sum(1 for x in hh if x>=95)}",
              file=sys.stderr)

    # model_book.json 직접 재반영
    if MODEL.exists():
        mb = json.loads(MODEL.read_text(encoding="utf-8"))
        bm = {r["code"]: r for r in rows}
        for row in mb.get("rows", []):
            x = bm.get(row.get("code"))
            if not x:
                continue
            for k in ("breakout_date", "breakout_close", "days_pivot_to_breakout",
                      "gain_pivot_to_breakout_pct", "breakout_vol_vs_50d",
                      "breakout_vs_prior_252d_high_pct", "breakout_method", "breakout_note"):
                if k in x:
                    row[k] = x[k]
        MODEL.write_text(json.dumps(mb, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"model_book.json breakout 재반영 ({len(mb.get('rows', []))}행)", file=sys.stderr)


if __name__ == "__main__":
    main()
