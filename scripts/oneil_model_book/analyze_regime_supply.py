"""약세장 시작 무렵 외국인·기관 수급 — 조기경고 검증 (사용자 1+2+3+기관).

질문:
 1. 표본 확대(대형주 바스켓 = 시장 대표 + winners 표본)로 굳히기.
 2. 수급(외인/기관 집중 순매도)을 "조심" 조기경고 후보로 정식 백테스트:
    200일선 신호(2021-11-12 점등, 고점대비 -10%·87거래일 늦음) 대비
    선행성 · 약세 커버리지 · 강세장 헛경보.
 3. 강세장 매도 강도 vs 약세장 시작 매도 강도 차이(임계 존재?).
 +  외국인뿐 아니라 *기관*도 ②③ 동일 분석(side-by-side).

데이터: finance.naver /item/frgn 일별 기관·외인 순매매(주식수, ~2010).
KRX 공식 시장합계 아님 = *표본 프록시*. 정규화 강도지표(시점간 비교):
 종목별 pressure(i,투자자) = 최근60일 순매수합 / (최근252일 |일별순| 합+eps)
 breadth(i,투자자) = 바스켓 중 최근60일 순매도(<0) 비율
원자료는 `_regime_supply_raw.json` 캐시(재실행 수초; --refresh로 강제재조회).
KOSPI ^KS11(정답 약세·200일선 신호 기준)·환각 금지·결손 비임퓨트.
사용: python analyze_regime_supply.py [--ns 25] [--seed 7] [--refresh]
"""
import argparse
import bisect
import json
import random
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402

CY = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
      / "cycles" / "c2024-12")
RAW = CY / "_regime_supply_raw.json"
PEAK, SIGNAL, BOTTOM = "2021-07-06", "2021-11-12", "2022-09-30"
BASKET = ["005930", "000660", "035420", "005380", "035720", "051910",
          "005490", "068270", "105560", "055550", "012330", "000270",
          "207940", "006400"]
W_BEAR_ONSET = ("2021-07-06", "2021-11-12")
W_BULL_21H1 = ("2021-02-01", "2021-06-30")
W_BULL_25 = ("2025-05-01", "2026-05-15")
INV = {0: "외국인", 1: "기관"}


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, default=25)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]
    pool = [r for r in rv if not r.get("exclude_reason")
            and r.get("n_days", 0) >= 250]
    random.seed(args.seed)
    win_codes = [w["code"] for w in random.sample(pool, min(args.ns, len(pool)))]
    all_codes = sorted(set(BASKET) | set(win_codes))
    need_pages = 92

    # 원자료: 캐시 우선 (재실행 수초)
    cache = {}
    if RAW.exists() and not args.refresh:
        cache = json.loads(RAW.read_text(encoding="utf-8"))
    by_code = {}
    n_ok = n_fetch = 0
    for code in all_codes:
        if code in cache:
            by_code[code] = {d: tuple(v) for d, v in cache[code].items()}
            n_ok += 1
            continue
        try:
            fr = fetch_naver_org_flow(code, pages=need_pages, sleep_ms=120)
        except Exception:
            continue
        if not fr:
            continue
        n_ok += 1
        n_fetch += 1
        m = {r["date"]: ((r.get("fgn_net") or 0), (r.get("org_net") or 0))
             for r in fr}
        by_code[code] = m
        cache[code] = {d: list(v) for d, v in m.items()}
    RAW.write_text(json.dumps(cache), encoding="utf-8")

    if not by_code:
        print("no flow data", file=sys.stderr)
        return

    def agg(codes):
        a = defaultdict(lambda: [0, 0])
        for c in codes:
            for d, v in by_code.get(c, {}).items():
                a[d][0] += v[0]
                a[d][1] += v[1]
        return a

    A_basket = agg([c for c in BASKET if c in by_code])
    A_win = agg([c for c in win_codes if c in by_code])

    def cum60(A, anchor):
        ds = sorted(d for d in A if d <= anchor)
        seg = ds[-60:]
        return [sum(A[d][k] for d in seg) for k in (0, 1)]

    code_dates = {c: sorted(m) for c, m in by_code.items()}

    def stock_pressure(code, anchor, idx):
        ds = code_dates[code]
        j = bisect.bisect_right(ds, anchor)
        if j < 80:
            return None
        seg60 = ds[max(0, j - 60):j]
        seg252 = ds[max(0, j - 252):j]
        if len(seg60) < 40:
            return None
        net60 = sum(by_code[code][d][idx] for d in seg60)
        absum = sum(abs(by_code[code][d][idx]) for d in seg252) or 1
        return net60 / absum

    def basket_intensity(anchor, idx):
        ps = [stock_pressure(c, anchor, idx) for c in BASKET if c in by_code]
        ps = [x for x in ps if x is not None]
        if not ps:
            return None, None
        return st.median(ps), 100 * sum(1 for x in ps if x < 0) / len(ps)

    def window_intensity(w0, w1, idx):
        anch = sorted(set(d for m in by_code.values() for d in m
                          if w0 <= d <= w1))
        rows = [basket_intensity(a, idx) for a in anch]
        prs = [r[0] for r in rows if r[0] is not None]
        brs = [r[1] for r in rows if r[1] is not None]
        return (st.median(prs) if prs else None,
                st.median(brs) if brs else None, len(anch))

    ch = fetch_yahoo_chart("%5EKS11", period1=_ep("2020-01-01"),
                           period2=_ep("2026-12-31"), interval="1d")
    kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ch["timestamps"]]
    kc = ch["closes"]

    def k200_signal(date):
        i = bisect.bisect_right(kd, date) - 1
        if i < 252:
            return None
        ma = sum(kc[i - 199:i + 1]) / 200
        ma_p = sum(kc[i - 219:i - 19]) / 200
        return (kc[i] < ma) and (ma < ma_p)

    sig_first = next((d for d in kd if d >= SIGNAL and k200_signal(d)), SIGNAL)
    bask_dates = sorted(A_basket)

    def trig(anchor, idx, kind, thr):
        p, b = basket_intensity(anchor, idx)
        if p is None:
            return None
        return (p <= thr) if kind == "pressure" else (b >= thr)

    GRID = [("pressure", -0.20), ("pressure", -0.40),
            ("breadth", 60.0), ("breadth", 75.0)]

    def eval_trig(idx, kind, thr):
        anch = [d for d in bask_dates if d >= PEAK]
        first = next((d for d in anch if trig(d, idx, kind, thr)), None)
        ip = bisect.bisect_left(kd, PEAK)
        lead = (bisect.bisect_left(kd, first) - ip) if first else None
        bull = [d for d in bask_dates if W_BULL_25[0] <= d <= W_BULL_25[1]]
        fa = (100 * sum(1 for d in bull if trig(d, idx, kind, thr))
              / len(bull) if bull else None)
        cov_n = cov_on = 0
        for d in bask_dates:
            i = bisect.bisect_right(kd, d) - 1
            if i < 252:
                continue
            ma = sum(kc[i - 199:i + 1]) / 200
            hi = max(kc[i - 251:i + 1])
            if kc[i] <= 0.80 * hi and kc[i] < ma:
                cov_n += 1
                if trig(d, idx, kind, thr):
                    cov_on += 1
        cov = 100 * cov_on / cov_n if cov_n else None
        return first, lead, fa, cov

    out = []
    out.append("[수급 조기경고 검증 — 외국인 vs 기관] 바스켓 %d/%d + "
               "winners %d (seed%d), deep frgn ~%dp, cache=%s"
               % (sum(1 for c in BASKET if c in by_code), len(BASKET),
                  sum(1 for c in win_codes if c in by_code), args.seed,
                  need_pages, "fetch%d" % n_fetch if n_fetch else "hit"))
    out.append("순매수=표본 일별 순매매 주식수 합(KRX 공식 아님·프록시). "
               "강도=per-stock 정규화 pressure 중앙(음=순매도) · "
               "breadth=순매도 종목%.")
    out.append("기준: 고점 %s / 200일선 신호 %s / 바닥 %s"
               % (PEAK, sig_first, BOTTOM))
    out.append("")

    out.append("== 1) 핵심시점 직전 60거래일 누적 순매수 (바스켓, 백만주) ==")
    out.append("                    | 외국인 | 기관")
    for tag, anc in (("고점 " + PEAK, PEAK), ("신호 " + sig_first, sig_first),
                     ("바닥 " + BOTTOM, BOTTOM)):
        bf = cum60(A_basket, anc)
        out.append("%-19s | %+8.1f | %+8.1f"
                   % (tag, bf[0] / 1e6, bf[1] / 1e6))
    out.append("→ 외인=고점쪽 front-load, 기관=바닥쪽까지 지속 매도면")
    out.append("  '외인 선행 / 기관 후행' 시점차.")
    out.append("")

    for idx in (0, 1):
        nm = INV[idx]
        out.append("== [%s] 3) 강세 vs 약세시작 매도 강도 ==" % nm)
        out.append("구간                         | 강도중앙(음=순매도)"
                   " | 순매도종목% | 일수")
        for tag, (w0, w1) in (("강세 2021상(2~6월)", W_BULL_21H1),
                               ("약세시작 2021-07~11", W_BEAR_ONSET),
                               ("강세 2025-05~2026-05", W_BULL_25)):
            p, b, nn = window_intensity(w0, w1, idx)
            out.append("%-28s | %s | %s | %d"
                       % (tag,
                          ("%+.2f" % p) if p is not None else "  -  ",
                          ("%4.0f%%" % b) if b is not None else " - ", nn))
        out.append("== [%s] 2) 조기경고 트리거 (vs 200일선=고점+87거래일) =="
                   % nm)
        out.append("트리거            | 첫점등(고점→거래일) | 약세커버 | "
                   "강세헛경보(2025~26)")
        for kind, thr in GRID:
            first, lead, fa, cov = eval_trig(idx, kind, thr)
            lab = ("압력≤%.2f" % thr if kind == "pressure"
                   else "순매도종목≥%.0f%%" % thr)
            out.append("%-16s | %s (%s거래일) | %s | %s"
                       % (lab, first or "-",
                          lead if lead is not None else "-",
                          ("%.0f%%" % cov) if cov is not None else "-",
                          ("%.0f%%" % fa) if fa is not None else "-"))
        out.append("")

    out.append("== 월별 순매수 (바스켓, 백만주, 2021-06~2022-12) ==")
    out.append("월       | 외국인 | 기관")
    for ym in sorted({d[:7] for d in A_basket
                      if "2021-06" <= d[:7] <= "2022-12"}):
        f = sum(A_basket[d][0] for d in A_basket if d[:7] == ym)
        o = sum(A_basket[d][1] for d in A_basket if d[:7] == ym)
        mk = ("  <-고점" if ym == PEAK[:7] else
              "  <-신호" if ym == sig_first[:7] else
              "  <-바닥" if ym == BOTTOM[:7] else "")
        out.append("%s | %+8.1f | %+8.1f%s" % (ym, f / 1e6, o / 1e6, mk))
    out.append("")
    out.append("== 한계 (정직) ==")
    out.append("표본 프록시(KRX 공식 아님·시총가중 아님·주식수 단순합)·")
    out.append("단일 약세장 in-sample·종가무관·수급 노이즈 큼·임계는")
    out.append("관찰 그리드(임의 컷오프 금지)·선행성은 2021 단일사례.")
    out.append("기관=국내 기관 합산(연기금/금투/투신 등 미분리).")

    fn = "_regime_supply_s%d.txt" % args.seed
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print("saved: %s (ok=%d fetch=%d)" % (fn, n_ok, n_fetch),
          file=sys.stderr)


if __name__ == "__main__":
    main()
