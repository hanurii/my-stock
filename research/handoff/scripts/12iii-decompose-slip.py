# -*- coding: utf-8 -*-
"""12 (iii) — **진입 효과만** 떼어 내는 분해판 + **슬리피지** (ii)·(iii) 공통.

(i)과 (ii)는 청산 규칙과 진입 집합을 **동시에** 바꾼다. 그래서 (ii)에서 여섯 칸 중
다섯이 부호를 유지한 것이 **청산 때문인지 진입 때문인지 가를 수 없었다.**
한 칸을 더 채우면 2×2가 완성된다:

| 판 | 진입 집합 | 청산 규칙 | 재는 것 |
|---|---|---|---|
| (i)   | 현행 고정      | 각 칸        | 청산 효과만 |
| (iii) | **각 칸 자체** | **+20/−10 고정** | **진입 효과만** |
| (ii)  | 각 칸 자체     | 각 칸        | 둘의 합 |

**이것은 판정이 아니라 진단이다.** 12번의 판정은 (i)의 자체 문턱 여섯이 정하고,
문턱 5(최대통계)가 이미 깨져 있다.

슬리피지는 12번 (i)과 같은 규약 — **손절로 끝난 건에만** `gain -= slip`
(`both_same_day`는 12번이 별도 사유로 두므로 여기서도 먹이지 않는다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12iii-decompose-slip.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import random
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
TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
BASE = (20, 10)
SLIPS = [0.0, 0.5, 1.0]
N = 200
YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")
FOCUS = [(50, 7), (40, 7), (50, 10), (50, 5), (30, 7), (40, 5)]
net = slot_sim.net

# ── order_key 메모이즈 — 같은 (seed, 거래)를 24칸 × 3슬립 × 2판에서 다시 쓴다 ──
_ok_cache: dict = {}
_orig_order_key = slot_sim.order_key


def order_key_cached(seed, t):
    k = (seed, t["code"], t["scan_date"], t.get("pattern", ""))
    v = _ok_cache.get(k)
    if v is None:
        v = _orig_order_key(seed, t)
        _ok_cache[k] = v
    return v


slot_sim.order_key = order_key_cached


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def score(cands_take, res_key, slip):
    """진입 집합은 그대로 두고 **청산 규칙 res_key** 로 손익을 매긴다."""
    out = []
    for t in cands_take:
        rd, gain, why, days = t["_src"]["res"][res_key]
        if why == "stop":
            gain -= slip
        out.append({"code": t["code"], "pattern": t["pattern"],
                    "scan_date": t["scan_date"], "entry_date": t["entry_date"],
                    "resolve_date": rd or t["entry_date"], "gain": gain,
                    "reason": why, "year": t["year"],
                    "result": ("win" if why == "target" else
                               "loss" if why in ("stop", "both_same_day") else
                               ("win" if gain > 0 else "loss"))})
    return out


def entries(cands, tg, sp):
    """그 칸의 청산 규칙으로 만든 진입 집합 (원본 후보 dict 를 매달아 둔다)."""
    open_until, cur_year, taken = {}, None, []
    for t in cands:
        if t["src_year"] != cur_year:
            cur_year = t["src_year"]
            open_until = {}
        c, ed = t["code"], t["entry_date"]
        if c in open_until and ed <= open_until[c]:
            continue
        rd = t["res"][(tg, sp)][0]
        open_until[c] = rd or ed
        taken.append({"code": c, "pattern": t["pattern"], "scan_date": t["scan_date"],
                      "entry_date": ed, "year": t["year"], "_src": t})
    return taken


def eqs_of(trades):
    return [slot_sim.sim(trades, seed=s)["equity_pct"] for s in range(N)]


def main():
    print("후보 경로 적재 …", flush=True)
    cands = g.load_candidates()
    print("후보 %d건" % len(cands), flush=True)

    ent = {(tg, sp): entries(cands, tg, sp) for tg in TARGETS for sp in STOPS}
    base_ent = ent[BASE]
    res = {"n_candidates": len(cands), "n_seeds": N, "slips": SLIPS,
           "note": "(iii)은 판정이 아니라 진단이다. 청산 규칙을 +20/−10 으로 고정하고 "
                   "진입 집합만 각 칸의 것으로 바꿔 진입 효과를 떼어 낸다.",
           "slip_rule": "12번 (i)과 같은 규약 — 손절(stop)로 끝난 건에만 gain -= slip"}

    grids = {}
    for slip in SLIPS:
        base_eq = eqs_of(score(base_ent, BASE, slip))
        for pan, rk in (("(ii) 진입+청산", None), ("(iii) 진입만", BASE)):
            tab = {}
            for tg in TARGETS:
                for sp in STOPS:
                    key = "+%d/-%d" % (tg, sp)
                    e = eqs_of(score(ent[(tg, sp)], rk or (tg, sp), slip))
                    d = [e[i] - base_eq[i] for i in range(N)]
                    lo, hi = band(e)
                    tab[key] = {"n": len(ent[(tg, sp)]),
                                "median": st.median(e), "band": [lo, hi],
                                "band_width": hi - lo,
                                "win_pct": sum(1 for x in d if x > 0) / N * 100,
                                "diff_median": st.median(d), "diff_ci": list(ci(d))}
            grids["%s|slip%.1f" % (pan, slip)] = tab
            pos = [k for k, v in tab.items() if v["median"] > 0]
            print("\n[%s · 슬립 %.1f%%p] 기준선 중앙 %+.1f%% · "
                  "슬롯5 중앙이 **플러스인 칸 %d / 24**"
                  % (pan, slip, st.median(base_eq), len(pos)), flush=True)
            for tg in TARGETS:
                print("   " + " ".join(
                    "%s %+7.1f" % ("+%d/-%d" % (tg, sp), tab["+%d/-%d" % (tg, sp)]["median"])
                    for sp in STOPS), flush=True)
    res["grids"] = grids

    # ── (iii) 한 해 제거 — (ii)-b 와 같은 축·같은 칸 ──
    print("\n[(iii) 진입만 · 슬롯5 축 한 해 제거] 슬립 0 · 짝비교 %d회" % N, flush=True)
    dy = {}
    b0 = score(base_ent, BASE, 0.0)
    for tg, sp in FOCUS:
        key = "+%d/-%d" % (tg, sp)
        t0 = score(ent[(tg, sp)], BASE, 0.0)
        rows = {}
        full = [x - y for x, y in zip(eqs_of(t0), eqs_of(b0))]
        rows["전체"] = {"diff_median": st.median(full), "band": list(band(full)),
                      "win_pct": sum(1 for x in full if x > 0) / N * 100}
        line = ["  %-8s 전체 %+7.1f%%p" % (key, rows["전체"]["diff_median"])]
        for y in YEARS:
            a = [t for t in t0 if t["year"] != y]
            b = [t for t in b0 if t["year"] != y]
            d = [x - z for x, z in zip(eqs_of(a), eqs_of(b))]
            rows[y] = {"diff_median": st.median(d), "band": list(band(d))}
            line.append("%s제거 %+7.1f" % (y, rows[y]["diff_median"]))
        flips = [y for y in YEARS
                 if (rows[y]["diff_median"] > 0) != (rows["전체"]["diff_median"] > 0)]
        rows["_flip_years"] = flips
        dy[key] = rows
        print(" · ".join(line), flush=True)
        print("      → 부호 반전: %s" % (", ".join(flips) if flips else "없음 (6/6 유지)"),
              flush=True)
    res["iii_drop_year"] = dy

    (OUT / "12iii-decompose-slip.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12iii-decompose-slip.json")


if __name__ == "__main__":
    main()
