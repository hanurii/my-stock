"""[비교] 친구분 전략 vs 우리 메가캡 모멘텀 vs KOSPI.

친구분 = 시총 상위 10 동일가중·연간 재조정(빠진 거 빼고 새로 들어온
거 사기)·손절/스위치 없음·DCA(매달 적립). 세계적으로 알려진 정직한
패시브 전략. *우리 데이터로 직접 비교*.

세 전략:
  K. KOSPI 매수보유
  F. 친구분: top-10 EW·연 1회 재조정·항상 투자
  M. 우리 메가캡 모멘텀(베스트): 월간·N=5·top-30·1년 모멘텀·
     −15%손절·★약세현금화

지표: 전구간 ×배·CAGR·MDD(=마음 압박). 강세장 한정 별도. 점별
시총(close[t]×주식수, look-ahead 無). 비용 0.66%. n=2.
사용: python scripts/oneil_model_book/analyze_top10_friend.py
"""
import bisect
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE                       # noqa: E402
import analyze_equity_curve_rt as RT                    # noqa: E402
import analyze_doppelganger as AD                       # noqa: E402
import analyze_megatop as MT                            # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"


def pit_mcap(c, j, sh):
    return c[j] * sh / 1e8 if sh else 0


def top10_friend(src, cost=0.0066, k=10, rebal=252, markets=None):
    """top-k EW·연(annual=252거래일) 재조정·항상 투자(스위치 X).
    markets={'KOSPI'} 면 코스피 전용."""
    U = AD.pick_universe_file(src)
    codes_d = {kk: (s["d"], s["c"]) for kk, s in U.items()
               if s.get("d") and len(s.get("c", [])) > 260}
    if markets:
        mp = json.loads(
            (OUT / "_universe_market.json").read_text(encoding="utf-8"))
        codes_d = {k: v for k, v in codes_d.items()
                   if mp.get(k) in markets}
    al = sorted({x for d, _ in codes_d.values() for x in d})
    rs0 = al[min(len(al) - 1, 260)]
    end = al[-1]
    axis = [t for t in al if rs0 <= t <= end]
    sh = RT.load_shares()
    pos = {}                                # code -> {inv, entry}
    cash = 1.0
    eq_d, eq = [], []

    def topk(t):
        cap = []
        for code, (d, c) in codes_d.items():
            j = bisect.bisect_right(d, t) - 1
            if j < 0:
                continue
            mc = pit_mcap(c, j, sh.get(code, 0))
            if mc > 0:
                cap.append((mc, code, c[j]))
        cap.sort(reverse=True)
        return [(c, p) for _, c, p in cap[:k]]

    # 초기 매수
    init = topk(axis[0])
    each = 1.0 / max(1, len(init))
    for code, px in init:
        pos[code] = {"inv": each * (1 - cost), "entry": px}
    cash = 0.0
    rebal_t = 0
    for ti, t in enumerate(axis):
        # 연간 재조정
        if ti > 0 and ti - rebal_t >= rebal:
            rebal_t = ti
            now_top = {c: p for c, p in topk(t)}
            # 이탈 종목 매도 → 현금
            for code in list(pos):
                if code in now_top:
                    continue
                d, c = codes_d[code]
                i = bisect.bisect_right(d, t) - 1
                px = c[i] if i >= 0 else pos[code]["entry"]
                cash += pos[code]["inv"] * (px / pos[code]["entry"]) \
                    * (1 - cost)
                del pos[code]
            # 신규 진입에 균등 배분
            new_codes = [c for c in now_top if c not in pos]
            if new_codes and cash > 1e-9:
                each = cash / len(new_codes)
                for code in new_codes:
                    pos[code] = {"inv": each * (1 - cost),
                                 "entry": now_top[code]}
                cash = 0.0
        # 평가
        mv = cash
        for code, p in pos.items():
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq_d.append(t)
        eq.append(mv)
    return eq_d, eq


def mdd_of(eq):
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd * 100


def bull_chain(ed, eq, kd, kc):
    bl = [RT.bull_on(kd, kc, x) for x in ed]

    def ch(s):
        v = 1.0
        for i in range(1, len(s)):
            if bl[i] and s[i - 1] > 0:
                v *= s[i] / s[i - 1]
        return v
    bd = sum(1 for i in range(1, len(bl)) if bl[i])
    yb = bd / 252
    return ((ch(eq) ** (1 / yb) - 1) * 100 if yb > 0 and ch(eq) > 0 else 0)


def main():
    kd, kc = AE.kospi_series()
    L = ["[비교] 친구분 top-10 EW(연간) vs 우리 메가캡 모멘텀(월간·N=5)"
         " vs KOSPI 매수보유 — 두 사이클",
         "  · 친구분: top-10 동일가중·연 1회 재조정·항상 투자·"
         "스위치 X·손절 X",
         "  · 우리(메가캡 베스트): top-30 중 1년 모멘텀 N=5·월 1회·"
         "−15%손절·★약세현금화",
         "  · 비용 0.66% 왕복·점별 시총·강세장 한정 별도 산출",
         "=" * 70]
    for cid in ["c2024-12", "c2020-03"]:
        # KOSPI
        U = AD.pick_universe_file(cid)
        al = sorted({x for s in U.values() for x in s.get("d", [])
                     if s.get("c")})
        rs0 = al[min(len(al) - 1, 260)]
        end = al[-1]
        bh = AE.kospi_bh(kd, kc, rs0, end)
        bhM = AE.metrics(bh[0], bh[1])
        bhM["mdd"] = mdd_of(bh[1])
        bhM["bull"] = bull_chain(bh[0], bh[1], kd, kc)
        # 친구분
        ed, eq = top10_friend(cid)
        fM = AE.metrics(ed, eq)
        fM["mdd"] = mdd_of(eq)
        fM["bull"] = bull_chain(ed, eq, kd, kc)
        # 우리 메가캡 베스트(월간·N=5·top-30·1년)
        edM, eqM, tr = MT.run_method(cid, "A", 5, 0.0066,
                                     top_k=30, rebal_step=20, lookback=252)
        mM = AE.metrics(edM, eqM)
        mM["mdd"] = mdd_of(eqM)
        mM["bull"] = bull_chain(edM, eqM, kd, kc)
        yr = (datetime.strptime(end, "%Y-%m-%d")
              - datetime.strptime(rs0, "%Y-%m-%d")).days / 365.25
        L += [f"\n>>> {cid}  {rs0}~{end} (≈{yr:.1f}년)",
              "-" * 70,
              f"  {'전략':<24}| 전 ×배 | 연수익 | MDD  | 강세장만 CAGR",
              f"  {'KOSPI 매수보유':<24}| ×{bhM['final']:.2f}  | "
              f"{(bhM['cagr'] or 0)*100:+.0f}% | {bhM['mdd']:.0f}% | "
              f"{bhM['bull']:+.0f}%",
              f"  {'친구분 top-10 EW 연재조정':<24}| ×{fM['final']:.2f}  | "
              f"{(fM['cagr'] or 0)*100:+.0f}% | {fM['mdd']:.0f}% | "
              f"{fM['bull']:+.0f}%",
              f"  {'우리 메가캡(월·N=5)':<24}| ×{mM['final']:.2f}  | "
              f"{(mM['cagr'] or 0)*100:+.0f}% | {mM['mdd']:.0f}% | "
              f"{mM['bull']:+.0f}%"]
    L += ["\n" + "=" * 70,
          "해석: 친구분 전략은 *항상 투자·매우 단순*. 우리 시스템은",
          "*약세장 현금화·집중·모멘텀선별*. 친구분이 KOSPI·우리 둘 다",
          "근접/상회면 = 단순한 게 답(우리 정교화 무의미). 우리가",
          "친구분을 *위험조정 후*(MDD 대비 수익) 상회해야 라이브 가치.",
          "한계: 사후·종가·일별·n=2·점별시총=close×현재주식수(소오차)·",
          "친구분 DCA 미반영(일괄투자 가정·세후/거래비용 단순). "
          "친구분 실거래는 적립효과로 평균진입가 분산 효과 추가됨."]
    txt = "\n".join(L)
    (OUT / "_friend_vs_megatop.txt").write_text(txt, encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 친구분 vs 우리 메가캡 비교\n\n```\n{txt}\n```\n")
    print(txt)


if __name__ == "__main__":
    main()
