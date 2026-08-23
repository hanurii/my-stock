# -*- coding: utf-8 -*-
"""17d — 슬리피지 × 슬롯 수, 그리고 **격자 24칸 한 해 제거**(둘 다 우대 비용).

17c 의 슬롯 수 절은 이미 끝났고(`17c-slots-and-grid.json`), 여기서는 남은 두 절만 돈다.

★ 슬리피지는 **손절로 끝난 건에만** 먹인다(12번과 같은 규약).
★ 격자 한 해 제거는 **서술의 정확성** 문제다 — 판정은 M24로 안 바뀐다(문턱 5가 이미 깨졌다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/17d-slip-grid.py
"""
from __future__ import annotations

import bisect
import importlib.util
import json
import statistics as st
import sys
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
N_FAST = 50
SLOT_LIST = [3, 5, 8, 10, 15, 20]
SLIPS = [0.0, 0.5, 1.0]
TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
NETF = g.make_net(0.000034, 0.002034)
slot_sim.net = NETF


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
    res = {"fee": "우대 왕복 0.207%", "n": len(tr)}

    print("[슬리피지 × 슬롯] 손절 건에만 먹임 (우대 비용)", flush=True)
    tab = {}
    for S in SLOT_LIST:
        line = []
        for slip in SLIPS:
            t2 = [dict(t, gain=t["gain"] - (slip if t["reason"] == "stop" else 0.0))
                  for t in tr]
            med = st.median(slot_sim.sim(t2, slots=S, seed=s)["equity_pct"]
                            for s in range(N_FAST))
            tab["S%d|%.1f" % (S, slip)] = med
            line.append("슬립%.1f **%+7.1f%%**" % (slip, med))
        print("  슬롯 %-3d %s" % (S, " · ".join(line)), flush=True)
    res["slip_by_slot"] = tab

    print("\n[격자 24칸 한 해 제거] 우대 비용 · 슬롯5", flush=True)
    rows = g.load()
    # rows 에는 이미 +20/-10 결착이 들어 있으므로 경로 재계산이 필요하다
    raw = []
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
            raw.append({"code": p["code"], "pattern": p["pattern"],
                        "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                        "year": p["entry_date"][:4], "e": e, "c": c, "dts": dts,
                        "rmax": rmax, "rmin": rmin, "n": n})
    grid, pos_cells = {}, []
    for tg in TARGETS:
        for sp in STOPS:
            t2 = []
            for r in raw:
                rd, gg, why = resolve(r, tg, sp)
                if rd not in pos_of:
                    continue
                t2.append({"code": r["code"], "pattern": r["pattern"],
                           "scan_date": r["scan_date"], "entry_date": r["entry_date"],
                           "resolve_date": rd, "gain": gg, "year": r["year"],
                           "result": "win" if why == "target" else "loss"})
            med = st.median(slot_sim.sim(t2, seed=s)["equity_pct"] for s in range(N_FAST))
            yr = {y: st.median(slot_sim.sim([t for t in t2 if t["year"] != y],
                                            seed=s)["equity_pct"] for s in range(N_FAST))
                  for y in YS}
            k = "+%d/-%d" % (tg, sp)
            grid[k] = {"median": med, "drop_year": yr,
                       "flip_years": [y for y in YS if (yr[y] > 0) != (med > 0)]}
            if med > 0:
                pos_cells.append(k)
    res["grid"] = grid
    res["n_pos_cells"] = len(pos_cells)
    print("  슬롯5 중앙이 플러스인 칸 **%d / 24**" % len(pos_cells), flush=True)
    survive = 0
    for k in sorted(pos_cells, key=lambda x: -grid[x]["median"]):
        v = grid[k]
        survive += not v["flip_years"]
        print("   %-8s 전체 %+7.1f%% · %s → 반전 %s"
              % (k, v["median"],
                 " ".join("%s %+6.1f" % (y, v["drop_year"][y]) for y in YS),
                 ", ".join(v["flip_years"]) if v["flip_years"] else "**없음(6/6)**"),
              flush=True)
    res["n_survive_all_years"] = survive
    print("  → **플러스 %d칸 중 여섯 해 전부 부호를 유지하는 칸 %d개**"
          % (len(pos_cells), survive), flush=True)

    (OUT / "17d-slip-grid.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/17d-slip-grid.json")


if __name__ == "__main__":
    main()
