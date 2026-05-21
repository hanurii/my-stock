"""HMM(011200) 단일 상세 분석 — 우리 원칙·로직 부합/차이 확인.

수집: 2019~2022 일별 종가·거래량(Yahoo) + 외국인·기관 일별 순매수
(네이버 frgn deep). 산출:
 1) 마일스톤: 저점·우리 pivot(2020-09-10)·고점·이후 하락
 2) 월말 타임라인: 종가 · 외국인 누적순매수 · 기관 누적순매수
 3) 빠른 +20% 출발점들: 각 시점 거래량/50일·52주고가%·50일선%·
    직전60일상승 · 외인60일순매수 · 기관60일순매수 (5신호 점검)
 4) 출구 시뮬: 인과진입→WIDE(-15%재해·-35%트레일) vs ONEIL(-8%·+20%/8주)
 5) 우리 원칙 부합/차이 요약(L·I·매수신호·손절·매도)

RS백분위는 단일종목이라 횡단 불가 → HMM 52주수익률(프록시)만, 명시.
종가·인-샘플·상폐무관·1종목. 환각 금지·결손 비임퓨트.
사용:  python analyze_hmm.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

OUT = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
       / "cycles" / "c2020-03" / "_hmm_detail.txt")
CODE, MKT = "011200", "KOSPI"
TROUGH = "2020-03-23"
PIVOT = "2020-09-10"          # REPORT.md c2020-03
GAIN, MAXH, DROP = 0.20, 60, 0.10


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def main():
    ch = fetch_yahoo_chart("011200.KS", period1=_ep("2019-01-01"),
                           period2=_ep("2022-12-31"), interval="1d")
    if not ch or not ch.get("closes"):
        print("HMM 시세 조회 실패", file=sys.stderr)
        return
    ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ch["timestamps"]]
    c, v = ch["closes"], ch["volumes"]
    n = len(c)

    def idx(ds):
        cand = [k for k in range(n) if ts[k] <= ds]
        return cand[-1] if cand else 0

    # 외국인·기관 일별 (deep frgn, 2019까지 ≈ pages 120)
    try:
        fr = fetch_naver_org_flow(CODE, pages=120, sleep_ms=120)
    except Exception:
        fr = []
    frm = {r["date"]: (r.get("fgn_net") or 0, r.get("org_net") or 0)
           for r in fr}
    fdates = sorted(frm)

    def flow60(ds, kk):
        seg = [d for d in fdates if d <= ds][-60:]
        return sum(frm[d][kk] for d in seg) if len(seg) >= 30 else None

    ti, pvi = idx(TROUGH), idx(PIVOT)
    pki = max(range(ti, n), key=lambda k: c[k])
    lo = c[ti]
    hi = c[pki]
    L = [f"[HMM 011200] 상세 분석 — 우리 원칙 대조",
         f"시세 {ts[0]}~{ts[-1]} ({n}일). 저점 {ts[ti]} {lo:,.0f} → ",
         f"고점 {ts[pki]} {hi:,.0f} (×{hi/lo:.1f}, +{(hi/lo-1)*100:.0f}%) | "
         f"우리 pivot {PIVOT}",
         "(RS백분위=단일종목 횡단 불가 → 52주수익률 프록시만 표기)",
         ""]

    # 2) 월말 타임라인 (종가·외인누적·기관누적)
    L.append("== 월말 타임라인 (종가 / 외국인 누적순매수 / 기관 누적순매수, 주) ==")
    cf = ci = 0
    seen = set()
    cumf = {}
    for d in fdates:
        cf += frm[d][0]
        ci += frm[d][1]
        cumf[d] = (cf, ci)
    for yymm in [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]:
        days = [d for d in fdates if d.startswith(yymm)]
        if not days:
            continue
        dd = days[-1]
        pc = c[idx(dd)]
        f_, i_ = cumf[dd]
        L.append(f"  {yymm}: 종가 {pc:,.0f} | 외인누적 {f_:+,} | 기관누적 {i_:+,}")
    L.append("")

    # 3) 빠른 +20% 출발점 + 5신호
    L.append("== 빠른 +20% 출발점 (스윙저점→−10%전 60일내 +20%) + 그 시점 지표 ==")
    x = max(ti, 55)
    casen = 0
    while x < n - 6 and casen < 14:
        if c[x] <= 0 or c[x] != min(c[max(0, x-5):min(n, x+6)]):
            x += 1
            continue
        tgt, hit = c[x]*(1+GAIN), None
        bad = False
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
        L.append(
            f"  [{casen}] 매수 {ts[x]} {c[x]:,.0f} → +20% {hit-x}거래일 "
            f"(이후최대 +{(max(c[x:])/c[x]-1)*100:.0f}%)")
        L.append(
            f"      거래량 {round(v[x]/v50,2) if v50 else '?'}배 | "
            f"52주고가 {round(c[x]/hi52*100,1) if hi52 else '?'}% | "
            f"50일선 {round((c[x]/m50-1)*100,1) if m50 else '?'}% | "
            f"52주수익 {round(r52,0) if r52 is not None else '?'}% | "
            f"직전60일 +{round((c[x]/min(c[max(0,x-60):x+1])-1)*100,0)}%")
        L.append(
            f"      외인60일 {f60:+,}주" if f60 is not None else
            "      외인60일 결손",)
        L[-1] += (f" | 기관60일 {i60:+,}주" if i60 is not None else
                  " | 기관60일 결손")
        x = hit + 1
    L.append("")

    # 4) 출구 시뮬 (인과진입)
    e = None
    for xx in range(max(ti, 20), n-5):
        m = ma(c, xx, 20)
        if m and c[xx] > m:
            e = xx
            break
    if e is not None:
        end = n-1
        # WIDE
        pk = c[e]
        wexit = end
        for k in range(e+1, end+1):
            pk = max(pk, c[k])
            if c[k] <= c[e]*0.85 or c[k] <= pk*0.65:
                wexit = k
                break
        # ONEIL
        oexit = end
        for k in range(e+1, end+1):
            g = c[k]/c[e]-1
            if c[k] <= c[e]*0.92:
                oexit = k
                break
            if g >= 0.20:
                oexit = k if (k-e) > 15 else min(end, e+40)
                break
        bh = c[end]/c[e]-1
        # −8% 초기손절이 큰 상승 전에 터졌나
        hit8 = next((ts[k] for k in range(e+1, pki+1)
                     if c[k] <= c[e]*0.92), None)
        L += ["== 출구 시뮬 (인과진입 = 저점후 첫 종가>20일선) ==",
              f"  진입 {ts[e]} {c[e]:,.0f}",
              f"  WIDE(-15%재해·-35%트레일): 청산 {ts[wexit]} {c[wexit]:,.0f} "
              f"= {(c[wexit]/c[e]-1)*100:+.0f}%",
              f"  ONEIL(-8%·+20%/8주): 청산 {ts[oexit]} {c[oexit]:,.0f} "
              f"= {(c[oexit]/c[e]-1)*100:+.0f}%",
              f"  (참고 매수후 보유 끝까지: {bh*100:+.0f}% / 고점기준 "
              f"+{(hi/c[e]-1)*100:.0f}%)",
              f"  오닐 −8% 초기손절: {'발동 '+hit8+' (큰상승 전 청산됨!)' if hit8 else '미발동(생존)'}",
              ""]

    # 5) 원칙 부합/차이 (데이터 기반 자동 메모 + 정성)
    f_all, i_all = (cumf[fdates[-1]] if fdates else (None, None))
    L += ["== 우리 원칙 부합/차이 (HMM) ==",
          f"  · I(수급): 전 구간 외국인 누적 {f_all:+,} / 기관 누적 {i_all:+,} "
          "→ 부호·시점은 위 월말표·출발점표로 직접 판단(개인 vs 외인/기관)",
          "  · 매수신호: 출발점표의 거래량(조용?)·신고가거리(아래?)·50일선",
          "    근처·직전상승 — 5신호 패턴 부합 여부 육안 대조",
          "  · 손절: 오닐 −8% 초기손절 발동 여부(위) = 한국형 −15%가 필요했나",
          "  · 매도: WIDE vs ONEIL 실현 — 넓은 트레일이 +20%매도보다 우월?",
          "  · L: 52주수익 프록시(출발점표) — 강했나(주도주?)",
          "한계: 단일 종목·종가·RS횡단 불가(프록시)·frgn 결손 비임퓨트.",
          "해석·결론은 사용자: 표를 보고 '개인장이라도 외인/기관이",
          "결정적이었나'를 직접 판정."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
