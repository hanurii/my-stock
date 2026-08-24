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
             use_cash=True, cash_rule="seq", partial=True):
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

    nomw = {}              # 거래 -> 명목 비중(진입 시점 자산 대비)
    arith = [0.0]          # 🚨 «곱하지 않은» 합 — 산술 예측(분해 표의 왼쪽)
    fills = []             # 체결된 거래의 순수익 — 「체결분 거래당」

    def credit(items):
        nonlocal eq
        for _d, _c, wg, fr, g, _t in sorted(items, key=lambda x: (x[0], x[1])):
            eq += wg * fr * net(g) / 100
            # 🚨 **명목 비중**으로 더한다 — `wg` 는 «그 시점 자산»에 비례하므로
            #    그대로 더하면 «관측과 항등식»이 되어 격차가 늘 0 이 나온다
            #    (2026-08-24 실제로 0.00%p 가 나와 잡았다).
            arith[0] += nomw.get(id(_t), 0.0) * fr * net(g) / 100

    def close_out(t):
        nonlocal n, w, mw, streak, best
        n += 1
        fills.append(sum(fr * net(g) for _d, fr, g in t["legs"]))
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
                    due.append((leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1]))
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
            # 🚨 **현금 규칙이 두 가지다. 섞으면 안 된다.**
            #   seq      : `min(위험/손절, 상한, 남은현금)` — 먼저 온 것이 다 가져갈 수 있다
            #              **2회차 사양(`min(..., 가용현금)`)이 이것이다.** 칸 수가 안 정해져
            #              있으므로 「빈칸수로 나눈다」가 정의되지 않는다.
            #   per_slot : `min(..., 가용현금 / 빈칸수)` — `slot_sim_frac` 의 현금제약판과 «같은» 규칙.
            #              **양방향 관문에만 쓴다.**
            #   ⚠️ 2026-08-24: 관문을 seq 로 걸어 «실패»했는데, 그건 버그가 아니라
            #      **서로 다른 두 규칙을 마주 세운 내 설계 오류**였다.
            _free = (max_positions - len(held)) if max_positions else None
            _share = (max(0.0, cash) / _free) if (cash_rule == "per_slot" and _free) else None
            for t in sorted(byday[d], key=lambda x: order_key(seed, x)):
                if max_positions is not None and len(held) >= max_positions:
                    break
                sf_ = t.get("stop_frac") or 0.10
                # use_cash=True  : **집행 가능한 판** — 현금이 없으면 못 산다
                # use_cash=False : **정본과 같은 성질의 판** — 현금을 안 보고 산다
                #                  (0~1회차 정본이 그랬다. 비교를 위해 남긴다)
                lim = min(eq * risk / sf_, eq * cap)
                if not use_cash:
                    per = lim
                elif cash_rule == "per_slot":
                    per = min(lim, _share if _share is not None else cash)
                else:
                    per = min(lim, cash)
                # 🚨 **사양 모호점**: 현금이 목표 크기보다 «적을» 때 쪼개서 잡는가?
                #    partial=True  : 남은 현금만큼 잡는다 → 작은 포지션이 쌓여 동시 보유가 는다
                #    partial=False : **목표 크기를 못 채우면 «안 잡는다»**
                #                    (「자본이 차면 새 진입 없음」의 문자 그대로)
                #    실측 차이가 크다 — 동시 보유 중앙 13 vs 예측 6.4.
                if not partial and per < lim - 1e-12:
                    n_blocked_cash += 1
                    continue
                if per <= 1e-12:            # 🚨 현금이 없으면 «새 진입 없음»
                    n_blocked_cash += 1
                    continue
                nomw[id(t)] = per / eq if eq > 0 else 0.0       # 명목 비중
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

    rest = [(leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1]) for h in held for leg in h[3]]
    credit(rest)
    for h in sorted(held, key=lambda x: (x[0], x[1]["code"])):
        close_out(h[1])
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    cc = sorted(conc)
    m = len(cc)
    import statistics as _st
    return {"curve": curve, "equity_pct": (eq - 1) * 100, "n_filled": n,
            "arith_pct": arith[0] * 100,
            # 🚨 «실제 명목 비중» 분포 — 41번 회계(0.20 고정)와의 차이를 만드는 값
            "nom_w_mean": (_st.mean(nomw.values()) if nomw else 0.0),
            "nom_w_median": (_st.median(nomw.values()) if nomw else 0.0),
            "nom_w_p10": (sorted(nomw.values())[len(nomw)//10] if nomw else 0.0),
            "nom_w_p90": (sorted(nomw.values())[9*len(nomw)//10] if nomw else 0.0),
            "nom_w_lt20": (100.0 * sum(1 for v in nomw.values() if v < 0.1999)
                           / len(nomw) if nomw else 0.0),
            "filled_per_trade": (_st.mean(fills) if fills else 0.0),
            "win_rate": (w / n * 100 if n else 0.0),
            "money_win_rate": (mw / n * 100 if n else 0.0),
            "mdd_pct": mdd * 100, "max_loss_streak": best,
            "cash_floor": cash_floor, "blocked_cash": n_blocked_cash,
            "conc_mean": st.mean(cc) if cc else 0.0,
            "conc_p10": cc[m // 10] if cc else 0, "conc_median": cc[m // 2] if cc else 0,
            "conc_p90": cc[9 * m // 10] if cc else 0, "conc_max": cc[-1] if cc else 0,
            # 🚨 단위: (초과 %p) × (포지션 비중) = **이미 «자산 대비 %p»**.
            #    예전엔 여기 ×100 이 더 붙어 있어 100배로 보고됐다(2026-08-24 정정).
            "risk_overrun_mean": (st.mean(overrun) if overrun else 0.0),
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
    # 🚨 **비트 단위 동일은 «불가능»하다.** 칸 크기를 한쪽은 `eq / 5`, 다른 쪽은
    #    `eq * 0.02 / 0.10` 으로 만든다 — 수학적으로 같지만 **부동소수점 경로가 다르다.**
    #    그래서 «상대 오차» 로 잰다. 문턱 1e-9 는 float 누적(1e-14 수준)보다 5자리 위다.
    #    **관문을 느슨하게 하는 게 아니라, 잴 수 있는 자로 바꾸는 것이다.**
    TOL = 1e-9
    bad, worst = [], 0.0
    for s in range(n_seed):
        a = sim_size(tt, risk=0.02, cap=0.20, seed=s, max_positions=5,
                     cash_rule="per_slot")   # 🚨 관문은 «같은 현금 규칙»으로 세운다
        b = sf.sim_frac(trades, seed=s, sizing="cash")
        for k in ("equity_pct", "n_filled", "win_rate", "mdd_pct", "max_loss_streak"):
            x, y = a[k], b[k]
            rel = abs(x - y) / max(1e-12, abs(y))
            worst = max(worst, rel)
            if rel > TOL:
                bad.append((s, k, x, y, rel))
    return bad, worst
