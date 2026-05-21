"""[진단] 메가캡 모멘텀(월간·N=5·top30·1년) -62% 최대낙폭의 *원인*.

거래내역 전수 기록 + 자본곡선 peak→trough→회복 시점 추적 +
MDD 하강기에 *무엇을 들고 있었나* 분석.
"""
import bisect
import json
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE                       # noqa: E402
import analyze_equity_curve_rt as RT                    # noqa: E402
import analyze_doppelganger as AD                       # noqa: E402
import analyze_megatop as MT                            # noqa: E402

OUT = HERE.parents[1] / "research" / "oneil-model-book"


def run_logged(src, n=5, rebal=20, lookback=252, cost=0.0066):
    """megatop.run_method 와 동일 로직 + 거래·보유 풀로그."""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"]) for k, s in U.items()
               if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _ in codes_d.values() for x in d})
    rs0 = al[min(len(al) - 1, 260)]
    end = al[-1]
    axis = [t for t in al if rs0 <= t <= end]
    kd, kc = AE.kospi_series()
    sh = RT.load_shares()

    pos = {}
    cash = 1.0
    eq_d, eq = [], []
    trades = []      # (code, buy_dt, sell_dt, ret%, reason)
    held_log = []    # per-day list of held codes (for MDD inspection)

    for ti, t in enumerate(axis):
        on = not AE.kbear_at(kd, kc, t)
        # 일일 -15%·★스위치
        for code in list(pos):
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i < 0:
                continue
            px = c[i]
            p = pos[code]
            reason = None
            if px <= p["entry"] * 0.85:
                reason = "-15% 손절"
            elif not on:
                reason = "★ 약세 현금화"
            if reason:
                cash += p["inv"] * (px / p["entry"]) * (1 - cost)
                trades.append((code, p["buy_dt"], t,
                               (px / p["entry"] - 1) * 100, reason))
                del pos[code]
        # 월간 리밸런스
        if on and ti % rebal == 0:
            # top-30 by 점별 시총
            cap = []
            for code, (d, c) in codes_d.items():
                j = bisect.bisect_right(d, t) - 1
                if j < lookback or c[j] <= 0:
                    continue
                mc = c[j] * sh.get(code, 0) / 1e8
                if mc > 0:
                    cap.append((mc, code, j, c))
            cap.sort(reverse=True)
            top30 = cap[:30]
            # 1년 모멘텀 랭킹 → top-N
            scored = []
            for _, code, j, c in top30:
                if c[j - lookback] <= 0:
                    continue
                scored.append((c[j] / c[j - lookback] - 1, code, c[j]))
            scored.sort(reverse=True)
            tgt = {code: px for _, code, px in scored[:n]}
            # 이탈 매도
            for code in list(pos):
                if code in tgt:
                    continue
                d, c = codes_d[code]
                i = bisect.bisect_right(d, t) - 1
                px = c[i] if i >= 0 else pos[code]["entry"]
                cash += pos[code]["inv"] * (px / pos[code]["entry"]) \
                    * (1 - cost)
                trades.append((code, pos[code]["buy_dt"], t,
                               (px / pos[code]["entry"] - 1) * 100,
                               "리밸런스 이탈"))
                del pos[code]
            # 신규 매수(등가중)
            slot = max(1, n)
            for code, px in tgt.items():
                if code in pos or cash <= 1e-9:
                    continue
                buy = min(cash, cash / (slot - len(pos)))
                cash -= buy
                pos[code] = {"inv": buy * (1 - cost), "entry": px,
                             "buy_dt": t}
        mv = cash
        for code, p in pos.items():
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq_d.append(t)
        eq.append(mv)
        held_log.append(sorted(pos.keys()))
    return eq_d, eq, trades, held_log


def code_names():
    """FDR 현재 상장목록에서 code→name."""
    import FinanceDataReader as fdr
    nm = {}
    for mk in ("KOSPI", "KOSDAQ"):
        for _, r in fdr.StockListing(mk).iterrows():
            c = str(r.get("Code") or "").zfill(6)
            if c.isdigit() and r.get("Name"):
                nm[c] = r["Name"]
    return nm


def main():
    src = "c2024-12"
    print(f"[진단] {src} 메가캡 모멘텀 N=5·월간·top30·1년·비용0.66%",
          file=sys.stderr)
    ed, eq, trades, held = run_logged(src)
    nm = code_names()

    # MDD 시점 추적
    peak, peak_i, trough_i = eq[0], 0, 0
    cur_peak_i = 0
    mdd = 0.0
    for i, v in enumerate(eq):
        if v >= peak:
            peak = v
            cur_peak_i = i
        dd = v / peak - 1
        if dd < mdd:
            mdd = dd
            trough_i = i
            peak_i = cur_peak_i
    rec_i = trough_i
    for i in range(trough_i + 1, len(eq)):
        if eq[i] >= eq[peak_i]:
            rec_i = i
            break
    else:
        rec_i = len(eq) - 1

    L = [f"[진단] 우리 메가캡 모멘텀 시스템(N=5·월간) {src} 최대낙폭 분석",
         f"전구간 자본: 시작 1.00 → 최고 {eq[peak_i]:.2f} ({ed[peak_i]}) "
         f"→ 최저 {eq[trough_i]:.2f} ({ed[trough_i]}) → 마지막 "
         f"{eq[-1]:.2f} ({ed[-1]})",
         f"최대낙폭 {mdd*100:.0f}% (고점→저점, {ed[peak_i]}→{ed[trough_i]}, "
         f"{trough_i-peak_i}거래일·약 {(trough_i-peak_i)/21:.0f}개월)",
         f"회복까지: {ed[rec_i]} ({rec_i-trough_i}거래일)"
         if eq[rec_i] >= eq[peak_i] else "회복 미완료(데이터 끝까지)",
         "=" * 70]

    # 최악 거래 톱-10
    tr_sorted = sorted(trades, key=lambda x: x[3])
    L += ["■ 최악 손실 거래 톱-10 (전체 {}건 중)".format(len(trades))]
    L.append(f"  {'종목':<14} {'매수':<12}{'매도':<12}{'손익':>8}  사유")
    for code, b, s, r, why in tr_sorted[:10]:
        n_ = (nm.get(code, code) or code)[:12]
        L.append(f"  {n_:<14}({code}) {b}  {s}  {r:+6.0f}%  {why}")

    # MDD 하강기 보유 종목
    L += ["", "■ 최대낙폭 *하강 구간* 보유 종목 빈도",
          f"  ({ed[peak_i]} ~ {ed[trough_i]} 사이 매일 보유했던 코드 집계)"]
    from collections import Counter
    cnt = Counter()
    for i in range(peak_i, trough_i + 1):
        for code in held[i]:
            cnt[code] += 1
    seg_days = trough_i - peak_i + 1
    L.append(f"  {'종목':<14}  보유일/전체  비중")
    for code, days in cnt.most_common(8):
        n_ = (nm.get(code, code) or code)[:12]
        L.append(f"  {n_:<14}({code})  {days}/{seg_days}일  "
                 f"{100*days/seg_days:.0f}%")

    # 그 구간 동안 청산된 거래 손익
    descent_trades = [t for t in trades if peak_i <= 0
                      or (ed[peak_i] <= t[2] <= ed[trough_i])]
    if descent_trades:
        L.append("")
        L.append(f"■ 하강기({ed[peak_i]}~{ed[trough_i]}) 청산 거래 "
                 f"{len(descent_trades)}건 손익")
        ds = sorted(descent_trades, key=lambda x: x[3])
        for code, b, s, r, why in ds[:10]:
            n_ = (nm.get(code, code) or code)[:12]
            L.append(f"  {n_:<14}({code})  {b}→{s}  {r:+6.0f}%  {why}")

    L += ["",
          "해석: 위 종목들이 *그 −62% 하강의 주범*. 한 두 종목이 큰",
          "  비중(1/5=20%)에서 깊게 빠진 게 누적 → 자본 큰 폭 손실.",
          "  단일 종목이 −40% 도달하면 등가중 5종목에선 통장 −8%p,",
          "  여러 종목이 동반 하락하면 합산 -60%+ 가능.",
          "  ★스위치는 코스피<200일선 시 자동 청산 — 그 사이 종목별",
          "  −15% 손절이 어디까지 실제로 발동했는지 사유 컬럼 참고.",
          "한계: 사후·종가·일별·주식수 현재값(소오차)·이름은 현재상장명."]
    txt = "\n".join(L)
    (OUT / "_megatop_mdd_diag.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
