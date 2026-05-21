"""[메가캡 모멘텀 견고성 검증] 베스트 구성(N=3·top30·주간·1년·비용
0.66%·1년1등모멘텀) 주변을 흔들어 결과가 *튼튼한가* 측정.

흔드는 축:
  ① 비용: 0.66 / 1.0 / 1.5 / 2.0%
  ② 종목수 N: 2 / 3 / 5 / 7 / 10
  ③ 리밸런스: 주간(5d) / 격주(10d) / 월간(20d)
  ④ 모멘텀 기간: 6개월(126d) / 9개월(189d) / 1년(252d)
  ⑤ 유니버스: top-20 / 30 / 50
  ⑥ 분기 안정성: 각 사이클을 반으로 잘라 *두 토막 모두* 이기나
  ⑦ 베스트 구성의 드로다운·최장수중·최악거래 프로파일

판정: 어떤 축을 흔들어도 KOSPI를 *대체로* 이기면 견고. 한 축에서
무너지면 그 축이 약점(라이브 전 보강 필요). 사후·종가·일별·n=2·
주식수=현재단일값. 모든 비교는 강세장(★ON) 한정 vs KOSPI.

사용: python scripts/oneil_model_book/analyze_megatop_robust.py
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
import analyze_megatop as MT                            # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"

CYCLES = ["c2024-12", "c2020-03"]
KOSPI_REF = {"c2024-12": 57.0, "c2020-03": 47.0}        # 강세장 KOSPI %
BASE = dict(method="A", n=3, cost=0.0066, top_k=30,
            rebal_step=5, lookback=252)


def bull_chain(ed, eq, kd, kc):
    ks = [kc[max(0, bisect.bisect_right(kd, x) - 1)] for x in ed]
    bl = [RT.bull_on(kd, kc, x) for x in ed]

    def ch(s):
        v = 1.0
        for i in range(1, len(s)):
            if bl[i] and s[i - 1] > 0:
                v *= s[i] / s[i - 1]
        return v
    bd = sum(1 for i in range(1, len(bl)) if bl[i])
    yb = bd / 252

    def cg(x):
        return (x ** (1 / yb) - 1) * 100 if yb > 0 and x > 0 else 0
    return cg(ch(eq)), cg(ch(ks))


def mdd_metrics(eq):
    peak, mdd, uw, uw_max = eq[0], 0.0, 0, 0
    for v in eq:
        if v >= peak:
            peak = v
            uw = 0
        else:
            uw += 1
            uw_max = max(uw_max, uw)
        mdd = min(mdd, v / peak - 1)
    return mdd * 100, uw_max


def go(cid, **overrides):
    """베이스 + overrides 로 1회 실행, 강세장 시스템·KOSPI·MDD 반환."""
    cfg = {**BASE, **overrides}
    kd, kc = AE.kospi_series()
    ed, eq, tr = MT.run_method(cid, cfg["method"], cfg["n"], cfg["cost"],
                               top_k=cfg["top_k"],
                               rebal_step=cfg["rebal_step"],
                               lookback=cfg["lookback"],
                               window=overrides.get("window"))
    sCg, kCg = bull_chain(ed, eq, kd, kc)
    m = AE.metrics(ed, eq)
    mdd, uw = mdd_metrics(eq)
    return {"final": m["final"], "bull_sys": sCg, "bull_kospi": kCg,
            "mdd": mdd, "uw_max": uw, "trades": len(tr),
            "worst_trade": (100 * min(tr)) if tr else 0,
            "win_rate": (100 * sum(1 for x in tr if x > 0) / len(tr)
                         if tr else 0)}


def sweep(cid, label, axis_name, values, key, fmt="{}"):
    """한 축을 흔들어 표 한 줄씩 누적."""
    L = [f"■ {label} — {axis_name} 민감도 ({cid})"]
    L.append(f"  {axis_name:<10}| 강세장 시스템 vs KOSPI · 격차 | "
             "전 ×배 | MDD | 거래")
    for v in values:
        r = go(cid, **{key: v})
        gap = r["bull_sys"] - r["bull_kospi"]
        L.append(f"  {fmt.format(v):<10}| 시{r['bull_sys']:+5.0f}% "
                 f"vs K{r['bull_kospi']:+5.0f}% · {gap:+5.0f}%p | "
                 f"×{r['final']:.2f} | {r['mdd']:.0f}% | {r['trades']}")
    return L


def half_periods(cid):
    """사이클을 강세장 거래일 기준 절반으로 분할."""
    kd, kc = AE.kospi_series()
    U = MT.AD.pick_universe_file(cid)
    codes_d = {k: (s["d"], s["c"]) for k, s in U.items()
               if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _ in codes_d.values() for x in d})
    rs0 = al[min(len(al) - 1, 260)]
    end = al[-1]
    days = [t for t in al if rs0 <= t <= end]
    mid = days[len(days) // 2]
    return (rs0, mid), (mid, end)


def main():
    L = ["[메가캡 모멘텀 견고성 검증] 베스트=N3·top30·주간·1년·"
         "비용0.66%·1년1등모멘텀(A)",
         "한 축씩 흔들어 KOSPI(c2024 +57%·c2020 +47%) 상회 유지하나.",
         "*강세장 한정·look-ahead 無·n=2·주식수 현재단일.*",
         "=" * 70]
    for cid in CYCLES:
        base = go(cid)
        L += [f"\n>>> {cid}  (베이스 강세장 {base['bull_sys']:+.0f}% vs "
              f"KOSPI {base['bull_kospi']:+.0f}%, ×{base['final']:.2f}, "
              f"MDD {base['mdd']:.0f}%, 거래 {base['trades']}, "
              f"승률 {base['win_rate']:.0f}%, 최악거래 "
              f"{base['worst_trade']:+.0f}%)",
              "-" * 70]
        L += sweep(cid, "①비용", "비용%",
                   [0.0066, 0.010, 0.015, 0.020], "cost", "{:.3%}")
        L += sweep(cid, "②종목수 N", "N",
                   [2, 3, 5, 7, 10], "n", "{}")
        # ③~⑥ 은 L2 에서
    # ③ 리밸런스 별도 처리(라벨)
    L2 = []
    for cid in CYCLES:
        L2 += [f"\n>>> {cid} (재실행 — 리밸런스/기간/유니버스 축)",
               "-" * 70]
        # 리밸런스
        L2.append("■ ③리밸런스 주기 민감도")
        L2.append("  주기      | 시스템 vs KOSPI | 격차 | ×배 | MDD | 거래")
        for step, nm in [(5, "주간(5d)"), (10, "격주(10d)"),
                         (20, "월간(20d)")]:
            r = go(cid, rebal_step=step)
            L2.append(f"  {nm:<10}| 시{r['bull_sys']:+5.0f}% vs "
                      f"K{r['bull_kospi']:+5.0f}% | "
                      f"{r['bull_sys']-r['bull_kospi']:+5.0f}%p | "
                      f"×{r['final']:.2f} | {r['mdd']:.0f}% | "
                      f"{r['trades']}")
        # ④ 모멘텀 기간
        L2.append("■ ④모멘텀 룩백 민감도")
        L2.append("  룩백      | 시스템 vs KOSPI | 격차 | ×배 | MDD")
        for lb, nm in [(126, "6개월"), (189, "9개월"), (252, "1년(베이스)")]:
            r = go(cid, lookback=lb)
            L2.append(f"  {nm:<10}| 시{r['bull_sys']:+5.0f}% vs "
                      f"K{r['bull_kospi']:+5.0f}% | "
                      f"{r['bull_sys']-r['bull_kospi']:+5.0f}%p | "
                      f"×{r['final']:.2f} | {r['mdd']:.0f}%")
        # ⑤ 유니버스
        L2.append("■ ⑤유니버스(시총 상위 K) 민감도")
        L2.append("  K         | 시스템 vs KOSPI | 격차 | ×배 | MDD")
        for k in [20, 30, 50]:
            r = go(cid, top_k=k)
            L2.append(f"  top-{k:<7}| 시{r['bull_sys']:+5.0f}% vs "
                      f"K{r['bull_kospi']:+5.0f}% | "
                      f"{r['bull_sys']-r['bull_kospi']:+5.0f}%p | "
                      f"×{r['final']:.2f} | {r['mdd']:.0f}%")
        # ⑥ 분기 안정성
        L2.append("■ ⑥분기 안정성(사이클 반으로 분할)")
        L2.append("  구간      | 시스템 vs KOSPI | 격차 | 거래")
        h1, h2 = half_periods(cid)
        for w, nm in [(h1, "전반부"), (h2, "후반부")]:
            r = go(cid, window=w)
            L2.append(f"  {nm:<10}| 시{r['bull_sys']:+5.0f}% vs "
                      f"K{r['bull_kospi']:+5.0f}% | "
                      f"{r['bull_sys']-r['bull_kospi']:+5.0f}%p | "
                      f"{r['trades']}")

    # 두 사이클 베이스 비교 + 판정
    bases = {c: go(c) for c in CYCLES}
    verdict = []
    for cid in CYCLES:
        gap = bases[cid]['bull_sys'] - bases[cid]['bull_kospi']
        verdict.append(f"  {cid}: 베이스 {gap:+.0f}%p, MDD "
                       f"{bases[cid]['mdd']:.0f}%, 최악거래 "
                       f"{bases[cid]['worst_trade']:+.0f}%")
    L = L + L2 + ["\n" + "=" * 70, "■ 종합", *verdict,
                  "해석: ①~⑤ 어느 축을 흔들어도 *대체로* 양(陽)의 격차",
                  "유지면 견고. 한 축에서 KOSPI 미달로 무너지면 거기가",
                  "약점·라이브 전 보강 필요(예: 비용 1.5%↑에서 무너지면",
                  "실거래 슬리피지 정밀화 필수). ⑥ 두 토막 다 이기면",
                  "한 구간 운빨 아님 확정. MDD 40%+ 면 N=3 집중 리스크",
                  "현실화 — 라이브 시 N=5 또는 변동성타깃이 더 안전.",
                  "한계: 사후·종가·일별·n=2·주식수 현재단일값·c2020 수급",
                  "결손은 외인강도 축에만 영향(여기 안 씀)."]
    txt = "\n".join(L)
    (OUT / "_megatop_robust.txt").write_text(txt, encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 메가캡 모멘텀 견고성 검증\n\n```\n{txt}\n```\n")
    print(txt)


if __name__ == "__main__":
    main()
