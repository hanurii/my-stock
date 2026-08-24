# -*- coding: utf-8 -*-
"""슬롯5 시뮬레이터 — **분할 청산판**. `slot_sim.py` 를 «건드리지 않고» 확장한다.

왜 따로 만드나
--------------
1회차 변형은 **한 거래를 여러 번에 나눠 판다**(예: +20%에 절반, 나머지는 추격).
정본 `slot_sim.sim()` 은 거래마다 청산이 **한 번**이라고 가정한다.
🚨 **정본을 고치면 0~5회차의 옛 결과가 조용히 바뀐다.** 그래서 새 모듈을 만든다.

거래 dict 에 필요한 키
----------------------
`code` · `scan_date` · `pattern` · `entry_date` · `resolve_date`(**마지막** 다리) ·
`result`(0회차 규약 그대로) · `legs` = [(청산일, 몫, 총수익%), ...]  몫의 합 = 1.0

산술을 정본과 «같게» 맞춘 곳 (양방향 관문의 근거)
--------------------------------------------------
- 진입 시 비중 `eq / slots` — 같다
- 반영 `eq += wg * frac * net(gain) / 100` — **몫이 1.0이면 `wg * 1.0` 은 정확히 `wg`**
  이므로 정본과 **비트 단위로 같다**
- 반영 순서 `(청산일, code)` 정렬 — 같다
- 슬롯은 **마지막 다리**가 끝나야 비고, `reuse='nextday'` 규약도 같다

🚨 **노출은 언제나 100% 이하다** — 진입 때만 `eq/slots` 를 잡고, 부분 청산은
   자본을 **돌려줄** 뿐 더 사지 않는다. 슬롯은 그대로 차 있다.
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict

import slot_sim
from slot_sim import net, order_key      # noqa: F401  (정본 환산식·정렬키를 그대로 쓴다)

SLOTS = slot_sim.SLOTS


def sim_frac(trades, slots: int = SLOTS, seed: int = 0, sizing: str = "canon"):
    """분할 청산 슬롯5 자산곡선. 규약은 정본의 `orderkey` + `nextday` 고정.

    반환: equity_pct · n_filled · win_rate(0회차 규약) · money_win_rate(총수익>0) ·
          mdd_pct · max_loss_streak · exposure_max
    """
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda t: (t["code"], t.get("pattern", ""),
                                     t.get("scan_date", "")))

    dates = sorted(set(list(byday)
                       + [t["resolve_date"] for t in trades]
                       + [d for t in trades for d, _f, _g in t["legs"]]))

    eq = 1.0
    held = []                # [resolve_date, trade, weight, legs_left(list)]
    n = w = mw = 0
    peak, mdd = 1.0, 0.0
    curve = []                # [(날짜, 자산)] — 자료 축 블록 재표집에 쓴다
    streak = best = 0
    expo_max = 0.0

    nomw = {}              # 거래 -> 명목 비중(진입 시점 자산 대비)
    arith = [0.0]          # 🚨 «곱하지 않은» 합 — 산술 예측(분해 표의 왼쪽)
    fills = []             # 체결된 거래의 순수익 — 「체결분 거래당」

    def credit(items):
        """items: [(청산일, code, 비중, 몫, 총수익%)] — 정본과 «같은» 순서·산술."""
        nonlocal eq
        for _d, _c, wg, fr, g, _t in sorted(items, key=lambda x: (x[0], x[1])):
            eq += wg * fr * net(g) / 100
            # 🚨 **명목 비중**으로 더한다 — `wg` 는 «그 시점 자산»에 비례하므로
            #    그대로 더하면 «관측과 항등식»이 되어 격차가 늘 0 이 나온다
            #    (2026-08-24 실제로 0.00%p 가 나와 잡았다).
            arith[0] += nomw.get(id(_t), 0.0) * fr * net(g) / 100

    def close_out(t):
        """마지막 다리까지 끝난 거래의 승패를 센다 (정본의 credit 안 계수부)."""
        nonlocal n, w, mw, streak, best
        n += 1
        fills.append(sum(fr * net(g) for _d, fr, g in t["legs"]))
        is_w = t["result"] == "win"
        w += is_w
        mw += sum(fr * g for _d, fr, g in t["legs"]) > 0
        streak = 0 if is_w else streak + 1
        best = max(best, streak)

    for d in dates:
        # ── 오늘 «이전»에 끝난 다리를 반영한다 (정본 reuse='nextday') ──────
        due = []
        for h in held:
            rest = []
            for leg in h[3]:
                if leg[0] < d:
                    due.append((leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1]))
                else:
                    rest.append(leg)
            h[3] = rest          # 남은 다리만 들고 간다 (제자리 갱신)
        credit(due)
        done = [h for h in held if h[0] < d]
        held = [h for h in held if h[0] >= d]
        # 🚨 **정본과 «같은 순서»로 센다** — `slot_sim.credit` 이 `(청산일, code)` 로
        #    정렬해 연속 손실을 세므로, 여기서 순서가 다르면 `max_loss_streak` 가 어긋난다.
        #    (합성 관문에서 실제로 2 vs 1 로 어긋나 잡았다.)
        for h in sorted(done, key=lambda x: (x[0], x[1]["code"])):
            assert not h[3], "🚨 마지막 다리보다 늦은 다리가 남았다"
            close_out(h[1])

        # ── 빈 슬롯 채우기 ────────────────────────────────────────────────
        free = slots - len(held)
        if d in byday and free > 0:
            # ── 칸 크기 ──────────────────────────────────────────────────
            #   canon : `자산 / 슬롯수`  (**정본** — 그 「자산」에 아직 안 판 칸의
            #           돈이 들어 있어 **없는 돈을 쓴다**. 실측 자유현금 최솟값 −0.1439)
            #   cash  : `min(자산/슬롯수, 가용현금/빈칸수)`  (**집행 가능한 유일한 판**)
            if sizing == "cash":
                open_w = sum(h[2] * sum(fr for _d2, fr, _g2 in h[3]) for h in held)
                per = min(eq / slots, max(0.0, eq - open_w) / free)
            else:
                per = eq / slots
            if per > 0:
                c = sorted(byday[d], key=lambda t: order_key(seed, t))
                for t in c[:free]:
                    nomw[id(t)] = per / eq if eq > 0 else 0.0   # 명목 비중
                    held.append([t["resolve_date"], t, per, list(t["legs"])])
        expo_max = max(expo_max, sum(h[2] for h in held) / eq if eq > 0 else 0.0)
        curve.append((d, eq))   # 자료 축 밴드용 일별 자산
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)

    # ── 남은 보유 정산 ────────────────────────────────────────────────────
    rest = [(leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1]) for h in held for leg in h[3]]
    credit(rest)
    for h in sorted(held, key=lambda x: (x[0], x[1]["code"])):   # 같은 이유로 정렬
        close_out(h[1])
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
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
            "exposure_max": expo_max * 100}


def band(trades, n_runs: int = 200, seed0: int = 0, **kw):
    """seed 밴드 — 정본 `slot_sim.band` 와 같은 자리의 값을 낸다."""
    rs = [sim_frac(trades, seed=s, **kw) for s in range(seed0, seed0 + n_runs)]
    eq = sorted(r["equity_pct"] for r in rs)
    return {"median": st.median(eq), "p5": eq[int(n_runs * .05)],
            "p95": eq[int(n_runs * .95)],
            "mdd": st.median([r["mdd_pct"] for r in rs]),
            "n_filled": st.median([r["n_filled"] for r in rs]),
            "win_rate": st.median([r["win_rate"] for r in rs]),
            "money_win_rate": st.median([r["money_win_rate"] for r in rs]),
            "exposure_max": max(r["exposure_max"] for r in rs)}


def gate_vs_canon(trades, n_seed: int = 20):
    """🚨 **양방향 관문** — 0회차 규약(다리 하나·몫 1.0)에서 정본과 «같은가».

    같지 않으면 변형 숫자를 쓸 수 없다. 다리를 하나로 만든 입력을 넣어 확인한다.
    """
    one = []
    for t in trades:
        assert len(t["legs"]) == 1 and t["legs"][0][1] == 1.0, "관문 입력은 다리 하나여야 한다"
        one.append(t)
    bad = []
    for s in range(n_seed):
        a = sim_frac(one, seed=s)
        b = slot_sim.sim([{**t, "gain": t["legs"][0][2]} for t in one], seed=s)
        for k in ("equity_pct", "n_filled", "win_rate", "mdd_pct", "max_loss_streak"):
            if a[k] != b[k]:
                bad.append((s, k, a[k], b[k]))
    return bad
