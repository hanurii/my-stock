# -*- coding: utf-8 -*-
"""점진적 노출 시뮬레이터 — **3회차용**. 포지션이 «두 번에 나눠» 들어간다.

무엇이 처음인가
---------------
0~2회차: 한 포지션은 **한 번에** 들어가고 여러 번 나올 수 있었다.
3회차:   **들어가는 것도 나뉜다.** 파일럿 → (오르면) 증액.
🚨 **자본이 «두 시점»에 나간다.** 현금 제약이 있는 판에서는 그게 결과를 바꾼다 —
   증액 시점에 현금이 없으면 **증액을 못 한다.** 그 사실을 세어 보고한다.

거래 dict 에 필요한 키
----------------------
`code` · `scan_date` · `pattern` · `entry_date` · `entry_px` · `stop_frac` ·
`add` = (증액일, 증액가) 또는 None · `exits` = [(청산일, 몫, 청산가)] · `resolve_date` · `result`
**`몫`은 «포지션 전체» 기준**(트랜치별이 아니다). 트랜치마다 «취득가»가 다르므로
수익률은 시뮬 안에서 트랜치별로 계산한다.

🚨 **양방향 관문**: `pilot=1.0`(전량 한 번에) 이면 **`slot_sim_size` 와 같아야** 한다.
   같지 않으면 이 모듈을 쓸 수 없다.
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict

import slot_sim
from slot_sim import net, order_key      # noqa: F401


def sim_pyr(trades, risk=0.0125, cap=0.25, seed=0, pilot=0.5,
            use_cash=True, partial=False, size_scale=None, date_scale=None,
            max_positions=None, cash_rule="seq"):
    """점진적 노출. `pilot` = 처음 넣는 몫(1.0 이면 2회차와 같다).

    `size_scale(t, state)` 가 주어지면 목표 크기에 곱한다(3c 의 「연속 손실이면 절반」).
    """
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda x: (x["code"], x.get("pattern", ""), x.get("scan_date", "")))
    adds = defaultdict(list)             # 증액일 -> [거래]
    for t in trades:
        if t.get("add"):
            adds[t["add"][0]].append(t)

    dates = sorted(set(list(byday) + list(adds)
                       + [t["resolve_date"] for t in trades]
                       + [d for t in trades for d, _f, _p in t["exits"]]))

    eq = 1.0
    held = {}            # id(t) -> {"t":t, "w":[(취득가, 비중)], "left":[남은 exits]}
    n = w = mw = 0
    peak, mdd = 1.0, 0.0
    streak = best = 0
    curve, conc = [], []
    cash_floor = 1e9
    nomw, arith, fills = {}, [0.0], []
    n_blocked_cash = n_add_blocked = n_added = 0
    overrun = []
    recent = []          # 최근 청산 결과 (3c 용)
    fill_log = []        # 🚨 체결 내역 — (키, 목표비중, 실제비중, 진입일, 결착일)
                         #    「어느 거래가 자본을 받았나」를 재려면 이게 있어야 한다

    def credit(items):
        nonlocal eq
        # 🚨 정렬 키에 «거래 dict» 가 들어가면 비교 불가로 터진다 — code 로 정렬한다
        for _d, _code, _c, tw, fr, px in sorted(items, key=lambda x: (x[0], x[1])):
            for epx_i, w_i in tw:
                g = px / epx_i * 100 - 100
                eq += w_i * fr * net(round(g, 2)) / 100
                arith[0] += nomw.get(id(_c), 0.0) * (w_i / max(1e-12, sum(x[1] for x in tw))) \
                    * fr * net(round(g, 2)) / 100

    def close_out(t, tw):
        nonlocal n, w, mw, streak, best
        n += 1
        tot = sum(x[1] for x in tw)
        r = sum(fr * net(round(px / epx_i * 100 - 100, 2)) * (w_i / max(1e-12, tot))
                for _d, fr, px in t["exits"] for epx_i, w_i in tw)
        fills.append(r)
        is_w = t["result"] == "win"
        w += is_w
        mw += r > 0
        streak = 0 if is_w else streak + 1
        best = max(best, streak)
        recent.append(r > 0)
        del recent[:-5]

    for d in dates:
        # ── 오늘 «이전»에 난 청산을 반영 ─────────────────────────────────
        due, done = [], []
        for k, h in list(held.items()):
            rest = []
            for ex in h["left"]:
                if ex[0] < d:
                    due.append((ex[0], h["t"]["code"], h["t"], h["w"], ex[1], ex[2]))
                else:
                    rest.append(ex)
            h["left"] = rest
            if h["t"]["resolve_date"] < d:
                done.append(k)
        credit(due)
        for k in sorted(done, key=lambda k: (held[k]["t"]["resolve_date"], held[k]["t"]["code"])):
            close_out(held[k]["t"], held[k]["w"])
            del held[k]

        open_w = sum(w_i * sum(fr for _d2, fr, _p in h["left"])
                     for h in held.values() for _e, w_i in h["w"])
        cash = eq - open_w
        cash_floor = min(cash_floor, cash)

        # ── 증액 ─────────────────────────────────────────────────────────
        for t in adds.get(d, ()):
            h = held.get(id(t))
            if h is None or h.get("added"):
                continue
            w2 = h["target"] * (1.0 - pilot)
            if w2 > cash + 1e-12:
                n_add_blocked += 1
                h["added"] = True
                continue
            h["w"].append((t["add"][1], w2))
            h["added"] = True
            cash -= w2
            n_added += 1

        # ── 새 진입 (파일럿) ─────────────────────────────────────────────
        if d in byday:
            # 🚨 `slot_sim_size` 와 «같은» 칸/현금 규약을 쓴다 (2026-08-25 추가)
            #    이게 없으면 5칸 20% 판을 재현하지 못한다 — 73번에서 관문이 깨졌다.
            _free = (max_positions - len(held)) if max_positions else None
            _share = (max(0.0, cash) / _free) if (cash_rule == "per_slot" and _free) else None
            for t in sorted(byday[d], key=lambda x: order_key(seed, x)):
                if max_positions is not None and len(held) >= max_positions:
                    break
                sf_ = t.get("stop_frac") or 0.10
                # 🚨 국면 상한(4c)은 «날짜»에 걸린다 — 스캔일 기준으로 넘겨받는다
                # 🚨 국면 상한(4c)은 «날짜»에 걸린다 — 스캔일 기준으로 넘겨받는다
                _s1 = size_scale(recent) if size_scale else 1.0
                _s2 = date_scale(t.get('scan_date')) if date_scale else 1.0
                scale = _s1 * _s2
                lim = min(eq * risk / sf_, eq * cap) * scale
                w1 = lim * pilot
                _avail = cash if _share is None else min(cash, _share)
                if use_cash and (not partial) and w1 > _avail + 1e-12:
                    n_blocked_cash += 1
                    continue
                if use_cash:
                    w1 = min(w1, _avail)
                if w1 <= 1e-12:
                    n_blocked_cash += 1
                    continue
                nomw[id(t)] = lim / eq if eq > 0 else 0.0
                held[id(t)] = {"t": t, "w": [(t["entry_px"], w1)],
                               "left": list(t["exits"]), "target": lim}
                fill_log.append(((t["scan_date"], t["code"], t["pattern"]),
                                 lim, w1, t["entry_date"], t["resolve_date"]))
                cash -= w1
                g0 = t["exits"][0][2] / t["entry_px"] * 100 - 100
                if t["result"] in ("loss", "ambiguous") and g0 < -sf_ * 100:
                    overrun.append((-g0 - sf_ * 100) * lim / eq)
        conc.append(len(held))
        curve.append((d, eq))
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)

    rest = [(ex[0], h["t"]["code"], h["t"], h["w"], ex[1], ex[2])
            for h in held.values() for ex in h["left"]]
    credit(rest)
    for k in sorted(held, key=lambda k: (held[k]["t"]["resolve_date"], held[k]["t"]["code"])):
        close_out(held[k]["t"], held[k]["w"])
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    cc = sorted(conc)
    m = len(cc)
    return {"curve": curve, "fill_log": fill_log, "equity_pct": (eq - 1) * 100, "n_filled": n,
            "arith_pct": arith[0] * 100,
            "filled_per_trade": (st.mean(fills) if fills else 0.0),
            "win_rate": (w / n * 100 if n else 0.0),
            "money_win_rate": (mw / n * 100 if n else 0.0),
            "mdd_pct": mdd * 100, "max_loss_streak": best,
            "cash_floor": cash_floor, "blocked_cash": n_blocked_cash,
            "n_added": n_added, "n_add_blocked": n_add_blocked,
            "nom_w_mean": (st.mean(nomw.values()) if nomw else 0.0),
            "conc_mean": st.mean(cc) if cc else 0.0,
            "conc_p10": cc[m // 10] if cc else 0, "conc_median": cc[m // 2] if cc else 0,
            "conc_p90": cc[9 * m // 10] if cc else 0, "conc_max": cc[-1] if cc else 0,
            "risk_overrun_mean": (st.mean(overrun) if overrun else 0.0),
            "risk_overrun_n": len(overrun)}


def band(trades, n_runs: int = 200, seed0: int = 0, **kw):
    rs = [sim_pyr(trades, seed=s, **kw) for s in range(seed0, seed0 + n_runs)]
    eq = sorted(r["equity_pct"] for r in rs)
    out = {"median": st.median(eq), "p5": eq[int(n_runs * .05)],
           "p95": eq[int(n_runs * .95)]}
    for k in ("mdd_pct", "n_filled", "win_rate", "money_win_rate", "arith_pct",
              "filled_per_trade", "conc_mean", "conc_median", "conc_p10", "conc_p90",
              "risk_overrun_mean", "n_added", "n_add_blocked", "blocked_cash"):
        out[k.replace("_pct", "")] = st.median([r[k] for r in rs])
    out["conc_max"] = max(r["conc_max"] for r in rs)
    out["cash_floor"] = min(r["cash_floor"] for r in rs)
    return out
