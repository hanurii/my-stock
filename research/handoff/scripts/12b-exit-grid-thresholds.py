# -*- coding: utf-8 -*-
"""12b — 청산 격자 채택 문턱 1·5 계산 (12-exit-grid.py 의 후속 패스).

지시서: research/handoff/tasks/12-exit-grid.md (v2) 5단계
  문턱 1 = 다섯 구간 전부에서 현행 대비 슬롯5 우세(구간별 짝비교 우세율 > 50%)
  문턱 5 = **날짜 블록 부트스트랩 1,000회 + 중심화(Westfall-Young) 최대통계 보정**
           (개정 v2 M5 — 원형이동 순열은 칸별 수익률을 안 바꿔 귀무를 못 만들므로 폐기)

문턱 2·3·4·6은 12-exit-grid.py 산출물(`12-exit-grid.json`)에서 바로 읽는다.

블록 부트스트랩 방식
--------------------
거래일 달력에서 길이 20~40일 블록을 **복원추출**해 같은 길이의 새 시간축을 만든다.
각 거래는 자기 진입일이 속한 블록을 따라 새 위치로 옮겨지고, 결착 위치는
**그 칸에서의 보유일수**를 더해 정한다(자기상관 보존). 그 위에서 슬롯5를 돌린다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12b-exit-grid-thresholds.py
난수 seed: 구간별 짝비교 0~399 · 부트스트랩 10000~10999 (고정)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "grid", Path(__file__).resolve().parent / "12-exit-grid.py")
grid = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grid)

OUT = ROOT / ".cache" / "bt5y" / "out"
TARGETS, STOPS = grid.TARGETS, grid.STOPS
BASE = grid.BASE_CELL
N_PAIR = 400
N_BOOT = 1000
BOOT_SEED0 = 10000
BLOCK_MIN, BLOCK_MAX = 20, 40
SEGMENTS = [("2021", "2021-01-01", "2021-12-31"), ("2022", "2022-01-01", "2022-12-31"),
            ("2023", "2023-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
            ("2025~26", "2025-01-01", "2026-12-31")]
net = slot_sim.net


def boot_sim(by_pos, n_pos, seed, slots=5):
    """새 시간축(정수 위치) 위의 슬롯5 — 정본 ④(결착분은 다음 위치부터 자리 비움)."""
    eq = 1.0
    held = []                     # [resolve_pos, trade, weight, credited]
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * net(h[1]["gain"]) / 100
                    h[3] = True
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0:
            c = by_pos.get(p)
            if c:
                if len(c) > 1:
                    c = sorted(c, key=lambda t: slot_sim.order_key(seed, t))
                wgt = eq / slots
                for t in c[:free]:
                    held.append([p + t["days_held"], t, wgt, False])
    for h in held:
        if not h[3]:
            eq += h[2] * net(h[1]["gain"]) / 100
    return (eq - 1) * 100


def main():
    print("경로 적재 …", flush=True)
    P, year_last = grid.load_paths()
    all_dates = sorted({d for p in P.values() for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    byday = grid.build_byday(P)
    drop = {k for k, p in P.items()
            for tg in TARGETS for sp in STOPS
            if grid.outcome(p, tg, sp, "na") is None}
    inter = set(P) - drop
    PLANS = [("가", "ga", None), ("나", "na", None), ("다", "na", inter)]
    res = {"n_boot": N_BOOT, "block": [BLOCK_MIN, BLOCK_MAX], "plans": {}}

    print("후보 순서 캐시 %d seed …" % N_PAIR, flush=True)
    cache = grid.build_order_cache(byday, N_PAIR)

    for pname, plan, keys in PLANS:
        cells = {}
        base_tr, _ = grid.cell_trades(P, *BASE, plan, keys)
        # ── 문턱 1: 구간별 짝비교 ──
        seg_out = {}
        for sname, lo, hi in SEGMENTS:
            skeys = {k for k, p in P.items()
                     if lo <= p["entry_date"] <= hi and (keys is None or k in keys)}
            sdates = sorted({d for k in skeys for d in P[k]["dates"]})
            sbyday = grid.build_byday({k: P[k] for k in skeys})
            scache = grid.build_order_cache(sbyday, N_PAIR)
            btr, _ = grid.cell_trades(P, *BASE, plan, skeys)
            bres = grid.run_cell(btr, scache, sbyday, sdates, drop5=False)
            row = {"n_base": len(btr), "base_median": bres["median"],
                   "base_n_filled": bres["n_filled"], "cells": {}}
            for tg in TARGETS:
                for sp in STOPS:
                    tr, stt = grid.cell_trades(P, tg, sp, plan, skeys)
                    r = grid.run_cell(tr, scache, sbyday, sdates, drop5=False)
                    cmp_ = grid.compare(r, bres)
                    row["cells"]["t%ds%d" % (tg, sp)] = {
                        "win_pct": cmp_["vs_base_win_pct"],
                        "median": r["median"], "n_filled": r["n_filled"], "n": stt["n"]}
            seg_out[sname] = row
            print("[판 %s] 구간 %s 완료 (기준선 중앙 %+.1f%% · 체결 %.0f)"
                  % (pname, sname, bres["median"], bres["n_filled"]), flush=True)

        # ── 문턱 5: 블록 부트스트랩 최대통계 (중심화) ──
        obs = {}
        rnd = random.Random(BOOT_SEED0)
        trades = {}
        for tg in TARGETS:
            for sp in STOPS:
                tr, _ = grid.cell_trades(P, tg, sp, plan, keys)
                trades["t%ds%d" % (tg, sp)] = tr
        trades["_base"] = base_tr
        # 관측 우위 (400 seed 짝비교의 중앙 차이)
        full = {}
        for key, tr in trades.items():
            full[key] = grid.run_cell(tr, cache, byday, all_dates, drop5=False)
        for key in trades:
            if key == "_base":
                continue
            obs[key] = st.median([full[key]["equities"][i] - full["_base"]["equities"][i]
                                  for i in range(N_PAIR)])
        obs_max_cell = max(obs, key=obs.get)
        obs_max = obs[obs_max_cell]

        # 거래를 진입일 위치로 색인
        idx = defaultdict(lambda: defaultdict(list))
        for key, tr in trades.items():
            for t in tr:
                idx[key][pos_of[t["entry_date"]]].append(t)

        n_pos = len(all_dates)
        maxes = []
        for b in range(N_BOOT):
            blocks, total = [], 0
            while total < n_pos:
                L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
                a = rnd.randint(0, n_pos - L)
                blocks.append((a, min(L, n_pos - total)))
                total += L
            seed = BOOT_SEED0 + b
            eqs = {}
            for key in trades:
                by_pos = defaultdict(list)
                off = 0
                for a, L in blocks:
                    for j in range(L):
                        for t in idx[key].get(a + j, ()):
                            by_pos[off + j].append(t)
                    off += L
                eqs[key] = boot_sim(by_pos, n_pos, seed)
            stat = max(eqs[k] - eqs["_base"] - obs[k] for k in obs)   # 중심화
            maxes.append(stat)
            if (b + 1) % 200 == 0:
                print("  [판 %s] 부트스트랩 %d/%d" % (pname, b + 1, N_BOOT), flush=True)
        p_max = sum(1 for x in maxes if x >= obs_max) / N_BOOT
        ms = sorted(maxes)
        print("[판 %s] 최고 칸 %s 관측우위 %+.1f%%p · 최대통계 p = %.3f (귀무 95%% 분위 %+.1f)"
              % (pname, obs_max_cell, obs_max, p_max, ms[int(N_BOOT * 0.95)]), flush=True)

        cells["segments"] = seg_out
        cells["maxstat"] = {"obs_best_cell": obs_max_cell, "obs_best_diff": obs_max,
                            "p_value": p_max, "null_p95": ms[int(N_BOOT * 0.95)],
                            "obs_diff_by_cell": obs}
        res["plans"][pname] = cells
        (OUT / "12b-exit-grid-thresholds.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n저장: .cache/bt5y/out/12b-exit-grid-thresholds.json")


if __name__ == "__main__":
    main()
