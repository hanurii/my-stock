# -*- coding: utf-8 -*-
"""17c — **슬롯 수 축**(우대 비용) + **격자 24칸 한 해 제거**(우대 비용).

★ 결과 보기 전 해석 고정 (두뇌 세션)
  슬롯을 늘리는 것은 **기대값을 키우는 게 아니라 분산 손실을 줄이는 것**이다.
  포지션 비중 f, 거래당 수익 x 일 때 로그수익 ≈ `f·x − f²x²/2` 이고 거래 수 N ∝ 1/f 이므로
  **총 로그수익 ≈ (연 회전수) × (E[x] − f·E[x²]/2)** —
  **기대값 항은 f와 무관하고 분산 손실 항만 f에 비례한다.**
  → **"슬롯을 늘리면 더 번다"가 아니라 "덜 잃는다"로 적는다.**

  메모리 `method-viability-9month`에 같은 방향이 이미 있다
  (3개 −2.5% → 5개 +1.6% → 11개 +6.1% → 15개 +7.2%).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/17c-slots-and-grid.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import bisect
import importlib.util
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g17b", HERE / "17b-turnover-drag.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED, N_FAST = 200, 50
SLOT_LIST = [3, 5, 8, 10, 15, 20]
SLIPS = [0.0, 0.5, 1.0]
TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
NETF = g.make_net(0.000034, 0.002034)          # 우대 왕복 0.207% (정본)
slot_sim.net = NETF


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def occupancy(trades, dates, pos_of, seed, slots):
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
        free = slots - len(held)
        c = order.get(d)
        if c and free > 0:
            for t in c[:free]:
                held.append([pos_of[t["resolve_date"]], t])
                filled.append(t)
        occ += len(held)
    return filled, occ, slots * len(dates)


def resolve(r, tg, sp):
    e, n = r["e"], r["n"]
    ti = bisect.bisect_left(r["rmax"], e * (1 + tg / 100))
    ti = ti if ti < n else None
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
    return r["dts"][i], (r["c"][i] / e - 1) * 100, why


def main():
    tr = g.load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    m_all = st.mean(NETF(t["gain"]) for t in tr)
    print("거래 %d건 · 거래일 %d일 · 전체 거래당 %+.4f%%p (우대 비용)"
          % (len(tr), len(dates), m_all), flush=True)
    res = {"n": len(tr), "per_trade_all": m_all, "fee": "우대 왕복 0.207%"}

    print("\n═══ 슬롯 수 축 (우대 비용, %d seed) ═══" % N_SEED, flush=True)
    print("  %-4s %10s %18s %8s %8s %7s %7s %9s"
          % ("슬롯", "중앙", "5~95% 밴드", "폭", "최대낙폭", "체결", "점유율", "상위5제거"),
          flush=True)
    slots_res = {}
    for S in SLOT_LIST:
        rs = [slot_sim.sim(tr, slots=S, seed=s) for s in range(N_SEED)]
        eqs = sorted(r["equity_pct"] for r in rs)
        lo, hi = band(eqs)
        med = st.median(eqs)
        nf = st.median(r["n_filled"] for r in rs)
        mdd = st.median(r["mdd_pct"] for r in rs)
        key = lambda t: abs(NETF(t["gain"]))
        e5 = st.median(slot_sim.sim(sorted(tr, key=key)[:-5], slots=S, seed=s)["equity_pct"]
                       for s in range(N_FAST))
        occ = st.median(occupancy(tr, dates, pos_of, s, S)[1] for s in range(10))
        av = S * len(dates)
        # 네 단계 분해
        dec = []
        for s in range(10):
            fl, _, _ = occupancy(tr, dates, pos_of, s, S)
            xs = [NETF(t["gain"]) / S / 100 for t in fl]
            n = len(xs)
            mf = st.mean(xs)
            geo = 1.0
            for x in xs:
                geo *= (1 + x)
            dec.append((((1 + m_all / 100 / S) ** n - 1) * 100,
                        ((1 + mf) ** n - 1) * 100, (geo - 1) * 100,
                        st.mean([NETF(t["gain"]) for t in fl])))
        naive = st.median(d[0] for d in dec)
        naive_f = st.median(d[1] for d in dec)
        geo = st.median(d[2] for d in dec)
        m_fill = st.median(d[3] for d in dec)
        yr = {y: st.median(slot_sim.sim([t for t in tr if t["year"] != y],
                                        slots=S, seed=s)["equity_pct"]
                           for s in range(N_FAST)) for y in YS}
        slots_res[S] = {"median": med, "band": [lo, hi], "band_width": hi - lo,
                        "mdd": mdd, "n_filled": nf, "occupancy_pct": occ / av * 100,
                        "drop_top5": e5, "naive_all": naive, "naive_filled": naive_f,
                        "geometric": geo, "per_trade_filled": m_fill,
                        "sel_effect": naive_f - naive, "var_drag": geo - naive_f,
                        "rest": med - geo, "drop_year": yr,
                        "flip_years": [y for y in YS if (yr[y] > 0) != (med > 0)]}
        print("  %-4d %+9.1f%% %+8.1f ~ %+7.1f %7.1f %+7.1f%% %7.0f %6.1f%% %+8.1f%%"
              % (S, med, lo, hi, hi - lo, mdd, nf, occ / av * 100, e5), flush=True)
    res["slots"] = slots_res

    print("\n  [네 단계 분해] ①전체평균 기준 → ②체결분 기준 → ③실제 곱 → ④실측", flush=True)
    for S in SLOT_LIST:
        v = slots_res[S]
        print("   슬롯 %-3d 체결분 거래당 %+.4f%%p · ① %+7.1f → ② %+7.1f (선택 %+6.1f) "
              "→ ③ %+7.1f (**분산손실 %+6.1f**) → ④ %+7.1f (나머지 %+5.1f)"
              % (S, v["per_trade_filled"], v["naive_all"], v["naive_filled"],
                 v["sel_effect"], v["geometric"], v["var_drag"], v["median"], v["rest"]),
              flush=True)

    print("\n  [한 해 제거 · 슬롯별]", flush=True)
    for S in SLOT_LIST:
        v = slots_res[S]
        print("   슬롯 %-3d %s → 부호 반전 %s"
              % (S, " · ".join("%s %+.1f" % (y, v["drop_year"][y]) for y in YS),
                 ", ".join(v["flip_years"]) if v["flip_years"] else "없음"), flush=True)

    print("\n  [슬리피지 × 슬롯] 손절 건에만 먹임", flush=True)
    rows = g.load()
    slip_tab = {}
    for S in SLOT_LIST:
        line = []
        for slip in SLIPS:
            t2 = [dict(t, gain=t["gain"] - (slip if t["result"] == "loss"
                                            and t["reason"] == "stop" else 0.0))
                  for t in tr]
            med = st.median(slot_sim.sim(t2, slots=S, seed=s)["equity_pct"]
                            for s in range(N_FAST))
            slip_tab["S%d|%.1f" % (S, slip)] = med
            line.append("슬립%.1f %+7.1f%%" % (slip, med))
        print("   슬롯 %-3d %s" % (S, " · ".join(line)), flush=True)
    res["slip_by_slot"] = slip_tab

    # ── D · 격자 24칸 한 해 제거 (우대 비용, 슬롯5) ──
    print("\n═══ D · 청산 격자 24칸 한 해 제거 (우대 비용 · 슬롯5) ═══", flush=True)
    grid = {}
    pos_cells = []
    for tg in TARGETS:
        for sp in STOPS:
            t2 = []
            for r in rows:
                rd, gg, why = resolve(r, tg, sp)
                t2.append({"code": r["code"], "pattern": r["pattern"],
                           "scan_date": r["scan_date"], "entry_date": r["entry_date"],
                           "resolve_date": rd, "gain": gg, "year": r["year"],
                           "result": "win" if why == "target" else "loss"})
            med = st.median(slot_sim.sim(t2, seed=s)["equity_pct"] for s in range(N_FAST))
            yr = {y: st.median(slot_sim.sim([t for t in t2 if t["year"] != y],
                                            seed=s)["equity_pct"] for s in range(N_FAST))
                  for y in YS}
            k = "+%d/-%d" % (tg, sp)
            flips = [y for y in YS if (yr[y] > 0) != (med > 0)]
            grid[k] = {"median": med, "drop_year": yr, "flip_years": flips}
            if med > 0:
                pos_cells.append(k)
    res["grid_drop_year"] = grid
    print("  슬롯5 중앙이 플러스인 칸 **%d / 24**" % len(pos_cells), flush=True)
    survive = 0
    for k in pos_cells:
        v = grid[k]
        print("   %-8s 전체 %+7.1f%% · %s → 부호 반전 %s"
              % (k, v["median"], " ".join("%s %+6.1f" % (y, v["drop_year"][y]) for y in YS),
                 ", ".join(v["flip_years"]) if v["flip_years"] else "**없음(6/6)**"),
              flush=True)
        survive += not v["flip_years"]
    res["n_pos_cells"] = len(pos_cells)
    res["n_survive_all_years"] = survive
    print("  → **플러스 %d칸 중 여섯 해 전부 부호를 유지하는 칸 %d개**"
          % (len(pos_cells), survive), flush=True)

    (OUT / "17c-slots-and-grid.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/17c-slots-and-grid.json")


if __name__ == "__main__":
    main()
