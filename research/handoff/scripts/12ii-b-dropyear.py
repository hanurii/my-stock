# -*- coding: utf-8 -*-
"""12 (ii)-b — **슬롯5 자산곡선 축**으로 한 해씩 뺀 값.

12번 (i)의 핵심 소견 "플러스 여섯 칸이 6/6 전부 2021을 빼면 마이너스"는
**슬롯5 자산곡선** 축의 값이다. 12ii 본체에서 낸 한 해 제거는 **거래당** 축이라
같은 축이 아니다(M22-4: 축이 다른 값을 나란히 놓고 패턴처럼 읽지 않는다).

여기서는 **(i)의 상위 3칸 + (ii)의 슬롯5 상위 3칸**에 대해 같은 축으로 다시 낸다.
비교는 짝비교(같은 seed)이고, 기준선도 같은 해를 뺀 +20/−10 자체 진입이다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12ii-b-dropyear.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g12ii", HERE / "12ii-self-entry-grid.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

OUT = ROOT / ".cache" / "bt5y" / "out"
N = 200
BASE = (20, 10)
YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")
# (i)의 상위 3칸 + (ii)의 슬롯5 상위 3칸 (합집합)
CELLS = [(50, 7), (40, 7), (50, 10), (50, 5), (30, 7), (40, 5)]


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def main():
    print("후보 경로 적재 …", flush=True)
    cands = g.load_candidates()
    print("후보 %d건" % len(cands), flush=True)

    base_take = g.replay_entries(cands, *BASE)
    res = {"n_seeds": N, "base": "+20/-10 자체 진입", "cells": {}}

    print("\n[슬롯5 자산곡선 축 · 한 해 제거] 짝비교 %d회 · 기준선도 같은 해를 뺀다" % N,
          flush=True)
    for tg, sp in CELLS:
        key = "+%d/-%d" % (tg, sp)
        take = g.replay_entries(cands, tg, sp)
        rows = {}
        full_d = [slot_sim.sim(take, seed=s)["equity_pct"]
                  - slot_sim.sim(base_take, seed=s)["equity_pct"] for s in range(N)]
        rows["전체"] = {"diff_median": st.median(full_d), "band": list(band(full_d)),
                      "win_pct": sum(1 for x in full_d if x > 0) / N * 100}
        line = ["  %-8s 전체 %+7.1f%%p" % (key, rows["전체"]["diff_median"])]
        for y in YEARS:
            t2 = [t for t in take if t["year"] != y]
            b2 = [t for t in base_take if t["year"] != y]
            d = [slot_sim.sim(t2, seed=s)["equity_pct"]
                 - slot_sim.sim(b2, seed=s)["equity_pct"] for s in range(N)]
            rows[y] = {"diff_median": st.median(d), "band": list(band(d)),
                       "win_pct": sum(1 for x in d if x > 0) / N * 100}
            line.append("%s제거 %+7.1f" % (y, rows[y]["diff_median"]))
        flips = [y for y in YEARS
                 if (rows[y]["diff_median"] > 0) != (rows["전체"]["diff_median"] > 0)]
        rows["_flip_years"] = flips
        res["cells"][key] = rows
        print(" · ".join(line), flush=True)
        print("      → 부호가 뒤집히는 해: %s"
              % (", ".join(flips) if flips else "없음 (6/6 유지)"), flush=True)

    (OUT / "12ii-b-dropyear.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12ii-b-dropyear.json")


if __name__ == "__main__":
    main()
