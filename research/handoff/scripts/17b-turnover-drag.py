# -*- coding: utf-8 -*-
"""17b — 슬롯 점유율 **직접 측정** + 복리 차이 **분해**.

17번에서 점유율을 `체결수 × 평균보유일 ÷ (슬롯 × 거래일)`로 추정했더니 **104.6%**가 나왔다.
**5칸뿐인 슬롯이 100%를 넘을 수 없다** — 추정식이 틀렸다(전체 3,776건의 평균 보유일을
체결된 424건에 곱했고, 마지막 거래의 결착이 구간 밖으로 넘어간다).
→ **시뮬 안에서 슬롯-일을 직접 센다.**

복리 차이도 셋으로 나눈다:
  ① **분산 손실** — `Π(1+xᵢ/5) ≤ (1+평균/5)^n` 은 산술·기하평균 부등식이라 **수학적 확실성**이다
  ② **슬롯 유휴** — 빈 칸이 노는 동안 복리가 안 돈다
  ③ **나머지** — 순서 효과·자본 변동에 따른 배분 크기 변화

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/17b-turnover-drag.py
"""
from __future__ import annotations

import bisect
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
SLOTS = 5
TARGET, STOP = 20.0, 10.0
FEES = {"현행 왕복0.482%": (0.0014, 0.0034),
        "우대 왕복0.207%": (0.000034, 0.002034)}


def make_net(buy, sell):
    K = (1 - sell) / (1 + buy)
    return lambda g: ((1 + g / 100) * K - 1) * 100


def load():
    rows = []
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            e = p["entry_price"]
            h, l, c, dts = p["h"], p["l"], p["c"], p["dates"]
            n = len(c)
            rmax, rmin = [], []
            mh, ml = -1e30, 1e30
            for i in range(n):
                mh = max(mh, h[i])
                ml = min(ml, l[i])
                rmax.append(mh)
                rmin.append(-ml)
            ti = bisect.bisect_left(rmax, e * (1 + TARGET / 100))
            si = bisect.bisect_left(rmin, -(e * (1 - STOP / 100)))
            ti = ti if ti < n else None
            si = si if si < n else None
            if ti is None and si is None:
                i, why = n - 1, "last_close"
            elif si is None:
                i, why = ti, "target"
            elif ti is None:
                i, why = si, "stop"
            elif ti < si:
                i, why = ti, "target"
            elif si < ti:
                i, why = si, "stop"
            else:
                i, why = ti, "both_same_day"
            rows.append({"code": p["code"], "pattern": p["pattern"],
                         "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                         "resolve_date": dts[i], "gain": (c[i] / e - 1) * 100,
                         "days": i, "year": p["entry_date"][:4], "reason": why,
                         "result": ("win" if why == "target" else
                                    "loss" if why in ("stop", "both_same_day")
                                    else ("win" if c[i] > e else "loss"))})
    return rows


def sim_occupancy(trades, dates, pos_of, seed):
    """정본 ④ 규칙으로 돌면서 **슬롯-일 점유**와 체결 거래를 그대로 센다."""
    from collections import defaultdict
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for d in byday:
        byday[d].sort(key=lambda t: (t["code"], t["pattern"], t["scan_date"]))
    order = {d: sorted(v, key=lambda t: slot_sim.order_key(seed, t))
             for d, v in byday.items()}
    held, filled, occ = [], [], 0
    for i, d in enumerate(dates):
        held = [h for h in held if h[0] >= i]
        free = SLOTS - len(held)
        c = order.get(d)
        if c and free > 0:
            for t in c[:free]:
                held.append([pos_of[t["resolve_date"]], t])
                filled.append(t)
        occ += len(held)                 # 그날 점유된 칸 수
    return {"n_filled": len(filled), "slot_days_used": occ,
            "slot_days_avail": SLOTS * len(dates), "filled": filled}


def main():
    tr = load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    print("거래 %d건 · 거래일 %d일" % (len(tr), len(dates)), flush=True)

    print("\n═══ C · 슬롯 점유율 (시뮬에서 직접) ═══", flush=True)
    runs = [sim_occupancy(tr, dates, pos_of, s) for s in range(20)]
    occ = st.median(r["slot_days_used"] for r in runs)
    av = runs[0]["slot_days_avail"]
    nf = st.median(r["n_filled"] for r in runs)
    hd = sorted(t["days"] + 1 for t in runs[0]["filled"])
    print("  거래일 %d × 슬롯 %d = **슬롯-일 %d** · 실제 점유 **%.0f** → **점유율 %.1f%%**"
          % (len(dates), SLOTS, av, occ, occ / av * 100), flush=True)
    print("  체결 %.0f건 · **체결분 보유일수** 중앙 **%.0f일** · 평균 %.1f일 · P90 %.0f일"
          % (nf, st.median(hd), st.mean(hd), hd[int(len(hd) * .9)]), flush=True)
    print("  → 한 칸이 한 바퀴 도는 데 **%.1f거래일** (= 점유 슬롯-일 ÷ 체결수 %.1f + 유휴)"
          % (av / nf, occ / nf), flush=True)
    print("  → **빈 칸이 %.1f%%의 시간 동안 논다.**" % (100 - occ / av * 100), flush=True)
    res = {"n_trading_days": len(dates), "slot_days_avail": av,
           "slot_days_used": occ, "occupancy_pct": occ / av * 100,
           "n_filled": nf, "hold_median": st.median(hd), "hold_mean": st.mean(hd),
           "hold_p90": hd[int(len(hd) * .9)], "cycle_days": av / nf,
           "busy_days_per_trade": occ / nf}

    print("\n═══ B-2 · 복리 차이 분해 ═══", flush=True)
    res["decomp"] = {}
    for nm, f in FEES.items():
        netf = make_net(*f)
        slot_sim.net = netf
        eqs = sorted(slot_sim.sim(tr, seed=s)["equity_pct"] for s in range(N_SEED))
        actual = st.median(eqs)
        # 한 seed 의 실제 체결 순서로 ①②③ 분해
        gaps = []
        for s in range(20):
            r = sim_occupancy(tr, dates, pos_of, s)
            xs = [netf(t["gain"]) / SLOTS / 100 for t in r["filled"]]
            n = len(xs)
            m = st.mean(xs)
            naive = (1 + m) ** n - 1
            geo = 1.0
            for x in xs:
                geo *= (1 + x)
            gaps.append((naive * 100, (geo - 1) * 100))
        nv = st.median(g[0] for g in gaps)
        gm = st.median(g[1] for g in gaps)
        res["decomp"][nm] = {"naive": nv, "geometric": gm, "actual_slot5": actual,
                             "variance_drag": gm - nv, "rest": actual - gm}
        print("  %-16s ① 순진한 복리 **%+.1f%%** → ② 실제 곱 **%+.1f%%** "
              "(**분산 손실 %+.1f%%p**) → ③ 슬롯5 실제 **%+.1f%%** (나머지 %+.1f%%p)"
              % (nm, nv, gm, gm - nv, actual, actual - gm), flush=True)
    print("  ※ ①→② 는 산술·기하평균 부등식이라 **반드시 음수**다(수학적 확실성).", flush=True)
    print("  ※ ②→③ 은 **슬롯 유휴 · 자본 변동에 따른 배분 크기 · 순서**가 섞인 값이다.", flush=True)

    (OUT / "17b-turnover-drag.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/17b-turnover-drag.json")


if __name__ == "__main__":
    main()
