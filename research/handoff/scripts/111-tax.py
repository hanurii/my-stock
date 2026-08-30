# -*- coding: utf-8 -*-
"""111 — **세금을 넣으면 「2 대 2」가 어디로 기우는가** (㉠ · 사용자 물음 2026-08-30)

110 에서 낙폭을 맞춰 붙이니 «2 대 2» 였다. 그런데 세금이 빠져 있었고,
**미너비니가 압도적으로 자주 판다**(27년 매수 9,172 vs 200일선 매도 90).

# 규약 — 한국 «해외주식 양도소득세»
```
세율     22% (지방소득세 포함)
공제     해마다 **250만원**
통산     같은 해 손익만 통산. **이월결손금 공제 없음** → 손실 해는 0원
시점     실현한 해에 낸다
시작금    **1,000만원**   🚨 공제 250만원이 «금액»이라 계좌 크기에 따라 무게가 다르다
```

# 🚨 근사 하나 — 그대로 적는다
```
미너비니는 보유 중앙이 34일이라 **그 해 번 것을 그 해 거의 다 실현한다**
→ 「그 해 계좌 증가분 = 그 해 실현이익」으로 근사한다
→ 연말에 열려 있던 자리만큼 **세금을 «조금 더» 매기는 쪽**이다(미너비니에 불리한 근사)
지수 판은 «정확»하다 — 판 시점의 실현손익을 그대로 센다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r109", HERE / "109-index-stop.py")
r109 = _u.module_from_spec(_t)
_t.loader.exec_module(r109)

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
RATE = 0.22
DEDUCT = 250.0          # 만원
START = 1000.0          # 만원


def tax_on(gain_manwon):
    """그 해 실현이익(만원)에 매기는 세금. 손실이면 0(이월 없음)."""
    g = gain_manwon - DEDUCT
    return max(0.0, g) * RATE


def minervini_after_tax(curve, settle_pct):
    """해마다 계좌 증가분을 실현이익으로 보고 세금을 뗀다(근사)."""
    vals = [(d, v) for d, v in curve] + [(curve[-1][0], 1.0 + settle_pct / 100.0)]
    byy = {}
    for d, v in vals:
        byy[d[:4]] = v
    ys = sorted(byy)
    acct, prev_ratio = START, 1.0
    peak, mdd = START, 0.0
    for y in ys:
        r = byy[y] / prev_ratio          # 그 해 «수익 배수»
        prev_ratio = byy[y]
        before = acct
        acct *= r
        peak = max(peak, acct)
        mdd = min(mdd, acct / peak - 1.0)
        gain = acct - before
        if gain > 0:
            acct -= tax_on(gain)
    return acct, mdd * 100


def index_after_tax(ds, c, mode, cash_rate=2.0, L=1.0, fin=3.0):
    """지수 판 — 판 시점의 실현손익을 «정확히» 센다."""
    n = len(c)
    ma, run_ = [None] * n, []
    for i in range(n):
        run_.append(c[i])
        if len(run_) > 200:
            run_.pop(0)
        ma[i] = (sum(run_) / 200.0) if i >= 199 else None

    acct = START
    inmkt = (mode != "cash")
    basis = c[0]                       # 매입 단가 (지수 «값» 기준)
    units = acct / c[0] if inmkt else 0.0
    cash = 0.0 if inmkt else acct
    yr_gain = {}
    peak, mdd = acct, 0.0
    cd = cash_rate / 100.0 / 252.0
    d_fin = fin / 100.0 / 252.0 * (L - 1.0)
    for i in range(1, n):
        y = ds[i][:4]
        if inmkt:
            acct = units * c[i] + cash
            if L != 1.0:
                acct *= 1.0  # (레버리지는 아래 lev 경로에서만 씀 — 이 함수는 1배 전용)
        else:
            cash *= (1.0 + cd)
            acct = cash
        peak = max(peak, acct)
        mdd = min(mdd, acct / peak - 1.0)
        if mode == "hold":
            continue
        if inmkt and ma[i] is not None and c[i] < ma[i]:
            gain = units * (c[i] - basis)
            yr_gain[y] = yr_gain.get(y, 0.0) + gain
            cash = units * c[i]
            units, inmkt = 0.0, False
        elif (not inmkt) and ma[i] is not None and c[i] > ma[i]:
            units = cash / c[i]
            basis, cash, inmkt = c[i], 0.0, True
        # 연말 정산
        if i + 1 < n and ds[i + 1][:4] != y:
            t = tax_on(yr_gain.get(y, 0.0))
            if t > 0:
                if inmkt:
                    units -= t / c[i]
                else:
                    cash -= t
    # 마지막 — 남은 자리를 «판다»고 보고 과세(그냥 보유가 여기서 한 번 낸다)
    yend = ds[-1][:4]
    if inmkt:
        yr_gain[yend] = yr_gain.get(yend, 0.0) + units * (c[-1] - basis)
        cash = units * c[-1]
        units = 0.0
    t = tax_on(yr_gain.get(yend, 0.0))
    cash -= t
    return cash, mdd * 100


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else r91.N_SEED
    print("=" * 100, flush=True)
    print("111 — **세금을 넣으면 어디로 기우는가** · 한국 해외주식 양도세 22%%·공제 250만원", flush=True)
    print("=" * 100, flush=True)
    print("🚨 근사: 미너비니는 「그 해 계좌 증가분 = 그 해 실현이익」으로 본다", flush=True)
    print("   (보유 중앙 34일 · 연말 열린 자리만큼 «조금 더» 매기는 = 미너비니에 «불리한» 근사)\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    ev, _x, _y = r91.replay(by2)
    rs = r91.sim(ev, n_seed)
    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")

    yrs = 27.4
    rows = []
    # 미너비니
    pre = [(1.0 + x["equity_pct"] / 100.0) * START for x in rs]
    post = [minervini_after_tax(x["curve"], x["equity_pct"]) for x in rs]
    rows.append(("① 미너비니 (손절 −8%)", st.median(pre), st.median(p[0] for p in post),
                 st.median(p[1] for p in post)))
    # 지수
    for nm, ds_, c_, mode in (("② SPY 그냥 보유", dsS, cS, "hold"),
                              ("③ SPY + 200일선", dsS, cS, "ma"),
                              ("④ QQQ 그냥 보유", dsQ, cQ, "hold"),
                              ("⑤ QQQ + 200일선", dsQ, cQ, "ma")):
        r0 = r109.run(ds_, c_, mode, cash_rate=2.0)
        a, md = index_after_tax(ds_, c_, mode)
        rows.append((nm, r0["final"] * START, a, md))

    print("  %-24s %13s %13s %11s %10s"
          % ("", "세금 «전»", "**세금 «후»**", "깎인 비율", "연평균(후)"), flush=True)
    print("  " + "-" * 78, flush=True)
    for nm, a0, a1, md in rows:
        cg = ((a1 / START) ** (1 / yrs) - 1) * 100
        print("  %-24s %10.0f만 %12.0f만 %10.1f%% %+9.2f%%"
              % (nm, a0, a1, 100.0 * (a1 - a0) / a0, cg), flush=True)

    print("\n" + "=" * 100, flush=True)
    print("★ 세금이 «누구를 더» 깎았나 — 그게 이 판의 답이다", flush=True)
    base = rows[0]
    for nm, a0, a1, md in rows[1:]:
        cut_m = 100.0 * (base[2] - base[1]) / base[1]
        cut_i = 100.0 * (a1 - a0) / a0
        print("  %-24s 미너비니 %+.1f%%  vs  이 판 %+.1f%%   →  차 **%+.1f%%p**"
              % (nm, cut_m, cut_i, cut_i - cut_m), flush=True)

    (r91.OUT / "111-tax.json").write_text(
        json.dumps([{"name": n, "pre": a0, "post": a1, "mdd": m} for n, a0, a1, m in rows],
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n🚨 이월결손금 공제가 «없다»고 봤다(해외주식 규약). 손실 해는 0원이다.", flush=True)
    print("🚨 공제 250만원은 «금액»이라 계좌가 커질수록 무게가 줄어든다. 시작 1,000만원 기준이다.",
          flush=True)
    print("\n저장: 111-tax.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
