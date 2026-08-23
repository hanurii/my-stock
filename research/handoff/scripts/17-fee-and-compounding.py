# -*- coding: utf-8 -*-
"""17 — 우대수수료 전환과 복리 (사용자 질문 둘).

질문 ① 실제 수수료는 **우대(왕복 0.207%)**인데 우리는 **0.482%**로 재 왔다.
질문 ② **"+20/−10을 여러 번 반복하면 복리로 지수를 이기지 않나"**

★ 비용은 **곱셈 상수**다 — `순수익 = (1+총수익/100) × K − 1`, `K = (1−매도) / (1+매수)`.
  · 현행 K = 0.995207 (왕복 0.482%) · **우대 K = 0.997932 (왕복 0.207%)**
  · **비율 K_우대 / K_현행 = 1.002738**
  → **모든 거래의 순수익이 (1+총수익/100) × 0.2725%p 만큼 올라가고,
     모든 "차이"(A−B)는 정확히 1.002738배가 된다.**
     **즉 상대 비교는 사실상 안 바뀌고 절대 수준만 움직인다.** (아래 D절에서 수치로 확인)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/17-fee-and-compounding.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import bisect
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
YEARS_LEN = 5.55                      # 2021-02-01 ~ 2026-08-21
SLOTS = 5
TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
SLIPS = [0.0, 0.5, 1.0]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
FEES = {"현행 왕복0.482%": (0.0014, 0.0034),
        "우대 왕복0.207%": (0.000034, 0.002034)}


def K_of(buy, sell):
    return (1 - sell) / (1 + buy)


def make_net(buy, sell):
    K = K_of(buy, sell)
    return lambda g: ((1 + g / 100) * K - 1) * 100


def load_paths():
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
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rmin.append(-ml)
            rows.append({"code": p["code"], "pattern": p["pattern"],
                         "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                         "year": p["entry_date"][:4], "e": e, "c": c, "dts": dts,
                         "rmax": rmax, "rmin": rmin, "n": n})
    return rows


def resolve(r, tg, sp):
    e, n = r["e"], r["n"]
    ti = bisect.bisect_left(r["rmax"], e * (1 + tg / 100))
    ti = ti if ti < n else None
    si = None
    if sp is not None:
        si = bisect.bisect_left(r["rmin"], -(e * (1 - sp / 100)))
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
    return {"resolve_date": r["dts"][i], "gain": (r["c"][i] / e - 1) * 100,
            "reason": why, "days": i}


def trades_of(rows, tg, sp, slip=0.0):
    out = []
    for r in rows:
        v = resolve(r, tg, sp)
        g = v["gain"] - (slip if v["reason"] == "stop" else 0.0)
        out.append({"code": r["code"], "pattern": r["pattern"],
                    "scan_date": r["scan_date"], "entry_date": r["entry_date"],
                    "resolve_date": v["resolve_date"], "gain": g, "year": r["year"],
                    "days": v["days"], "reason": v["reason"],
                    "result": ("win" if v["reason"] == "target" else
                               "loss" if v["reason"] in ("stop", "both_same_day")
                               else ("win" if g > 0 else "loss"))})
    return out


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def absolute(tr, netf, nm):
    n = [netf(t["gain"]) for t in tr]
    W = [x for x in n if x > 0]
    L = [x for x in n if x <= 0]
    wr = len(W) / len(n) * 100
    w, l = st.mean(W), st.mean(L)
    be = (-l) / (w - l) * 100
    print("  %-16s 승률 %.2f%% · 평균승 %+.3f · 평균패 %+.3f · 본전 %.2f%% · "
          "**여유 %+.2f%%p** · 거래당 %+.4f%%p"
          % (nm, wr, w, l, be, wr - be, st.mean(n)), flush=True)
    return {"win_rate": wr, "mean_win": w, "mean_loss": l, "breakeven": be,
            "margin": wr - be, "per_trade": st.mean(n)}


def slot5(tr, netf, nm):
    slot_sim.net = netf
    rs = [slot_sim.sim(tr, seed=s) for s in range(N_SEED)]
    eqs = sorted(r["equity_pct"] for r in rs)
    lo, hi = band(eqs)
    med = st.median(eqs)
    fills = st.median(r["n_filled"] for r in rs)
    mdd = st.median(r["mdd_pct"] for r in rs)
    key = lambda t: abs(netf(t["gain"]))
    e5 = st.median(slot_sim.sim(sorted(tr, key=key)[:-5], seed=s)["equity_pct"]
                   for s in range(N_SEED))
    yr = {}
    for y in YS:
        sub = [t for t in tr if t["year"] != y]
        yr[y] = st.median(slot_sim.sim(sub, seed=s)["equity_pct"] for s in range(50))
    print("  %-16s 중앙 %+8.1f%% · 5~95%% %+7.1f ~ %+7.1f (폭 %6.1f) · 최대낙폭 %+6.1f%% · "
          "체결 %4.0f · 상위5제거 %+8.1f%%"
          % (nm, med, lo, hi, hi - lo, mdd, fills, e5), flush=True)
    print("       한 해 제거: %s" % {k: round(v, 1) for k, v in yr.items()}, flush=True)
    return {"median": med, "band": [lo, hi], "band_width": hi - lo, "mdd": mdd,
            "n_filled": fills, "drop_top5": e5, "drop_year": yr}


def main():
    print("경로 적재 …", flush=True)
    rows = load_paths()
    base = trades_of(rows, 20, 10)
    print("거래 %d건" % len(base), flush=True)
    res = {"n": len(base), "fees": {k: {"buy": v[0], "sell": v[1], "K": K_of(*v),
                                        "roundtrip_pct": (1 / K_of(*v) - 1) * 100}
                                    for k, v in FEES.items()},
           "K_ratio": K_of(*FEES["우대 왕복0.207%"]) / K_of(*FEES["현행 왕복0.482%"])}

    print("\n═══ A · 절대 성적 (비용 두 판) ═══", flush=True)
    res["absolute"] = {nm: absolute(base, make_net(*f), nm) for nm, f in FEES.items()}

    print("\n═══ B · 슬롯5 자산곡선 (%d seed) ═══" % N_SEED, flush=True)
    res["slot5"] = {nm: slot5(base, make_net(*f), nm) for nm, f in FEES.items()}

    print("\n═══ B-2 · 순진한 복리 vs 실제 — **분산 손실** ═══", flush=True)
    res["compounding"] = {}
    for nm, f in FEES.items():
        netf = make_net(*f)
        m = res["absolute"][nm]["per_trade"]
        nf = res["slot5"][nm]["n_filled"]
        naive = ((1 + m / 100 / SLOTS) ** nf - 1) * 100
        actual = res["slot5"][nm]["median"]
        per_yr = nf / YEARS_LEN
        ann_naive = ((1 + naive / 100) ** (1 / YEARS_LEN) - 1) * 100
        res["compounding"][nm] = {"per_trade": m, "n_fills": nf,
                                  "fills_per_year": per_yr, "naive_total": naive,
                                  "naive_annual": ann_naive, "actual_median": actual,
                                  "variance_drag": actual - naive}
        print("  %-16s 거래당 %+.4f%% · 체결 %.0f건(연 %.1f건) → **순진한 복리 %+.1f%%**"
              "(연 %+.2f%%) vs **실제 슬롯5 %+.1f%%** → **차이 %+.1f%%p**"
              % (nm, m, nf, per_yr, naive, ann_naive, actual, actual - naive), flush=True)
    print("  ※ 차이는 **분산 손실 + 슬롯 유휴 + 순서 효과**가 섞인 값이다. 하나로 귀속하지 않는다.",
          flush=True)

    print("\n═══ C · 회전 속도 — 슬롯이 실제로 얼마나 도는가 ═══", flush=True)
    netf = make_net(*FEES["우대 왕복0.207%"])
    slot_sim.net = netf
    hold = [t["days"] + 1 for t in base]
    hold.sort()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in base)
    hi_d = max(t["resolve_date"] for t in base)
    n_days = len([d for d in cal if lo_d <= d <= hi_d])
    occ = []
    for s in range(20):
        r = slot_sim.sim(base, seed=s)
        occ.append(r["n_filled"])
    med_fill = st.median(occ)
    # 슬롯-일 점유 = 체결 건수 × 평균 보유일 ÷ (슬롯 × 거래일)
    used = med_fill * st.mean(hold)
    avail = SLOTS * n_days
    res["turnover"] = {"hold_median": st.median(hold), "hold_mean": st.mean(hold),
                       "hold_p90": hold[int(len(hold) * .9)], "n_trading_days": n_days,
                       "n_filled": med_fill, "slot_days_used": used,
                       "slot_days_available": avail, "occupancy_pct": used / avail * 100,
                       "cycle_days": avail / med_fill}
    print("  보유일수(결착 포함) 중앙 **%.0f일** · 평균 %.1f일 · P90 %.0f일"
          % (st.median(hold), st.mean(hold), hold[int(len(hold) * .9)]), flush=True)
    print("  거래일 %d일 × 슬롯 %d = 슬롯-일 %d · 실제 점유 %.0f → **점유율 %.1f%%**"
          % (n_days, SLOTS, avail, used, used / avail * 100), flush=True)
    print("  → **슬롯 하나가 한 바퀴 도는 데 %.1f거래일**(슬롯-일 ÷ 체결수). "
          "빈 슬롯이 **%.1f%%**의 시간 동안 놀고 있다."
          % (avail / med_fill, 100 - used / avail * 100), flush=True)

    print("\n═══ D · 비용이 기존 판정을 바꾸는가 ═══", flush=True)
    print("  [D-0] 해석: 순수익은 (1+총수익/100)×K−1 이라 **모든 차이가 정확히 %.6f배**가 된다."
          % res["K_ratio"], flush=True)
    # D-1 여유·거래당은 위 A절
    # D-2 격자 24칸 (고정 진입)
    print("\n  [D-2] 청산 격자 24칸 (고정 진입 3,776) — 슬리피지 0/0.5/1.0 (E절 겸함)", flush=True)
    grid = {}
    for nm, f in FEES.items():
        nf2 = make_net(*f)
        for slip in SLIPS:
            pos_pt = pos_eq = 0
            cells = {}
            for tg in TARGETS:
                for sp in STOPS:
                    tr = trades_of(rows, tg, sp, slip)
                    pt = st.mean([nf2(t["gain"]) for t in tr])
                    slot_sim.net = nf2
                    eq = st.median(slot_sim.sim(tr, seed=s)["equity_pct"]
                                   for s in range(50))
                    cells["+%d/-%d" % (tg, sp)] = {"per_trade": pt, "slot5": eq}
                    pos_pt += pt > 0
                    pos_eq += eq > 0
            grid["%s|slip%.1f" % (nm, slip)] = {"n_pos_per_trade": pos_pt,
                                                "n_pos_slot5": pos_eq, "cells": cells}
            print("    %-16s 슬립 %.1f%%p → 거래당 플러스 **%2d/24** · 슬롯5 플러스 **%2d/24**"
                  % (nm, slip, pos_pt, pos_eq), flush=True)
    res["grid"] = grid

    # D-3 손절의 몫
    print("\n  [D-3] 14번 손절의 몫 (①현행 − ②목표만)", flush=True)
    only_t = trades_of(rows, 20, None)
    res["stop_share"] = {}
    for nm, f in FEES.items():
        nf2 = make_net(*f)
        a = st.mean([nf2(t["gain"]) for t in base])
        b = st.mean([nf2(t["gain"]) for t in only_t])
        yr = {}
        for y in YS:
            aa = st.mean([nf2(t["gain"]) for t in base if t["year"] == y])
            bb = st.mean([nf2(t["gain"]) for t in only_t if t["year"] == y])
            yr[y] = aa - bb
        sg = sum(1 for v in yr.values() if v > 0)
        res["stop_share"][nm] = {"cur": a, "target_only": b, "diff": a - b,
                                 "by_year": yr, "n_pos_years": sg}
        print("    %-16s ①%+.4f − ②%+.4f = **%+.4f%%p** · 연도 부호 %d/6"
              % (nm, a, b, a - b, sg), flush=True)

    # D-4 16번 A·B·C 는 차이라 1.0027배
    print("\n  [D-4] 16번 A·B·C — 전부 **차이**이므로 %.6f배가 될 뿐이다"
          % res["K_ratio"], flush=True)
    for k, v in (("A β1", 0.5949), ("B", 1.1449), ("C", -0.4364)):
        print("    %-6s %+.4f → **%+.4f** (변화 %+.4f%%p)"
              % (k, v, v * res["K_ratio"], v * (res["K_ratio"] - 1)), flush=True)
    print("    → **상대 비교의 판정은 바뀌지 않는다.**", flush=True)

    (OUT / "17-fee-and-compounding.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/17-fee-and-compounding.json")


if __name__ == "__main__":
    main()
