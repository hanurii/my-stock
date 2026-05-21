"""한국형 최적 매수 타이밍 — 사후 최적진입 시그니처 역산.

각 위너의 [trough,peak] 구간에서 '사후 최적 진입일'을 찾고(R=위험대비수익),
그 날을 오닐 9개 매수타이밍 변수축에 사상해 한국형 시그니처를 역산한다.
오닐 규칙을 강요하지 않음 — 시그니처는 데이터에서 emergent. 예측규칙 v1은
'후보'이며 거짓양성률은 미검증(위너만 표본 — 한계 명시, 환각 금지).

사용:  python analyze_buy_timing.py [--limit N]   (OMB_CYCLE 환경변수로 사이클)
"""
import argparse
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol, sleep  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402
from detect_cycles import zigzag  # noqa: E402

_FGN: dict = {}


def fgn_map(code: str, pages: int = 22) -> dict | None:
    """best_entry 전후 외국인/기관 일별 순매수. {date: (fgn,org)}.
    finance.naver frgn ≈ pages×20영업일(22p≈1.7년 — c2024-12 진입 도달).
    옛 사이클은 결손 가능(추정 금지)."""
    if code in _FGN:
        return _FGN[code]
    try:
        rows = fetch_naver_org_flow(code, pages=pages, sleep_ms=200)
        m = {r["date"]: (r.get("fgn_net"), r.get("org_net")) for r in rows} or None
    except Exception:
        m = None
    _FGN[code] = m
    return m

DIR = cyclecfg.DIR
HIST = cyclecfg.RESEARCH / "analysis_history.md"
BUY_MD = cyclecfg.RESEARCH / "buy_timing.md"

MIN_HOLD = 20      # best_entry는 고점 최소 20거래일 전 (진입이지 '바닥 1틱' 방지)
EPS = 0.01         # R 분모 안정화
STOP = 0.08        # 오닐 손절 −8%

_IDX = {}


def idx_series(market: str):
    sym = "%5EKS11" if market == "KOSPI" else "%5EKQ11"
    if sym not in _IDX:
        ch = cyclecfg.yahoo(sym)
        _IDX[sym] = ch or {}
    return _IDX[sym]


def regime_at(market: str, date_str: str) -> str | None:
    s = idx_series(market)
    ts = s.get("timestamps")
    if not ts:
        return None
    ds = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in ts]
    c = s["closes"]
    i = max((k for k in range(len(ds)) if ds[k] <= date_str), default=None)
    if i is None or i < 200:
        return None
    px, m50, m200 = c[i], sum(c[i - 49:i + 1]) / 50, sum(c[i - 199:i + 1]) / 200
    if px > m50 and px > m200 and m50 > m200:
        return "상승추세"
    return "중립" if px > m200 else "하락추세"


def load(name):
    p = DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def analyze_one(w, pmap, bmap, mmap):
    code, mkt, name = w["code"], w["market"], w["name"]
    tro, peak = w["trough_date"], w["peak_date"]
    ch = cyclecfg.yahoo(yahoo_symbol(code, mkt))
    sleep(60)
    if not ch or not ch.get("closes"):
        return {"code": code, "name": name, "error": "시세조회실패"}
    ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in ch["timestamps"]]
    c, v = ch["closes"], ch["volumes"]
    n = len(c)

    def nidx(dstr):
        cand = [k for k in range(n) if ts[k] <= dstr]
        return cand[-1] if cand else None

    ti, pi = nidx(tro), nidx(peak)
    if ti is None or pi is None or pi - ti < MIN_HOLD + 5:
        return {"code": code, "name": name, "error": "구간부족"}

    def sma(arr, j, w):
        return sum(arr[j - w + 1:j + 1]) / w if j >= w - 1 else None

    # 추세확인 필터(오닐 비강요·일반): 그날 알 수 있는 정보만으로 실행가능한
    # 진입만 후보 — 종가>50일선 & 50일선 상승(>10일전) & 종가>20거래일전.
    # (없으면 R이 '정확한 바닥'으로 degenerate → 예측 불가. 검증서 확인됨.)
    def confirmed(d):
        if d < 60:
            return False
        m, mp = sma(c, d, 50), sma(c, d - 10, 50)
        return (m is not None and mp is not None and c[d] > m and m > mp
                and c[d] > c[d - 20])

    best_i, best_R, best_mdd = None, -1e9, 0.0
    for d in range(ti, pi - MIN_HOLD + 1):
        if c[d] <= 0 or not confirmed(d):
            continue
        run_max, mdd = c[d], 0.0
        for k in range(d, pi + 1):
            if c[k] > run_max:
                run_max = c[k]
            dd = (run_max - c[k]) / run_max if run_max else 0.0
            if dd > mdd:
                mdd = dd
        R = (c[pi] / c[d] - 1) / (mdd + EPS)
        if R > best_R:
            best_R, best_i, best_mdd = R, d, mdd
    if best_i is None:                       # 추세확인 후보 없음 → 결손(추정 금지)
        return {"code": code, "name": name, "error": "추세확인 진입 없음"}
    simple_i = min(range(ti, pi + 1), key=lambda k: c[k])  # 바닥(degeneracy 대비용)

    o = {"code": code, "name": name, "market": mkt,
         "trough_date": tro, "peak_date": peak,
         "best_entry_date": ts[best_i], "best_entry_close": round(c[best_i], 1),
         "R": round(best_R, 2), "maxDD_after_pct": round(best_mdd * 100, 1),
         "simple_low_date": ts[simple_i],
         "best_vs_simplelow_days": best_i - simple_i,
         "best_vs_trough_pct": round((c[best_i] / c[ti] - 1) * 100, 1),
         "resid_upside_pct": round((c[pi] / c[best_i] - 1) * 100, 1),
         "trough_to_best_days": best_i - ti,
         "elapsed_frac": round((best_i - ti) / (pi - ti), 2)}

    mb = mmap.get(code, {})
    bk = bmap.get(code, {})
    pv = None
    pr = pmap.get(code, {})
    for vv in pr.get("variants", []):
        if abs(vv.get("drawdown", 0) - 0.20) < 1e-6:
            pv = vv
            break

    # 축1 base 품질 (model_book 재사용) + 200일선
    o["base_len_days"] = mb.get("base_len_days")
    o["base_depth_pct"] = mb.get("base_depth_pct")
    o["prior_uptrend_pct"] = mb.get("prior_uptrend_pct")
    o["above_ma200_at_best"] = (c[best_i] > sum(c[best_i - 199:best_i + 1]) / 200
                                if best_i >= 200 else None)

    # 축2 base 고점 대비 best 위치
    bs = mb.get("base_start_date")
    bsi = nidx(bs) if bs else None
    pvi = nidx(pv["pivot_date"]) if pv and pv.get("pivot_date") else None
    if bsi is not None and pvi is not None and pvi > bsi:
        bhi = max(c[bsi:pvi + 1])
        blo = min(c[bsi:pvi + 1])
        o["best_vs_base_high_pct"] = round((c[best_i] / bhi - 1) * 100, 1)
        o["best_in_base_band"] = (round((c[best_i] - blo) / (bhi - blo), 2)
                                  if bhi > blo else None)

    # 축3 거래량 배수 (직전 50일)
    s = slice(max(0, best_i - 50), best_i)
    av = sum(v[s]) / max(1, len(v[s]))
    o["best_vol_vs_50d"] = round(v[best_i] / av, 2) if av else None

    # 축4 매수존: pivot/breakout 가격·시점 대비
    if pv:
        o["best_vs_pivot_price_pct"] = round((c[best_i] / pv["pivot_close"] - 1) * 100, 1)
        if pvi is not None:
            o["best_minus_pivot_days"] = best_i - pvi
    if bk.get("breakout_date"):
        bki = nidx(bk["breakout_date"])
        if bki is not None:
            o["best_minus_breakout_days"] = best_i - bki

    # 축5 신고가 거리
    if best_i >= 1:
        hh = max(c[max(0, best_i - 250):best_i])
        o["best_vs_52w_high_pct"] = round(c[best_i] / hh * 100, 1) if hh else None

    # 축6 타이트(직전 15일 변동성·거래량 추세)
    w15 = c[max(0, best_i - 15):best_i]
    if len(w15) >= 5:
        o["tight_cv_pct"] = round(st.pstdev(w15) / (sum(w15) / len(w15)) * 100, 1)
    v15, vprev = v[max(0, best_i - 15):best_i], v[max(0, best_i - 30):max(0, best_i - 15)]
    if v15 and vprev:
        o["vol_dryup_ratio"] = round((sum(v15) / len(v15)) / (sum(vprev) / len(vprev) or 1), 2)

    # 축7 시장국면(그 날)
    o["market_regime_at_best"] = regime_at(mkt, ts[best_i])
    # 축8 RS (winner-level)
    o["rs_score"] = mb.get("rs_score")
    # 축9 −8% 손절 생존: best 이후 고점 전 종가가 best*0.92 하회한 적?
    stopped = any(c[k] <= c[best_i] * (1 - STOP) for k in range(best_i + 1, pi + 1))
    o["stop8_survived"] = (not stopped)
    # 외국인 수급: best_entry 직전 20거래일 / 직후 20거래일 누적·이어짐 여부
    fm = None if NO_FGN else fgn_map(code)
    if fm:
        pre = [fm[ts[k]][0] for k in range(max(0, best_i - 20), best_i)
               if ts[k] in fm and fm[ts[k]][0] is not None]
        post = [fm[ts[k]][0] for k in range(best_i, min(pi, best_i + 20) + 1)
                if ts[k] in fm and fm[ts[k]][0] is not None]
        if pre:
            o["fgn_pre20_net"] = sum(pre)
        if post:
            o["fgn_post20_net"] = sum(post)
            o["fgn_post20_buydays_pct"] = round(
                100 * sum(1 for x in post if x > 0) / len(post), 1)
            o["fgn_continues"] = sum(post) > 0          # 진입 후 이어지는가
        d0 = fm.get(ts[best_i], (None, None))[0]
        if d0 is not None:
            o["fgn_at_best_pos"] = d0 > 0

    # zigzag base 스윙 수
    if bsi is not None and pvi is not None and pvi > bsi + 3:
        zz = zigzag(ts[bsi:pvi + 1], c[bsi:pvi + 1])
        o["base_swings"] = len(zz)
    return o


def med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(st.median(xs), 1) if xs else None


def q(xs, p):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return round(xs[int(p * (len(xs) - 1))], 1) if xs else None


NO_FGN = False


def main():
    global NO_FGN
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--no-fgn", action="store_true",
                    help="§7 외국인수급(frgn) 스킵 — best_entry 정확도 무영향, 고속")
    args = ap.parse_args()
    NO_FGN = args.no_fgn

    wf = load("winners_final.json")
    if not wf:
        print("winners_final.json 없음", file=sys.stderr)
        return
    winners = wf["winners"][:args.limit]
    pmap = {r["code"]: r for r in (load("pivots.json") or {}).get("pivots", [])}
    bmap = {r["code"]: r for r in (load("breakout.json") or {}).get("rows", [])}
    mmap = {r["code"]: r for r in (load("model_book.json") or {}).get("rows", [])}

    rows = []
    for i, w in enumerate(winners, 1):
        print(f"  [{i}/{len(winners)}] {w['name']}", file=sys.stderr)
        rows.append(analyze_one(w, pmap, bmap, mmap))
    ok = [r for r in rows if not r.get("error")]
    n = len(ok)
    if not n:
        print("유효 0", file=sys.stderr)
        return

    def col(k):
        return [r.get(k) for r in ok]

    L = [f"[{cyclecfg.CYCLE_ID}] 매수타이밍 N={n}  (생성 {datetime.now().strftime('%Y-%m-%d %H:%M')})",
         f"정의: best_entry = argmax R, R=(고점/진입가−1)/(진입후 maxDD+{EPS}), "
         f"고점 {MIN_HOLD}거래일 전까지 후보.",
         "",
         "== 한국형 best_entry 시그니처 (중앙 / 25~75분위) ==",
         f"best vs base고점 %      : {med(col('best_vs_base_high_pct'))} "
         f"({q(col('best_vs_base_high_pct'),.25)}~{q(col('best_vs_base_high_pct'),.75)})  [오닐: 피벗=base고점 돌파]",
         f"best vs pivot가격 %     : {med(col('best_vs_pivot_price_pct'))} "
         f"({q(col('best_vs_pivot_price_pct'),.25)}~{q(col('best_vs_pivot_price_pct'),.75)})  [오닐 매수존 +0~5%]",
         f"best 거래량/50일 배수   : {med(col('best_vol_vs_50d'))} "
         f"({q(col('best_vol_vs_50d'),.25)}~{q(col('best_vol_vs_50d'),.75)})  [오닐 +40~50%↑=1.4~1.5]",
         f"best vs 52주고가 %      : {med(col('best_vs_52w_high_pct'))}  [오닐 ~85%↑(15%이내)]",
         f"best 직전 변동성 CV%    : {med(col('tight_cv_pct'))} | 거래량마름비 {med(col('vol_dryup_ratio'))}",
         f"base 길이/깊이/선행상승 : {med(col('base_len_days'))}일 / "
         f"{med(col('base_depth_pct'))}% / {med(col('prior_uptrend_pct'))}%",
         f"base 스윙수            : {med(col('base_swings'))}",
         f"best vs 바닥(trough) %  : {med(col('best_vs_trough_pct'))} "
         f"({q(col('best_vs_trough_pct'),.25)}~{q(col('best_vs_trough_pct'),.75)})  "
         f"[실행가능 진입=바닥서 +이만큼 오른 뒤]",
         f"진입 시점: trough→best {med(col('trough_to_best_days'))}거래일, "
         f"경과율 {med(col('elapsed_frac'))}, 잔존상승 {med(col('resid_upside_pct'))}%",
         f"best − pivot 일수      : {med(col('best_minus_pivot_days'))} "
         f"(음수=pivot 전, 양수=후)",
         f"best − breakout 일수   : {med(col('best_minus_breakout_days'))}",
         f"best − 단순바닥 일수   : {med(col('best_vs_simplelow_days'))} (0이면 바닥=최적)",
         "",
         "== 비율 ==",
         f"시장 상승추세 비율   : {round(100*sum(1 for x in col('market_regime_at_best') if x=='상승추세')/n)}%",
         f"200일선 위 비율      : {round(100*sum(1 for x in col('above_ma200_at_best') if x)/n)}%",
         f"−8% 손절 생존 비율   : {round(100*sum(1 for x in col('stop8_survived') if x)/n)}%",
         f"best가 pivot '이전'  : {round(100*sum(1 for x in col('best_minus_pivot_days') if isinstance(x,int) and x<0)/n)}%",
         f"RS중앙               : {med(col('rs_score'))}",
         ]
    if NO_FGN:
        L += ["", "== 외국인 수급 == (--no-fgn: 스킵)"]
    else:
        L += [
            "",
            "== 외국인 수급 (best_entry 전후 20거래일) ==",
            f"진입 후 외인 순매수 이어짐 : "
            f"{round(100*sum(1 for x in col('fgn_continues') if x)/max(1,sum(1 for x in col('fgn_continues') if x is not None)))}% "
            f"(가용 {sum(1 for x in col('fgn_continues') if x is not None)}/{n})",
            f"진입 당일 외인 순매수(+)  : "
            f"{round(100*sum(1 for x in col('fgn_at_best_pos') if x)/max(1,sum(1 for x in col('fgn_at_best_pos') if x is not None)))}%",
            f"진입 직전20일 외인순매수 중앙 : {med(col('fgn_pre20_net'))}주",
            f"진입 직후20일 외인순매수 중앙 : {med(col('fgn_post20_net'))}주 / "
            f"매수일비율 중앙 {med(col('fgn_post20_buydays_pct'))}%",
        ]
    block = "\n".join(L)
    (DIR / f"_buytiming_N{n}.txt").write_text(block, encoding="utf-8")
    with HIST.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 매수타이밍 스냅샷 [{cyclecfg.CYCLE_ID}] N={n}\n\n```\n{block}\n```\n")
    # 사이클 디렉터리에 원자료도 저장
    (DIR / "buy_timing_rows.json").write_text(
        json.dumps({"cycle": cyclecfg.CYCLE_ID, "n": n, "rows": rows},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    err = len(rows) - n
    print(f"buy_timing N={n} (error {err}) saved: _buytiming_N{n}.txt, "
          f"buy_timing_rows.json + analysis_history append", file=sys.stderr)


if __name__ == "__main__":
    main()
