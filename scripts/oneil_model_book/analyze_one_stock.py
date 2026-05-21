"""단일 종목 상세 분석 (파라미터형) — 우리 원칙·로직 부합/차이 확인.

analyze_hmm.py 일반화: 어떤 종목이든 code/market/trough/pivot 지정.
수집: 2019~2022 일별 종가·거래량(Yahoo) + 외국인·기관 일별 순매수
(네이버 frgn deep). 산출: 월말 타임라인(종가·외인누적·기관누적),
빠른 +20% 출발점별 5신호+외인/기관 60일, 출구 시뮬(WIDE vs ONEIL),
원칙 부합/차이 요약. 종가·인-샘플·1종목·RS프록시. 환각 금지.

사용:  python analyze_one_stock.py --code 194480 --market KOSDAQ \
        --trough 2020-03-23 --pivot 2020-12-28 --name 데브시스터즈
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CYDIR = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
         / "cycles" / "c2020-03")
GAIN, MAXH, DROP = 0.20, 60, 0.10


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--market", required=True)        # KOSPI/KOSDAQ
    ap.add_argument("--trough", required=True)         # YYYY-MM-DD
    ap.add_argument("--pivot", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--p1", default="2019-01-01")
    ap.add_argument("--p2", default="2022-12-31")
    args = ap.parse_args()
    nm = args.name or args.code

    ch = fetch_yahoo_chart(yahoo_symbol(args.code, args.market),
                           period1=_ep(args.p1), period2=_ep(args.p2),
                           interval="1d")
    if not ch or not ch.get("closes"):
        print(f"{nm} 시세 조회 실패", file=sys.stderr)
        return
    ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ch["timestamps"]]
    c, v = ch["closes"], ch["volumes"]
    n = len(c)

    def idx(ds):
        cand = [k for k in range(n) if ts[k] <= ds]
        return cand[-1] if cand else 0

    try:
        fr = fetch_naver_org_flow(args.code, pages=120, sleep_ms=120)
    except Exception:
        fr = []
    frm = {r["date"]: (r.get("fgn_net") or 0, r.get("org_net") or 0)
           for r in fr}
    fdates = sorted(frm)

    def flow60(ds, kk):
        seg = [d for d in fdates if d <= ds][-60:]
        return sum(frm[d][kk] for d in seg) if len(seg) >= 30 else None

    ti = idx(args.trough)
    pki = max(range(ti, n), key=lambda k: c[k])
    lo, hi = c[ti], c[pki]
    L = [f"[{nm} {args.code}/{args.market}] 상세 분석 — 우리 원칙 대조",
         f"시세 {ts[0]}~{ts[-1]} ({n}일). 저점 {ts[ti]} {lo:,.0f} → "
         f"고점 {ts[pki]} {hi:,.0f} (×{hi/lo:.1f}, +{(hi/lo-1)*100:.0f}%)"
         + (f" | 우리 pivot {args.pivot}" if args.pivot else ""),
         "(RS백분위=단일종목 횡단 불가 → 52주수익률 프록시만)",
         "",
         "== 월말 타임라인 (종가 / 외국인 누적 / 기관 누적, 주) =="]
    cf = ci = 0
    cum = {}
    for d in fdates:
        cf += frm[d][0]
        ci += frm[d][1]
        cum[d] = (cf, ci)
    for yymm in [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]:
        days = [d for d in fdates if d.startswith(yymm)]
        if not days:
            continue
        dd = days[-1]
        f_, i_ = cum[dd]
        L.append(f"  {yymm}: 종가 {c[idx(dd)]:,.0f} | 외인누적 {f_:+,} | "
                 f"기관누적 {i_:+,}")
    L.append("")
    L.append("== 빠른 +20% 출발점 + 그 시점 지표 ==")
    x, casen = max(ti, 55), 0
    while x < n - 6 and casen < 14:
        if c[x] <= 0 or c[x] != min(c[max(0, x-5):min(n, x+6)]):
            x += 1
            continue
        tgt, hit, bad = c[x]*(1+GAIN), None, False
        for k in range(x+1, min(n, x+MAXH+1)):
            if c[k] <= c[x]*(1-DROP):
                bad = True
                break
            if c[k] >= tgt:
                hit = k
                break
        if not hit or bad:
            x += 1
            continue
        v50 = sum(v[x-50:x])/50 if x >= 50 and sum(v[x-50:x]) else None
        hi52 = max(c[max(0, x-252):x+1])
        m50 = ma(c, x, 50)
        r52 = (c[x]/c[x-252]-1)*100 if x >= 252 and c[x-252] > 0 else None
        f60, i60 = flow60(ts[x], 0), flow60(ts[x], 1)
        casen += 1
        L.append(f"  [{casen}] 매수 {ts[x]} {c[x]:,.0f} → +20% {hit-x}거래일 "
                 f"(이후최대 +{(max(c[x:])/c[x]-1)*100:.0f}%)")
        L.append(f"      거래량 {round(v[x]/v50,2) if v50 else '?'}배 | "
                 f"52주고가 {round(c[x]/hi52*100,1) if hi52 else '?'}% | "
                 f"50일선 {round((c[x]/m50-1)*100,1) if m50 else '?'}% | "
                 f"52주수익 {round(r52,0) if r52 is not None else '?'}% | "
                 f"직전60일 +{round((c[x]/min(c[max(0,x-60):x+1])-1)*100,0)}%")
        L.append((f"      외인60일 {f60:+,}주" if f60 is not None
                  else "      외인60일 결손")
                 + (f" | 기관60일 {i60:+,}주" if i60 is not None
                    else " | 기관60일 결손"))
        x = hit + 1
    L.append("")
    e = next((xx for xx in range(max(ti, 20), n-5)
              if ma(c, xx, 20) and c[xx] > ma(c, xx, 20)), None)
    if e is not None:
        end = n-1
        pk, wexit = c[e], end
        for k in range(e+1, end+1):
            pk = max(pk, c[k])
            if c[k] <= c[e]*0.85 or c[k] <= pk*0.65:
                wexit = k
                break
        oexit = end
        for k in range(e+1, end+1):
            g = c[k]/c[e]-1
            if c[k] <= c[e]*0.92:
                oexit = k
                break
            if g >= 0.20:
                oexit = k if (k-e) > 15 else min(end, e+40)
                break
        hit8 = next((ts[k] for k in range(e+1, pki+1)
                     if c[k] <= c[e]*0.92), None)
        L += ["== 출구 시뮬 (인과진입=저점후 첫 종가>20일선) ==",
              f"  진입 {ts[e]} {c[e]:,.0f}",
              f"  WIDE(-15%·-35%트레일): {ts[wexit]} {c[wexit]:,.0f} = "
              f"{(c[wexit]/c[e]-1)*100:+.0f}%",
              f"  ONEIL(-8%·+20%/8주): {ts[oexit]} {c[oexit]:,.0f} = "
              f"{(c[oexit]/c[e]-1)*100:+.0f}%",
              f"  (보유 끝까지 {(c[end]/c[e]-1)*100:+.0f}% / 고점 "
              f"+{(hi/c[e]-1)*100:.0f}%) | 오닐 −8% 초기손절: "
              f"{'발동 '+hit8 if hit8 else '미발동(생존)'}",
              ""]
    L += ["== 원칙 부합/차이 (사용자 판정용) ==",
          "월말표·출발점표로: 코로나 패닉 때 외인 순매도/기관 매집 가설,",
          "큰 상승 연료가 외인인지 기관인지, 5신호(조용·신고가아래·50일선)",
          "부합, 오닐+20%매도 vs 넓은트레일, −8% 발동 여부 직접 확인.",
          "한계: 단일종목·종가·RS프록시·frgn 결손 비임퓨트."]
    out = CYDIR / f"_stock_{args.code}_detail.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
