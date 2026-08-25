# -*- coding: utf-8 -*-
"""`slot_sim_lots` 자기 점검 — **합성 자료 + 손계산**.

왜 합성인가
-----------
실제 경로로 재면 «해결자와 시뮬이 같이 틀렸을 때» 통과한다.
여기서는 답을 **손으로 계산해** 두고 맞춘다 — 코드끼리 맞추지 않는다.

관문 넷
-------
A. 트랜치가 «하나»면 `slot_sim_frac.sim_frac(slots=5, sizing="cash")` 와 같다
B. 트랜치 셋을 다 사면 «손계산»과 같다
C. **현금이 없어 막히면** 안 산 조합으로 «다시 풀린다» — 이게 옛 도구에 없던 것
D. **예약하면 막힘이 0** 이다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/slot_sim_lots_selftest.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slot_sim                                   # noqa: E402
import slot_sim_frac as sf                        # noqa: E402
import slot_sim_lots as sl                        # noqa: E402

slot_sim.FEE_BUY, slot_sim.FEE_SELL = 0.0, 0.002        # 우대수수료
NET = lambda g: (1 + g / 100) * 0.998 * 100 - 100        # noqa: E731  손계산용


def _d(i):
    return "2021-%02d-%02d" % (1 + i // 28, 1 + i % 28)


# ─────────────────────────────────────────────────────────────────────────
# A. 트랜치 하나 = 옛 판과 «같다»
# ─────────────────────────────────────────────────────────────────────────
def make_legs(n=400, seed=7, multileg=True):
    rnd = random.Random(seed)
    ev = []
    for i in range(n):
        e, hold, r = rnd.randrange(0, 300), rnd.randrange(1, 40), rnd.gauss(3, 18)
        if multileg and rnd.random() < 0.45:
            legs = [(_d(e + max(1, hold // 2)), 0.5, 20.0),
                    (_d(e + hold), 0.5, round(r, 2))]
            res = "win"
        else:
            legs = [(_d(e + hold), 1.0, round(r, 2))]
            res = "win" if r > 0 else "loss"
        ev.append({"code": "A%04d" % i, "scan_date": _d(max(0, e - 1)),
                   "pattern": "VCP", "entry_date": _d(e),
                   "resolve_date": _d(e + hold), "legs": legs,
                   "result": res, "stop_frac": 0.08})
    return ev


def gate_a(n_seed=30):
    bad = []
    for multileg in (False, True):
        ev = make_legs(multileg=multileg)
        lots = sl.from_legs(ev)
        for s in range(n_seed):
            a = sf.sim_frac(ev, slots=5, seed=s, sizing="cash")
            b = sl.sim_lots(lots, seed=s, slots=5, risk=0.02, cap=0.20)
            for k in ("equity_pct", "n_filled", "mdd_pct", "win_rate",
                      "max_loss_streak"):
                x, y = a[k], b[k]
                rel = abs(x - y) / max(1e-12, abs(x)) if x else abs(y)
                if rel > 1e-9:
                    bad.append((multileg, s, k, x, y))
    print("A. 트랜치 하나 = sim_frac(5칸·현금제약)   %d판   → **%s**"
          % (2 * n_seed, "통과" if not bad else "🚨 미통과 %d건" % len(bad)))
    for x in bad[:6]:
        print("     ", x)
    return not bad


# ─────────────────────────────────────────────────────────────────────────
# B~D. 트랜치 셋 — 손계산과 맞춘다
# ─────────────────────────────────────────────────────────────────────────
def three():
    """1/3 씩 · +3% · +6% · 목표 = 평균단가 +20%. 네 조합을 미리 다 푼다."""
    epx, a1, a2 = 100.0, 103.0, 106.0
    sched = [("2021-01-10", a1, 1 / 3, 0), ("2021-01-20", a2, 1 / 3, 1)]
    masks = {}
    for m in ((True, True), (True, False), (False, True), (False, False)):
        px = [epx] + [p for p, t in zip((a1, a2), m) if t]
        avg = sum(px) / len(px)
        masks[m] = {"lots": [("2021-01-05", epx, 1 / 3, -1)]
                    + [x for x, t in zip(sched, m) if t],
                    "sched": list(sched),
                    "exits": [("2021-02-10", 1.0, avg * 1.20)],
                    "resolve_date": "2021-02-10", "result": "win"}
    return {"code": "AAA", "scan_date": "2021-01-04", "pattern": "VCP",
            "entry_date": "2021-01-05", "entry_px": epx, "stop_frac": 0.08,
            "shares": (1 / 3, 1 / 3, 1 / 3), "masks": masks}


def hog(i, date="2021-01-06"):
    """현금을 먹는 대조 종목 — 본전에 나간다(수수료만 나감)."""
    return {"code": "B%02d" % i, "scan_date": "2021-01-05", "pattern": "VCP",
            "entry_date": date, "entry_px": 100.0, "stop_frac": 0.08,
            "shares": (1.0,),
            "masks": {(): {"lots": [(date, 100.0, 1.0, -1)], "sched": [],
                           "exits": [("2021-03-01", 1.0, 100.0)],
                           "resolve_date": "2021-03-01", "result": "loss"}}}


def gate_bcd():
    ok = True
    # ── B. 셋 다 산다 ────────────────────────────────────────────────────
    #    자산 1 · 크기 min(1×0.02/0.08, 0.20) = 0.20 · 트랜치 0.20/3 씩
    #    평균 (100+103+106)/3 = 103 · 목표 123.6
    #    123.6/100 = 23.60% · 123.6/103 = **정확히** 20.00% · 123.6/106 = 16.60%
    r = sl.sim_lots([three()], seed=0, slots=5, risk=0.02, cap=0.20)
    exp = 0.20 / 3 * (NET(23.60) + NET(20.00) + NET(16.60)) / 100 * 100
    ok &= abs(r["equity_pct"] - exp) < 1e-9 and r["n_added"] == 2
    print("B. 셋 다 산다        시뮬 %+.8f%% · 손계산 %+.8f%% · 차 %.1e · 증액 %d → **%s**"
          % (r["equity_pct"], exp, abs(r["equity_pct"] - exp), r["n_added"],
             "통과" if abs(r["equity_pct"] - exp) < 1e-9 else "🚨 미통과"))

    # ── C. 현금이 없어 «둘 다» 막힌다 → mask=(False,False) 로 다시 푼다 ──
    #    🚨 현금이 바닥나려면 cap × 슬롯수 > 1 이어야 한다(아니면 항상 딱 맞는다)
    #    01-05 AAA 파일럿 0.30/3 = 0.10 → 현금 0.90
    #    01-06 B 4마리 · 빈칸 4 → 칸당 0.225 → 현금 0
    #    01-10 · 01-20 증액 0.10 필요 > 0 → 둘 다 막힘 → 원가 100 하나만, 목표 120
    ev = [three()] + [hog(i) for i in range(4)]
    KW = dict(seed=0, slots=5, risk=1.0, cap=0.30)
    r2 = sl.sim_lots(ev, reserve=False, **KW)
    exp2 = (0.10 * NET(20.00) / 100 + 4 * 0.225 * NET(0.0) / 100) * 100
    c_ok = r2["n_add_blocked"] == 2 and abs(r2["equity_pct"] - exp2) < 1e-9
    ok &= c_ok
    print("C. 둘 다 막힘        시뮬 %+.8f%% · 손계산 %+.8f%% · 차 %.1e · 막힘 %d → **%s**"
          % (r2["equity_pct"], exp2, abs(r2["equity_pct"] - exp2),
             r2["n_add_blocked"], "통과" if c_ok else "🚨 미통과"))

    #    C′. «한쪽만» 막힌다 → mask=(True,False)
    #    01-15 에 늦은 B 가 남은 현금을 다 먹어 둘째 증액만 막힌다
    #    평균 (100+103)/2 = 101.5 · 목표 121.8 · 121.8/103 = 18.25%
    ev3 = [three()] + [hog(i) for i in range(3)] + [hog(9, "2021-01-15")]
    r3 = sl.sim_lots(ev3, reserve=False, **KW)
    exp3 = (0.10 * (NET(21.80) + NET(18.25)) / 100
            + (3 * 0.225 + 0.125) * NET(0.0) / 100) * 100
    c2_ok = (r3["n_added"] == 1 and r3["n_add_blocked"] == 1
             and abs(r3["equity_pct"] - exp3) < 1e-9)
    ok &= c2_ok
    print("C′ 한쪽만 막힘       시뮬 %+.8f%% · 손계산 %+.8f%% · 차 %.1e · 증액 %d/막힘 %d → **%s**"
          % (r3["equity_pct"], exp3, abs(r3["equity_pct"] - exp3),
             r3["n_added"], r3["n_add_blocked"], "통과" if c2_ok else "🚨 미통과"))

    # ── D. 예약하면 막힘 0 ───────────────────────────────────────────────
    #    🚨 예약도 «칸 몫»을 넘을 수 없다 — cap 0.30 인데 빈칸 5 → 0.20 으로 잘린다
    #    목표 0.20 · 트랜치 0.20/3 · B 는 현금 0.80 을 4칸에 → 0.20 씩
    r4 = sl.sim_lots(ev, reserve=True, **KW)
    exp4 = (0.20 / 3 * (NET(23.60) + NET(20.00) + NET(16.60)) / 100
            + 4 * 0.20 * NET(0.0) / 100) * 100
    d_ok = r4["n_add_blocked"] == 0 and abs(r4["equity_pct"] - exp4) < 1e-9
    ok &= d_ok
    print("D. 예약함            시뮬 %+.8f%% · 손계산 %+.8f%% · 차 %.1e · **막힘 %d** → **%s**"
          % (r4["equity_pct"], exp4, abs(r4["equity_pct"] - exp4),
             r4["n_add_blocked"], "통과" if d_ok else "🚨 미통과"))
    print("   (묶여서 놀린 비중 평균 %.2f%% · 최대 %.2f%%  ← 예약의 «대가»)"
          % (r4["resv_frac_mean"], r4["resv_frac_max"]))
    return ok


def main() -> int:
    print("=" * 84)
    print("slot_sim_lots 자기 점검 — 합성 자료 + 손계산")
    print("=" * 84)
    ok = gate_a()
    ok &= gate_bcd()
    print("\n**%s**" % ("전부 통과" if ok else
                        "🚨 미통과 — 맞추려 하지 말고 «왜»부터 본다"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
