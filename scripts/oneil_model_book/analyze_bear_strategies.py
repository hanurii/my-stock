"""[약세장 전략 비교] 2022-2024 약세/횡보 구간에서 어떤 답이 좋나.

5가지 + 1 비교:
  A. 100% 현금 + 예금 3.5%/년
  B. KOSPI 매수보유 (그냥 두기)
  C. 우리 메가캡 시스템 (★OFF면 자동 현금)
  D. 친구분 top-10 EW 연간 재조정
  E. KODEX 인버스(114800) 매수보유 — 약세장 풀 노출
  ★F. 하이브리드: ★OFF면 인버스, ★ON이면 우리 시스템 — 양방향
"""
import bisect, json, sys
from datetime import datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE
import analyze_equity_curve_rt as RT
import analyze_megatop as MT
import analyze_top10_friend as TF
import FinanceDataReader as fdr

OUT = HERE.parents[1] / "research" / "oneil-model-book"
START, END = "2022-01-03", "2024-11-29"


def mdd_of(eq):
    p, m = eq[0], 0
    for v in eq:
        p = max(p, v)
        m = min(m, v / p - 1)
    return m * 100


def cash_strategy(rate=0.035):
    """예금 연 rate% 복리."""
    yr = (datetime.strptime(END, "%Y-%m-%d")
          - datetime.strptime(START, "%Y-%m-%d")).days / 365.25
    return (1 + rate) ** yr, yr


def kospi_strategy():
    kd, kc = AE.kospi_series()
    bh = AE.kospi_bh(kd, kc, START, END)
    return bh[1][-1], mdd_of(bh[1])


def inverse_strategy(code="114800"):
    df = fdr.DataReader(code, START, END)
    if df.empty:
        return None, None
    eq = [v / df["Close"].iloc[0] for v in df["Close"]]
    return eq[-1], mdd_of(eq)


def system_strategy():
    """우리 메가캡 시스템 (KOSPI 전용·N=5·월간·−10%/−20%/★)."""
    ed, eq, tr = MT.run_method("c2024-12", "A", 5, 0.0066,
                                top_k=30, rebal_step=20, lookback=252,
                                markets={'KOSPI'}, stop_pct=-0.10,
                                trail_pct=-0.20,
                                window=(START, END))
    return eq[-1], mdd_of(eq)


def friend_strategy():
    ed, eq = TF.top10_friend("c2024-12", markets={'KOSPI'})
    # window 자르기
    idx = [i for i, d in enumerate(ed) if START <= d <= END]
    if not idx:
        return None, None
    eq2 = [eq[i] / eq[idx[0]] for i in idx]
    return eq2[-1], mdd_of(eq2)


def hybrid_strategy(cost=0.0066):
    """★OFF=인버스, ★ON=우리 시스템."""
    kd, kc = AE.kospi_series()
    inv_df = fdr.DataReader("114800", START, END)
    inv_d = [d.strftime("%Y-%m-%d") for d in inv_df.index]
    inv_c = list(inv_df["Close"])

    # 우리 시스템 일별 자본 곡선 추출
    ed_sys, eq_sys, _ = MT.run_method("c2024-12", "A", 5, 0.0066,
                                       top_k=30, rebal_step=20, lookback=252,
                                       markets={'KOSPI'}, stop_pct=-0.10,
                                       trail_pct=-0.20,
                                       window=(START, END))
    # 일별 시스템 수익률
    sys_ret = {ed_sys[i]: eq_sys[i] / eq_sys[i - 1]
               for i in range(1, len(ed_sys)) if eq_sys[i - 1] > 0}
    # 일별 인버스 수익률
    inv_ret = {inv_d[i]: inv_c[i] / inv_c[i - 1]
               for i in range(1, len(inv_d)) if inv_c[i - 1] > 0}

    axis = sorted(set(ed_sys) | set(inv_d))
    axis = [t for t in axis if START <= t <= END]
    eq = [1.0]
    mode = None                            # None | 'sys' | 'inv'
    for i, t in enumerate(axis[1:], 1):
        on = not AE.kbear_at(kd, kc, t)
        new_mode = "sys" if on else "inv"
        if mode is None:
            mode = new_mode
        elif mode != new_mode:
            # 전환 비용
            eq[-1] *= (1 - cost)
            mode = new_mode
        if mode == "sys" and t in sys_ret:
            eq.append(eq[-1] * sys_ret[t])
        elif mode == "inv" and t in inv_ret:
            eq.append(eq[-1] * inv_ret[t])
        else:
            eq.append(eq[-1])
    return eq[-1], mdd_of(eq)


def main():
    yr = (datetime.strptime(END, "%Y-%m-%d")
          - datetime.strptime(START, "%Y-%m-%d")).days / 365.25
    print(f"[약세장 전략 비교] {START} ~ {END} ({yr:.1f}년)\n" + "=" * 64)
    print(f"  {'전략':<28}{'최종 ×':<10}{'연수익':<10}{'최대손실':<10}")

    rows = [
        ("A. 100% 현금 (예금 3.5%)", *cash_strategy()),
        ("B. KOSPI 매수보유", *kospi_strategy()),
        ("C. 우리 메가캡 시스템", *system_strategy()),
        ("D. 친구분 top-10 EW 연간", *friend_strategy()),
        ("E. KODEX 인버스 매수보유", *inverse_strategy()),
        ("★F. 하이브리드 (★OFF=인버스/ON=시스템)", *hybrid_strategy()),
    ]
    for nm, final, mdd in rows:
        if final is None:
            print(f"  {nm:<28}결손")
            continue
        cagr = (final ** (1 / yr) - 1) * 100 if yr > 0 and final > 0 else 0
        mdd_str = f"{mdd:.0f}%" if mdd is not None else "—"
        print(f"  {nm:<28}×{final:.2f}     {cagr:+.0f}%       {mdd_str}")
    print()
    print("해석은 별도 평이한 정리로.")


if __name__ == "__main__":
    main()
