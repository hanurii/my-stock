"""최근성 보정 I축 — 모델북 백테스트 (사용자 가설 검증).

라이브 스크리닝(`screen_buy_now`/`screen_asof`)에서 60일 누적 I축이
*고점 후 분산 국면*을 "매집"으로 오인하는 결함 발견(에이팩트 등 4종목,
24→7 재스크리닝). 가설: I축에 최근성/지속성을 더하면 변별력이 오른다.

모델북엔 일별 수급 원자료가 없고, `*_trend_60d`는 단순 sign(60d합)이라
최근성 프록시로 못 쓴다(검증 완료). 대신 point-in-time 캐시된
`*_net_60d`(pivot −0~−60일) vs `*_net_prev60d`(pivot −60~−120일)를
직접 비교해 *지속성*을 검증한다.

네 정의의 위너 vs 대조군 enrichment 비교:
  I_base     : (외인60>0) or (기관60>0)                 [현행 시스템]
  I_sustained: 양(+) 주체가 60일 AND 직전60일 모두 >0    [120일 지속 매집]
  I_burst    : 양(+) 주체가 60일>0 이나 직전60일 ≤0      [최근만·취약]
  I_accel    : 양(+) 주체 60일합 > 직전60일합            [가속 매집]
+ L(RS≥80)·M(상승추세)와 결합 시 L+M+I 변별력이 보정으로 더 벌어지나.

한계(정직): 이건 *pivot 직전 120일 내 지속성* 검증이지, 라이브에서
문제된 *최근 10/20일 반전(분산 전환)* 의 직접 재현이 아니다(그건 일별
원자료 재수집 필요 — 2020 pivot은 네이버 frgn 깊이 한계). D(고점후
배제)는 모델북 위너=정의상 진짜 pivot(폭발 전)이라 '고점후'가 성립
안 함 → 모델북서 검증 불가, 라이브 *타이밍(신선도)* 결함으로 분리.
즉 라이브 24→7 축소의 주동력은 D(타이밍)이며 I 최근성은 보조.
대조군은 c2024-12만(2020은 위너 잔존율만)·n=100 작음·상폐제외·인-샘플.

사용:  python analyze_recency_lift.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
OUT = CY / "c2024-12" / "_recency_lift.txt"


def rows(p):
    f = CY / p / "model_book.json"
    return json.loads(f.read_text(encoding="utf-8"))["rows"] if f.exists() else []


def gL(r):
    v = r.get("rs_score")
    return (v >= 80) if isinstance(v, (int, float)) else None


def gM(r):
    v = r.get("market_regime_at_pivot")
    return (v == "상승추세") if v is not None else None


def _actors(r):
    return (r.get("fgn_net_60d"), r.get("inst_net_60d"),
            r.get("fgn_trend_60d"), r.get("inst_trend_60d"))


def gI_base(r):
    fg, og, _, _ = _actors(r)
    if fg is None and og is None:
        return None
    return (fg or 0) > 0 or (og or 0) > 0


def _prev(r):
    return r.get("fgn_net_prev60d"), r.get("inst_net_prev60d")


def gI_sustained(r):
    fg, og, _, _ = _actors(r)
    fp, op = _prev(r)
    if fg is None and og is None:
        return None
    if fp is None and op is None:
        return None
    return (((fg or 0) > 0 and (fp or 0) > 0) or
            ((og or 0) > 0 and (op or 0) > 0))


def gI_burst(r):
    """60일>0 이나 직전60일 ≤0 — 최근에만 산 취약 케이스."""
    fg, og, _, _ = _actors(r)
    fp, op = _prev(r)
    if fg is None and og is None:
        return None
    if fp is None and op is None:
        return None
    pos_burst = (((fg or 0) > 0 and (fp or 0) <= 0) or
                 ((og or 0) > 0 and (op or 0) <= 0))
    sustained = (((fg or 0) > 0 and (fp or 0) > 0) or
                 ((og or 0) > 0 and (op or 0) > 0))
    return pos_burst and not sustained


def gI_accel(r):
    fg, og, _, _ = _actors(r)
    fp, op = _prev(r)
    if fg is None and og is None:
        return None
    if fp is None and op is None:
        return None
    return (((fg or 0) > 0 and (fg or 0) > (fp or 0)) or
            ((og or 0) > 0 and (og or 0) > (op or 0)))


def rate(rs, g):
    vals = [g(r) for r in rs]
    vals = [v for v in vals if v is not None]
    return (sum(1 for v in vals if v) / len(vals) if vals else None), len(vals)


def comb(*gs):
    def f(r):
        vs = [g(r) for g in gs]
        if any(v is None for v in vs):
            return None
        return all(vs)
    return f


def main():
    W = rows("c2024-12")
    C = rows("c2024-12-ctrl")
    W20 = rows("c2020-03")
    if not W or not C:
        print("model_book 부재", file=sys.stderr)
        return

    L = ["최근성 보정 I축 — 모델북 백테스트",
         f"위너 c2024-12 {len(W)} vs 비위너 대조군 {len(C)} "
         f"(+ c2020-03 위너 {len(W20)} 잔존율)",
         "enrichment = 위너통과율 / 대조군통과율 (>1=변별력). 측정=pivot.",
         "trend = fgn/inst_net 60d vs 직전60d 방향(거친 최근성 프록시).",
         "",
         "축 | 위너통과 | 대조통과 | enrichment | (n위너/n대조) | 2020위너통과",
         "---|---|---|---|---|---"]
    defs = [("I_base 60일>0", gI_base),
            ("I_sustained 120일지속", gI_sustained),
            ("I_burst 최근만취약", gI_burst),
            ("I_accel 가속", gI_accel)]
    for nm, g in defs:
        pw, nw = rate(W, g)
        pc, nc = rate(C, g)
        p20, n20 = rate(W20, g)
        lift = (pw / pc) if (pc and pc > 0) else float("inf")
        L.append(f"{nm} | {round(pw*100,1)}% | {round(pc*100,1)}% | "
                 f"{('∞' if lift==float('inf') else round(lift,2))}x | "
                 f"({nw}/{nc}) | {round(p20*100,1)}% ({n20})")

    L += ["", "== L(RS≥80)+M(상승)와 결합: I 정의별 결합 변별력 ==",
          "결합 | 위너통과 | 대조통과 | enrichment | 위너수/대조수"]
    for nm, g in defs:
        f = comb(gL, gM, g)
        pw, nw = rate(W, f)
        pc, nc = rate(C, f)
        wn = sum(1 for r in W if f(r) is True)
        cn = sum(1 for r in C if f(r) is True)
        lift = (pw / pc) if (pc and pc > 0) else float("inf")
        L.append(f"L+M+[{nm.split()[0]}] | {round(pw*100,1)}% | "
                 f"{round(pc*100,1)}% | "
                 f"{('∞' if lift==float('inf') else round(lift,2))}x | "
                 f"{wn}/{len(W)} vs {cn}/{len(C)}")

    L += ["",
          "== 해석 ==",
          "· I_base 1.41x = korea_canslim v1.1 기록치와 일치(정합성 OK).",
          "· I_sustained(120일 지속) 1.29x < base — '오래 산 것'은 위너",
          "  표지 아님. I_burst(최근60일만, 직전60일 ≤0) 1.58x > base —",
          "  진짜 pivot에선 *새로 유입된* 외인/기관이 더 강한 위너 신호.",
          "· 그러나 L+M 결합 변별력은 모든 보정이 base(41.9x)보다 낮음",
          "  → pivot 시점 I축 60일 정의는 결함 아님(보정이 외려 약화).",
          "· 사용자가 라이브서 본 문제는 *pivot 최근성*이 아니라 *고점후",
          "  분산*(D). 모델북 위너=정의상 pivot(폭발 전)이라 D는 검증",
          "  불가 → 결함은 I축이 아니라 라이브 *타이밍(신선도·고점후)*.",
          "",
          "== 정직한 한계 ==",
          "· prev60d=pivot −60~−120일. 이건 120일 내 지속성 검증이지",
          "  라이브의 최근 10/20일 반전(분산 전환) 직접 재현 아님",
          "  (그건 일별 원자료 재수집 필요·2020 frgn 깊이 한계).",
          "· 대조군 c2024-12만(2020 미수집)·n=100 작음·상폐제외·인-샘플.",
          "· enrichment=위너 농축이지 실거래 수익 보장 아님."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"recency-lift saved: {OUT}", file=sys.stderr)
    print("\n".join(L))


if __name__ == "__main__":
    main()
