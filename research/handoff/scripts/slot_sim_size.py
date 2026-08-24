# -*- coding: utf-8 -*-
"""포지션 크기 시뮬레이터 — **2회차용**. 슬롯 고정이 아니라 «위험 기반»이다.

무엇이 다른가
-------------
0~1회차: **칸 다섯 개**. 크기는 자본을 나눈 값.
2회차:   **칸 수가 정해져 있지 않다.** 크기를 «위험»에서 정하고, **현금이 차면 멈춘다.**
```
포지션 크기 = min( 위험목표 ÷ 손절폭 , 상한 , 가용현금 )
총 노출 <= 100%  ·  자본이 차면 새 진입 없음
```
예: 위험 1.25% · 손절 −8% → `0.0125 / 0.08 = 15.6%` → 동시 보유 **~6.4개**

🚨 **양방향 관문** — `위험/손절 = 20%` 이고 `상한 = 20%` 면 칸 크기가 `자산/5` 로 고정되고
   현금이 다섯 칸에서 정확히 바닥나므로 **`slot_sim_frac` 의 «현금제약판»과 같아야 한다.**
   같지 않으면 이 모듈을 쓸 수 없다.

거래 dict 키: `slot_sim_frac` 과 같다(`legs` 포함) + `stop_frac`(손절폭, 양수 소수).

⚠️ **위험목표는 「손절선까지 갔을 때 잃는 돈」이지 「실제로 잃는 돈」이 아니다.**
   갭다운이면 손절선보다 아래에서 나가므로 **실제 손실은 위험목표를 넘는다.**
   그 초과분을 이 모듈이 «잰다»(`risk_overrun`).
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict

import slot_sim
from slot_sim import net, order_key      # noqa: F401


def sim_size(trades, risk=0.0125, cap=0.25, seed=0, max_positions=None,
             use_cash=True):
    """위험 기반 포지션 크기. 반환에 **동시 보유 수 분포**를 함께 낸다."""
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda x: (x["code"], x.get("pattern", ""), x.get("scan_date", "")))
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in trades]
                       + [d for t in trades for d, _f, _g in t["legs"]]))

    eq = 1.0
    held = []                 # [resolve_date, trade, weight, legs_left]
    n = w = mw = 0
    peak, mdd = 1.0, 0.0
    curve = []                # [(날짜, 자산)] — 자료 축 블록 재표집에 쓴다
    streak = best = 0
    conc = []                 # 날마다의 동시 보유 수
    cash_floor = 1e9
    overrun = []              # 위험목표 초과분 (%p)
    n_blocked_cash = 0

    def credit(items):
        nonlocal eq
        for _d, _c, wg, fr, g in sorted(items, key=lambda x: (x[0], x[1])):
            eq += wg * fr * net(g) / 100

    def close_out(t):
        nonlocal n, w, mw, streak, best
        n += 1
        is_w = t["result"] == "win"
        w += is_w
        mw += sum(fr * g for _d, fr, g in t["legs"]) > 0
        streak = 0 if is_w else streak + 1
        best = max(best, streak)

    for d in dates:
        due = []
        for h in held:
            rest = []
            for leg in h[3]:
                if leg[0] < d:
                    due.append((leg[0], h[1]["code"], h[2], leg[1], leg[2]))
                else:
                    rest.append(leg)
            h[3] = rest
        credit(due)
        done = [h for h in held if h[0] < d]
        held = [h for h in held if h[0] >= d]
        for h in sorted(done, key=lambda x: (x[0], x[1]["code"])):
            close_out(h[1])

        open_w = sum(h[2] * sum(fr for _d2, fr, _g2 in h[3]) for h in held)
        cash = eq - open_w
        cash_floor = min(cash_floor, cash)

        if d in byday:
            for t in sorted(byday[d], key=lambda x: order_key(seed, x)):
                if max_positions is not None and len(held) >= max_positions:
                    break
                sf_ = t.get("stop_frac") or 0.10
                # use_cash=True  : **집행 가능한 판** — 현금이 없으면 못 산다
                # use_cash=False : **정본과 같은 성질의 판** — 현금을 안 보고 산다
                #                  (0~1회차 정본이 그랬다. 비교를 위해 남긴다)
                per = (min(eq * risk / sf_, eq * cap, cash) if use_cash
                       else min(eq * risk / sf_, eq * cap))
                if per <= 1e-12:            # 🚨 현금이 없으면 «새 진입 없음»
                    n_blocked_cash += 1
                    continue
                held.append([t["resolve_date"], t, per, list(t["legs"])])
                cash -= per
                # 위험목표 초과 — 손절선보다 아래에서 나간 몫
                g0 = t["legs"][0][2]
                if t["result"] in ("loss", "ambiguous") and g0 < -sf_ * 100:
                    overrun.append((-g0 - sf_ * 100) * per / eq)
        conc.append(len(held))
        curve.append((d, eq))   # 자료 축 밴드용 일별 자산
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)

    rest = [(leg[0], h[1]["code"], h[2], leg[1], leg[2]) for h in held for leg in h[3]]
    credit(rest)
    for h in sorted(held, key=lambda x: (x[0], x[1]["code"])):
        close_out(h[1])
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    cc = sorted(conc)
    m = len(cc)
    return {"curve": curve, "equity_pct": (eq - 1) * 100, "n_filled": n,
            "win_rate": (w / n * 100 if n else 0.0),
            "money_win_rate": (mw / n * 100 if n else 0.0),
            "mdd_pct": mdd * 100, "max_loss_streak": best,
            "cash_floor": cash_floor, "blocked_cash": n_blocked_cash,
            "conc_mean": st.mean(cc) if cc else 0.0,
            "conc_p10": cc[m // 10] if cc else 0, "conc_median": cc[m // 2] if cc else 0,
            "conc_p90": cc[9 * m // 10] if cc else 0, "conc_max": cc[-1] if cc else 0,
            "risk_overrun_mean": (st.mean(overrun) * 100 if overrun else 0.0),
            "risk_overrun_n": len(overrun)}


def band(trades, n_runs: int = 200, seed0: int = 0, **kw):
    rs = [sim_size(trades, seed=s, **kw) for s in range(seed0, seed0 + n_runs)]
    eq = sorted(r["equity_pct"] for r in rs)
    return {"median": st.median(eq), "p5": eq[int(n_runs * .05)],
            "p95": eq[int(n_runs * .95)],
            "mdd": st.median([r["mdd_pct"] for r in rs]),
            "n_filled": st.median([r["n_filled"] for r in rs]),
            "win_rate": st.median([r["win_rate"] for r in rs]),
            "money_win_rate": st.median([r["money_win_rate"] for r in rs]),
            "cash_floor": min(r["cash_floor"] for r in rs),
            "blocked_cash": st.median([r["blocked_cash"] for r in rs]),
            "conc_mean": st.mean([r["conc_mean"] for r in rs]),
            "conc_p10": st.median([r["conc_p10"] for r in rs]),
            "conc_median": st.median([r["conc_median"] for r in rs]),
            "conc_p90": st.median([r["conc_p90"] for r in rs]),
            "conc_max": max(r["conc_max"] for r in rs),
            "risk_overrun_mean": st.mean([r["risk_overrun_mean"] for r in rs]),
            "risk_overrun_n": st.median([r["risk_overrun_n"] for r in rs])}


def gate_vs_slot5(trades, n_seed: int = 20):
    """🚨 **양방향 관문** — `위험/손절 = 20%` · `상한 20%` 면 «현금제약 슬롯5»와 같아야 한다.

    같은 크기 규약이 되도록 모든 거래에 `stop_frac = 0.10` 을 주고 `risk = 0.02` 를 쓴다
    (`0.02 / 0.10 = 0.20`). 상한도 0.20. 그러면 칸 크기가 `min(자산*0.2, 현금)` 이 되어
    `slot_sim_frac(sizing='cash')` 와 같은 규칙이다.
    """
    import slot_sim_frac as sf
    tt = [{**t, "stop_frac": 0.10} for t in trades]
    bad = []
    for s in range(n_seed):
        a = sim_size(tt, risk=0.02, cap=0.20, seed=s, max_positions=5)
        b = sf.sim_frac(trades, seed=s, sizing="cash")
        for k in ("equity_pct", "n_filled", "win_rate", "mdd_pct", "max_loss_streak"):
            if a[k] != b[k]:
                bad.append((s, k, a[k], b[k]))
    return bad
