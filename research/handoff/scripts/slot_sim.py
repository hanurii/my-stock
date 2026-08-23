# -*- coding: utf-8 -*-
"""슬롯5 시뮬레이터 **정본 v2** — 사양: research/handoff/tasks/SLOT_SIM_SPEC.md

`.cache/bt5y/cmp_exit.py` 의 `sim()` 은 더 이상 정본이 아니다(개정 v2 M3).
그 파일은 이전 결과의 기록이므로 고치지 않는다. 앞으로 모든 슬롯5는 이 모듈만 쓴다.

고친 것 둘
----------
1. **난수 어긋남** — 옛 코드는 `rnd.shuffle` 을 "빈 슬롯이 있고 후보가 있는 날"에만
   불렀다. 청산 규칙이 바뀌면 결착일 → 빈 슬롯 패턴 → 셔플 호출 횟수가 달라져
   난수 스트림이 어긋났다(같은 seed 인데 다른 후보 순서). 여기서는 날짜마다
   `Random((seed, date))` 로 독립 셔플해 **시뮬 경로와 무관**하게 만든다.
2. **같은 날 재진입** — 옛 코드는 결착 처리 직후 그 슬롯을 같은 날 다시 채웠다.
   여기서는 결착한 슬롯을 **다음 거래일부터** 재사용한다.

두 고침은 `rng_mode` · `reuse` 로 켜고 끌 수 있다(검증 관문의 4조합 분해용).
`rng_mode='stream'` + `reuse='sameday'` 는 옛 `sim()` 을 그대로 재현한다.

거래 dict 에 필요한 키: `entry_date` · `resolve_date` · `gain` (총수익 %, 순수익 환산 전)
· `result` ('win' 이면 승) · `code` · `pattern` (기준 정렬용).
"""
from __future__ import annotations

import random
import statistics as st
from collections import defaultdict

SLOTS = 5
FEE_SELL = 0.0034      # 매도 수수료+세금
FEE_BUY = 0.0014       # 매수 수수료


def net(gain_pct: float) -> float:
    """총수익 % → 순수익 % (사전등록 고정 환산식)."""
    return ((1 + gain_pct / 100) * (1 - FEE_SELL) / (1 + FEE_BUY) - 1) * 100


def _byday(trades, base_order: str = "canonical"):
    """진입일별 후보.

    base_order='canonical' : (code, pattern, scan_date) 로 고정 — 입력 순서에
        결과가 좌우되지 않게 하고, 그 위에 셔플을 얹는다. (정본)
    base_order='input'     : 넘어온 순서 그대로 — 옛 `cmp_exit.sim()` 재현용.
    """
    d = defaultdict(list)
    for t in trades:
        d[t["entry_date"]].append(t)
    if base_order == "canonical":
        for k in d:
            d[k].sort(key=lambda t: (t["code"], t.get("pattern", ""),
                                     t.get("scan_date", "")))
    return d


def order_key(seed: int, t) -> float:
    """거래별 정렬키 (SLOT_SIM_SPEC 1-1). 거래마다 자기 난수를 가지므로
    후보 목록에서 몇 건이 빠져도 남은 거래의 상대 순서가 유지된다."""
    return random.Random("%d|%s|%s|%s" % (seed, t["code"], t["scan_date"],
                                          t.get("pattern", ""))).random()


def sim(trades, slots: int = SLOTS, seed: int = 0,
        rng_mode: str = "orderkey", reuse: str = "nextday", order=None,
        base_order: str = "canonical"):
    """슬롯5 자산곡선.

    rng_mode : 'orderkey' = 거래별 정렬키로 순서 결정 (**정본**)
               'perdate'  = 날짜마다 Random("seed|date") 독립 셔플 (구버전)
               'stream'   = 옛 방식(빈 슬롯 있는 날에만 하나의 스트림에서 셔플)
    reuse    : 'nextday' = 결착 슬롯도 손익도 다음 거래일부터 (**정본 ④**)
               'nextday_cash_today' = 슬롯만 다음날, 손익은 결착일 (민감도 ⑤)
               'sameday' = 옛 방식(결착 처리 직후 같은 날 재사용)
    order    : None 이면 셔플 순서 그대로. 함수면 셔플 뒤 `sorted(key=order)` 로
               안정 정렬해 **동점만 무작위**가 되게 한다(정렬 규칙 검정용).

    반환: dict(equity_pct, n_filled, win_rate, mdd_pct, max_loss_streak)
    """
    byday = _byday(trades, base_order)
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in trades]))
    rnd_stream = random.Random(seed)
    eq, held = 1.0, []            # held: [resolve_date, trade, weight, credited]
    n = w = 0
    peak, mdd = 1.0, 0.0
    streak = best_streak = 0
    outcomes = []                 # 결착 순서대로 (resolve_date, is_win)

    def credit(hs):
        nonlocal eq, n, w, streak, best_streak
        for rd, t, wg, _c in sorted(hs, key=lambda h: (h[0], h[1]["code"])):
            eq += wg * net(t["gain"]) / 100
            n += 1
            is_w = t["result"] == "win"
            w += is_w
            outcomes.append((rd, is_w))
            streak = 0 if is_w else streak + 1
            best_streak = max(best_streak, streak)

    for d in dates:
        if reuse == "sameday":
            # 옛 방식: 결착 처리 직후 그 슬롯을 같은 날 다시 채운다
            done = [h for h in held if h[0] <= d]
            held = [h for h in held if h[0] > d]
            credit(done)
        elif reuse == "nextday":
            # 정본: 오늘 결착분은 오늘 슬롯을 계속 차지하고, 손익도 다음 거래일에 반영
            done = [h for h in held if h[0] < d]
            held = [h for h in held if h[0] >= d]
            credit(done)
        else:  # 'nextday_cash_today' — 슬롯만 다음날부터, 손익은 결착일에 반영
            #   사양(SLOT_SIM_SPEC)은 슬롯 재사용 시점만 정하고 현금 반영 시점은
            #   말하지 않는다. 둘을 갈라 보기 위한 조합.
            credit([h for h in held if h[0] <= d and not h[3]])
            for h in held:
                if h[0] <= d:
                    h[3] = True
            held = [h for h in held if h[0] >= d]

        free = slots - len(held)
        if d in byday:
            c = byday[d][:]
            if rng_mode == "orderkey":
                c.sort(key=lambda t: order_key(seed, t))
            elif rng_mode == "perdate":
                # 구버전. 파이썬 3.12 는 튜플 seed 를 안 받아 문자열 "seed|날짜" 로 준다.
                random.Random("%d|%s" % (seed, d)).shuffle(c)
            else:
                if free > 0:
                    rnd_stream.shuffle(c)
            if order is not None:
                c = sorted(c, key=order)
            if free > 0:
                for t in c[:free]:
                    held.append([t["resolve_date"], t, eq / slots, False])
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)

    credit([h for h in held if not h[3]])        # 남은 보유 정산
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    return {"equity_pct": (eq - 1) * 100, "n_filled": n,
            "win_rate": (w / n * 100 if n else 0.0),
            "mdd_pct": mdd * 100, "max_loss_streak": best_streak}


def band(trades, n_runs: int = 200, **kw):
    """수준 추정 — 무작위 순서 n_runs 회. 중앙값과 5~95% 밴드."""
    rs = [sim(trades, seed=i, **kw) for i in range(n_runs)]
    eqs = sorted(r["equity_pct"] for r in rs)
    lo, hi = eqs[max(0, n_runs // 20 - 1)], eqs[min(n_runs - 1, n_runs - n_runs // 20)]
    return {
        "median": st.median(eqs), "p5": lo, "p95": hi,
        "n_filled": st.median(r["n_filled"] for r in rs),
        "win_rate": st.median(r["win_rate"] for r in rs),
        "mdd": st.median(r["mdd_pct"] for r in rs),
        "loss_streak": st.median(r["max_loss_streak"] for r in rs),
        "runs": n_runs,
    }


def paired(a_trades, b_trades, n_runs: int = 400, **kw):
    """같은 seed 짝비교 — A 가 B 를 이긴 비율과 차이 분포.
    rng_mode='orderkey' 라서 후보 구성이 달라져도 두 규칙이 같은 상대 순서를 본다."""
    diffs = []
    for i in range(n_runs):
        a = sim(a_trades, seed=i, **kw)["equity_pct"]
        b = sim(b_trades, seed=i, **kw)["equity_pct"]
        diffs.append(a - b)
    diffs_sorted = sorted(diffs)
    return {
        "win_rate_pct": sum(1 for x in diffs if x > 0) / n_runs * 100,
        "diff_median": st.median(diffs),
        "diff_p5": diffs_sorted[max(0, n_runs // 20 - 1)],
        "diff_p95": diffs_sorted[min(n_runs - 1, n_runs - n_runs // 20)],
        "runs": n_runs,
    }
