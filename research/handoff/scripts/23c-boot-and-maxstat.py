# -*- coding: utf-8 -*-
"""23c · **자료 축 구간(날짜 블록 부트스트랩)** + **Westfall–Young 최대통계 12칸**.

★ 1단계의 구간은 **seed 축**이었다. M10(불확실성의 단위는 자료)에 따라 여기서 **자료 축**을 낸다.
★ 최대통계는 12b 선례와 같은 형태 — 위치 블록 재추출로 새 시간축을 만들고 슬롯5를 다시 돌린 뒤
  **중심화**해서 최대를 취한다(복제당 seed 1개).
★ 통계는 칸마다 `min(보수적, 낙관적)`(두뇌 세션 정정).

⚠️ **관측 최고 헤드라인이 음수라면 최대통계는 결론을 바꿀 수 없다.** 그래도 문턱은 적는다.
  그리고 M12-1대로 **"효과 없음" 쪽에 최대통계를 걸어 유리하게 쓰지 않는다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/23c-boot-and-maxstat.py
난수 seed: 블록 부트스트랩 230200 · 블록 20~40거래일 · 1,000회 · 복제당 슬롯 seed 230200+b
"""
from __future__ import annotations

import importlib.util
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g1", HERE / "23-stage1-ratchet.py")
g1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g1)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_BOOT = 1000
BOOT_SEED = 230200
BLOCK_MIN, BLOCK_MAX = 20, 40
SLOTS = 5


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def boot_eq(by_pos, n_pos, slots=SLOTS):
    """by_pos[p] = [(rel_hold, net, okey)] — 이미 okey 오름차순 정렬."""
    eq, held = 1.0, []
    for p in range(n_pos):
        if held:
            keep = []
            for h in held:
                if h[0] < p:
                    eq += h[1] * h[2] / 100
                else:
                    keep.append(h)
            held = keep
        free = slots - len(held)
        c = by_pos.get(p)
        if free > 0 and c:
            wgt = eq / slots
            for rel, nt, _k in c[:free]:
                held.append([p + rel, wgt, nt])
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1) * 100


def main():
    P = g1.build()
    all_dates = sorted({d for p in P for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)
    arms = []
    for trig in g1.TRIGGERS:
        for lab, f in g1.NEWSTOPS:
            news = f(trig)
            if news < trig:
                arms.append((trig, lab, news))
    tr = {"_base": g1.to_trades(P, None)}
    for trig, lab, news in arms:
        for mode in ("pess", "opt"):
            tr["%g/%s/%s" % (trig, lab, mode)] = g1.to_trades(P, (trig, news, mode))
    keys = list(tr)
    base = tr["_base"]
    print("팔 %d + 기준선 · 거래일 %d · 거래 %d" % (len(tr) - 1, n_pos, len(base)),
          flush=True)

    # 관측 헤드라인(1단계 산출물 재사용)
    s1 = json.loads((OUT / "23-stage1-ratchet.json").read_text(encoding="utf-8"))
    obs_head = {"+%g%%/%s" % (c["trigger"], c["stop_label"]): c["headline"]
                for c in s1["cells"]}
    names = list(obs_head)
    obs_max = max(obs_head.values())
    obs_max_cell = max(obs_head, key=obs_head.get)
    print("관측 최고 헤드라인 %s **%+.2f%%p**" % (obs_max_cell, obs_max), flush=True)

    # 원 진입위치별 색인 (거래 인덱스는 팔끼리 공통)
    epos = [pos_of[t["entry_date"]] for t in base]
    idx_at = defaultdict(list)
    for i, p in enumerate(epos):
        idx_at[p].append(i)
    hold = {k: [pos_of[t["resolve_date"]] - pos_of[t["entry_date"]] for t in tr[k]]
            for k in keys}
    nets = {k: [slot_sim.net(t["gain"]) for t in tr[k]] for k in keys}
    okey_of = [(t["code"], t["scan_date"], t.get("pattern", "")) for t in base]

    rnd = random.Random(BOOT_SEED)
    diffs = {n: [] for n in names}
    maxes = []
    for b in range(N_BOOT):
        blocks, tot = [], 0
        while tot < n_pos:
            L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
            a = rnd.randint(0, n_pos - L)
            LL = min(L, n_pos - tot)
            blocks.append((a, LL))
            tot += LL
        seed = BOOT_SEED + b
        # 새 시간축 위 거래 목록 (팔 공통: 위치와 정렬키)
        placed = []            # (new_pos, trade_idx, okey)
        off = 0
        for a, L in blocks:
            for j in range(L):
                for i in idx_at.get(a + j, ()):
                    c, sd, pt = okey_of[i]
                    placed.append((off + j, i,
                                   random.Random("%d|%s|%s|%s" % (seed, c, sd, pt)).random()))
            off += L
        placed.sort(key=lambda z: (z[0], z[2]))
        eqs = {}
        for k in keys:
            bp = defaultdict(list)
            hk, nk = hold[k], nets[k]
            for np_, i, ky in placed:
                bp[np_].append((hk[i], nk[i], ky))
            eqs[k] = boot_eq(bp, n_pos)
        cur = {}
        for trig, lab, _n in arms:
            nm = "+%g%%/%s" % (trig, lab)
            v = min(eqs["%g/%s/pess" % (trig, lab)] - eqs["_base"],
                    eqs["%g/%s/opt" % (trig, lab)] - eqs["_base"])
            cur[nm] = v
            diffs[nm].append(v)
        maxes.append(max(cur[n] - obs_head[n] for n in names))
        if (b + 1) % 100 == 0:
            print("  부트스트랩 %d/%d" % (b + 1, N_BOOT), flush=True)

    print("\n" + "=" * 78, flush=True)
    print("자료 축 구간 — **날짜 블록 부트스트랩 1,000회** (1단계의 seed 구간과 나란히)",
          flush=True)
    print("=" * 78, flush=True)
    s1ci = {"+%g%%/%s" % (c["trigger"], c["stop_label"]): c["headline_ci"]
            for c in s1["cells"]}
    print("  %-16s %10s %22s %22s"
          % ("칸", "헤드라인", "자료 축 95%", "seed 축 95%(1단계)"), flush=True)
    rows = []
    for nm in names:
        lo, hi = ci(diffs[nm])
        rows.append({"cell": nm, "headline": obs_head[nm], "data_ci": [lo, hi],
                     "seed_ci": s1ci[nm],
                     "excludes_zero": bool(lo > 0 or hi < 0),
                     "boot_median": st.median(diffs[nm])})
        print("  %-16s %+9.2f%%p   %+8.2f ~ %+8.2f   %+8.1f ~ %+8.1f  %s"
              % (nm, obs_head[nm], lo, hi, s1ci[nm][0], s1ci[nm][1],
                 "**0 제외**" if (lo > 0 or hi < 0) else "0 포함"), flush=True)
    n_ex = sum(1 for r in rows if r["excludes_zero"])
    print("\n  **자료 축에서 0을 제외하는 칸 %d / 12** (전부 음수 쪽인지 확인: %s)"
          % (n_ex, all(r["data_ci"][1] < 0 for r in rows if r["excludes_zero"])),
          flush=True)

    ms = sorted(maxes)
    thr = ms[int(N_BOOT * 0.95)]
    p_max = sum(1 for x in maxes if x >= obs_max) / N_BOOT
    print("\n" + "=" * 78, flush=True)
    print("Westfall–Young 최대통계 · 12칸", flush=True)
    print("=" * 78, flush=True)
    print("  귀무(중심화) 최대통계 95%% 분위 **%+.2f%%p**" % thr, flush=True)
    print("  관측 최고 헤드라인 %s **%+.2f%%p** → 최대통계 p = **%.3f**"
          % (obs_max_cell, obs_max, p_max), flush=True)
    print("  보정 후 남는 칸: **%d / 12**"
          % sum(1 for n in names if obs_head[n] > thr and obs_head[n] > 0), flush=True)
    print("\n  ⚠️ 관측 최고가 **0 아래**이므로 이 보정은 결론을 바꿀 수 없다."
          "\n     '어느 칸도 기준선을 못 넘는다'는 보정 이전에 정해진다.", flush=True)

    res = {"n_boot": N_BOOT, "block": [BLOCK_MIN, BLOCK_MAX],
           "obs_max_cell": obs_max_cell, "obs_max": obs_max,
           "null_p95": thr, "p_maxstat": p_max,
           "n_excl_zero": n_ex, "cells": rows}
    (OUT / "23c-boot-and-maxstat.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/23c-boot-and-maxstat.json", flush=True)


if __name__ == "__main__":
    main()
