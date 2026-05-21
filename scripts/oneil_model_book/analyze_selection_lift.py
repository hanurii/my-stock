"""선별골격 lift — 한국식 CAN SLIM 축이 위너를 비위너에서 갈라내는가?

대조군 검증(타이밍 단독 lift≈1)의 후속: "선별 edge는 펀더멘털·수급 축"
이라는 *주장*을 증거로. 위너200(model_book) vs 비위너 대조군
(c2024-12-ctrl/model_book) 을 같은 변수로 비교, 각 축의
  enrichment = 위너 통과율 / 대조군 통과율  (>1 ⇒ 위너 쪽에 농축=변별력)
와 축을 누적 결합할 때 통과율 격차가 벌어지는지(=lift 상승) 측정.

한계(정직): 대조군 표본 작음·둘 다 *pivot* 시점 측정(타이밍 분리한
선별력 측정)·상폐 제외(생존자)·인-샘플. 실거래 수익 아님.

사용:  python analyze_selection_lift.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
OUT = CY / "c2024-12" / "_selection_lift.txt"


def rows(p):
    f = CY / p / "model_book.json"
    return json.loads(f.read_text(encoding="utf-8"))["rows"] if f.exists() else []


# 한국식 CAN SLIM v1 선별축 (korea_canslim.md / user_canslim_thresholds 근거)
def gM(r):  # 시장 상승추세
    v = r.get("market_regime_at_pivot")
    return (v == "상승추세") if v is not None else None


def gS(r):  # 소형·대주주≥30%·무희석
    lh, dl, mc = (r.get("largest_holder_pct"), r.get("share_dilution_1y_pct"),
                  r.get("market_cap_at_pivot_eok"))
    if lh is None or dl is None or mc is None:
        return None
    return (lh >= 30) and (dl == 0) and (mc < 10000)


def gL(r):  # 주도주 RS≥80
    v = r.get("rs_score")
    return (v >= 80) if isinstance(v, (int, float)) else None


def gI(r):  # 한국형: 외국인(또는 기관) 60일 순매수
    fg, inst = r.get("fgn_net_60d"), r.get("inst_net_60d")
    if fg is None and inst is None:
        return None
    return (fg or 0) > 0 or (inst or 0) > 0


def gIf(r):  # I 중 '외국인'만 (한국 핵심주체 분리 검증)
    fg = r.get("fgn_net_60d")
    return (fg > 0) if isinstance(fg, (int, float)) else None


def gC(r):  # 직전분기 EPS YoY > 0
    v = r.get("eps_yoy_q1_pct")
    return (v > 0) if isinstance(v, (int, float)) else None


def gK(r):  # 원/달러 6M 약세(원화 약세)
    v = r.get("krw_6m_change_pct")
    return (v > 0) if isinstance(v, (int, float)) else None


AXES = [("M 시장상승", gM), ("S 소형·대주주·무희석", gS), ("L RS≥80", gL),
        ("I 외인or기관매수", gI), ("I' 외국인만", gIf),
        ("C EPS YoY>0", gC), ("+K 원화약세", gK)]


def rate(rs, g):
    vals = [g(r) for r in rs]
    vals = [v for v in vals if v is not None]
    return (sum(1 for v in vals if v) / len(vals) if vals else None), len(vals)


def main():
    W = rows("c2024-12")          # 위너 200
    C = rows("c2024-12-ctrl")     # 비위너 대조군
    if not W or not C:
        print("model_book 부재 (위너 또는 대조군 수집 필요)", file=sys.stderr)
        return

    L = [f"선별골격 lift — 위너 {len(W)} vs 비위너 대조군 {len(C)}",
         "enrichment = 위너통과율 / 대조군통과율  (>1=위너에 농축=변별력)",
         "측정시점: 둘 다 pivot. 타이밍과 분리한 *선별력* 측정.",
         "",
         "축 | 위너통과 | 대조통과 | enrichment | (n위너/n대조)",
         "---|---|---|---|---"]
    scored = []
    for nm, g in AXES:
        pw, nw = rate(W, g)
        pc, nc = rate(C, g)
        if pw is None or pc is None:
            L.append(f"{nm} | {pw} | {pc} | - | ({nw}/{nc})")
            continue
        lift = (pw / pc) if pc > 0 else float("inf")
        scored.append((nm, g, lift, pw, pc))
        L.append(f"{nm} | {round(pw*100,1)}% | {round(pc*100,1)}% | "
                 f"{('∞' if lift==float('inf') else round(lift,2))}x | ({nw}/{nc})")

    # 누적 결합: 개별 enrichment 큰 순으로 AND 결합 → 격차 벌어지는가
    finite = [s for s in scored if s[2] != float("inf")]
    finite.sort(key=lambda s: s[2], reverse=True)
    L += ["", "== 누적 결합(개별 enrichment 상위부터 AND) ==",
          "결합축 | 위너통과 | 대조통과 | enrichment | 위너잔존/대조잔존"]
    accum = []
    for nm, g, *_ in finite:
        accum.append((nm, g))

        def allpass(r, ax=accum):
            vs = [gg(r) for _, gg in ax]
            if any(v is None for v in vs):
                return None
            return all(vs)
        pw, nw = rate(W, allpass)
        pc, nc = rate(C, allpass)
        if pw is None or pc is None:
            continue
        lift = (pw / pc) if pc and pc > 0 else float("inf")
        wn = sum(1 for r in W if allpass(r) is True)
        cn = sum(1 for r in C if allpass(r) is True)
        L.append(f"{'+'.join(n.split()[0] for n,_ in accum)} | "
                 f"{round(pw*100,1)}% | {round(pc*100,1)}% | "
                 f"{('∞' if lift==float('inf') else round(lift,2))}x | "
                 f"{wn}/{len(W)} vs {cn}/{len(C)}")

    L += ["",
          "== 정직한 한계 ==",
          f"대조군 n={len(C)}(작음·무작위·시드고정)·둘 다 pivot 측정.",
          "타이밍(앞 검증서 lift≈1)과 분리한 선별축 자체 변별력. 상폐 제외",
          "(생존자)·인-샘플. enrichment>1=위너 농축이지 실거래수익 보장 아님.",
          "결손 축은 통과율 None(추정 안 함). 대조군 확대(30→100)로 강화 예정."]
    block = "\n".join(L)
    OUT.write_text(block, encoding="utf-8")
    print(f"selection-lift saved: {OUT} (winners {len(W)}, control {len(C)})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
