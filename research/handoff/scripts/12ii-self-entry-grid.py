# -*- coding: utf-8 -*-
"""12 (ii) — 청산 격자 24칸 · **자체 진입 유니버스 판**.

지금까지 12번은 **(i) 고정 진입**만 냈다. 모든 칸이 현행 +20/−10 이 실제로 산 3,776건을
그대로 물려받아 청산만 바꾼 판이다. 그러나 **청산 규칙이 바뀌면 보유 기간이 바뀌고,
보유 기간이 바뀌면 겹침 차단(`open_until`)이 풀려 진입 자체가 달라진다.**
(ii)는 그것을 반영한다.

★ (ii)는 **12번의 판정을 바꾸지 않는다.** 채택 문턱이 연접이고 문턱 5가 이미 깨졌다.
  (ii)가 답하는 것은 **"청산 규칙을 바꾸면 진입이 몇 건 늘고 전체 효과가 얼마인가"** 하나다.

입력: `.cache/bt5y/out/cand_paths_{2021..2026}.json` — 하네스가 기록한 **후보 9,334건 전수**
      (진입 3,776 + 겹침으로 막힌 5,558). 기록본 하네스는 동일성 관문 6/6 통과.

판정축·렌즈·동등성 폭은 12번 사양 그대로(M14-1·M15·M24). M29-3·M30 함께 건다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12ii-self-entry-grid.py
난수 seed: 슬롯 순서 0~399 · 블록 부트스트랩 120000
"""
from __future__ import annotations

import bisect
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
BASE = (20, 10)
N_PAIR, N_LEVEL = 400, 200
N_BOOT, BOOT_SEED = 1000, 120000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K, EQUIV = 2.80, 0.5
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")
net = slot_sim.net


def resolve_all(p):
    """한 후보의 경로에서 24칸 전부의 결착을 한 번에 낸다."""
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
    out = {}
    for tg in TARGETS:
        ti = bisect.bisect_left(rmax, e * (1 + tg / 100))
        ti = ti if ti < n else None
        for sp in STOPS:
            si = bisect.bisect_left(rmin, -(e * (1 - sp / 100)))
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
            out[(tg, sp)] = (dts[i], (c[i] / e - 1) * 100, why, i)
    return out


def load_candidates():
    """후보 전수 + 24칸 결착표. 경로 배열은 즉시 버려 메모리를 아낀다."""
    rows = []
    for y in range(2021, 2027):
        d = json.loads((OUT / ("cand_paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            rows.append({"code": p["code"], "pattern": p["pattern"],
                         "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                         "blocked": p["blocked_overlap"], "year": p["entry_date"][:4],
                         "src_year": y,          # 하네스가 그 해 실행에서 낸 후보
                         "res": resolve_all(p)})
        print("  후보 경로 %d 적재 · 누적 %d" % (y, len(rows)), flush=True)
    return rows


def replay_entries(cands, tg, sp):
    """그 칸의 청산 규칙으로 **진입 타임라인을 다시 만든다**.

    하네스와 같은 규칙: 같은 종목은 직전 매매가 결착될 때까지 다시 안 산다
    (`edate <= open_until[code]` 이면 건너뛴다). 후보 목록의 순서는 하네스가 기록한
    순서 그대로라 같은 날 안의 처리 순서도 하네스와 같다.
    """
    # ★ 하네스는 **해마다 따로 실행**되므로 open_until 이 연초에 비워진다.
    #   해를 넘겨 이어붙이면 진입 집합이 달라진다(실측: 3,776 → 3,703).
    open_until = {}
    cur_year = None
    taken = []
    for t in cands:
        if t["src_year"] != cur_year:
            cur_year = t["src_year"]
            open_until = {}
        c, ed = t["code"], t["entry_date"]
        if c in open_until and ed <= open_until[c]:
            continue
        rd, gain, why, days = t["res"][(tg, sp)]
        open_until[c] = rd or ed
        taken.append({"code": c, "pattern": t["pattern"], "scan_date": t["scan_date"],
                      "entry_date": ed, "resolve_date": rd, "gain": gain,
                      "reason": why, "days": days, "year": t["year"],
                      "result": ("win" if why == "target" else
                                 "loss" if why in ("stop", "both_same_day") else
                                 ("win" if gain > 0 else "loss"))})
    return taken


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    out, tot = [], 0
    while tot < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - tot)
        out.append((a, LL))
        tot += LL
    return out


def main():
    print("후보 경로 적재 …", flush=True)
    cands = load_candidates()
    n_blocked = sum(1 for t in cands if t["blocked"])
    print("후보 %d건 (현행 규칙 진입 %d · 겹침으로 막힘 %d)"
          % (len(cands), len(cands) - n_blocked, n_blocked), flush=True)
    res = {"n_candidates": len(cands), "n_entered_current": len(cands) - n_blocked,
           "n_blocked_current": n_blocked, "equiv_bound": EQUIV,
           "note": "(ii)는 12번의 판정을 바꾸지 않는다. "
                   "답하는 것은 '진입이 몇 건 늘고 전체 효과가 얼마인가' 하나다."}

    # ── 관문: 현행 규칙(+20/−10)으로 재생하면 하네스 진입 집합과 같아야 한다 ──
    base_take = replay_entries(cands, *BASE)
    cur = {(t["scan_date"], t["code"], t["pattern"]) for t in cands if not t["blocked"]}
    rep = {(t["scan_date"], t["code"], t["pattern"]) for t in base_take}
    ok = cur == rep
    res["replay_gate"] = {"n_harness": len(cur), "n_replay": len(rep),
                          "identical": bool(ok),
                          "only_harness": len(cur - rep), "only_replay": len(rep - cur)}
    print("\n★ 재생 관문 — +20/−10 으로 진입 타임라인을 다시 만들면 하네스와 같은가", flush=True)
    print("   하네스 %d건 · 재생 %d건 · **%s** (하네스에만 %d · 재생에만 %d)"
          % (len(cur), len(rep), "일치" if ok else "불일치",
             len(cur - rep), len(rep - cur)), flush=True)
    if not ok:
        print("   ⚠ 불일치 상태로는 (ii) 값을 신뢰할 수 없다. 여기서 멈춘다.", flush=True)
        (OUT / "12ii-self-entry-grid.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]

    def stats(take):
        nets = [net(t["gain"]) for t in take]
        eqs = [slot_sim.sim(take, seed=s)["equity_pct"] for s in range(N_PAIR)]
        lo, hi = band(eqs[:N_LEVEL])
        segs = {}
        for sn, y0, y1 in SEGMENTS:
            v = [net(t["gain"]) for t in take if y0 <= t["year"] <= y1]
            segs[sn] = {"n": len(v), "mean": st.mean(v) if v else None}
        # 연도별 거래당 + 한 해씩 뺀 값 (12번 (i)의 "2021 한 해에 실려 있다" 확인용)
        by_year = {y: [net(t["gain"]) for t in take if t["year"] == y] for y in YEARS}
        drop_year = {y: (st.mean([v for yy, vs in by_year.items() if yy != y for v in vs])
                         if any(yy != y and vs for yy, vs in by_year.items()) else None)
                     for y in YEARS}
        return {"n": len(take), "per_trade": st.mean(nets),
                "win_rate": sum(1 for t in take if t["result"] == "win") / len(take) * 100,
                "slot5_median": st.median(eqs[:N_LEVEL]), "slot5_band": [lo, hi],
                "band_width": hi - lo, "eqs": eqs, "nets": nets, "segments": segs,
                "by_year": {y: (st.mean(v) if v else None) for y, v in by_year.items()},
                "n_by_year": {y: len(v) for y, v in by_year.items()},
                "drop_year": drop_year, "take": take}

    print("\n[24칸 · 자체 진입 판] 기준선은 +20/−10 자체 진입", flush=True)
    base = stats(base_take)
    print("  기준 +20/−10  진입 %4d · 거래당 %+7.4f%%p · 승률 %5.2f%% · "
          "슬롯5 중앙 %+7.1f%% · 폭 %6.1f%%p"
          % (base["n"], base["per_trade"], base["win_rate"],
             base["slot5_median"], base["band_width"]), flush=True)

    cells = {}
    for tg in TARGETS:
        for sp in STOPS:
            take = replay_entries(cands, tg, sp)
            s = stats(take)
            d = [s["eqs"][i] - base["eqs"][i] for i in range(N_PAIR)]
            key = "+%d/-%d" % (tg, sp)
            cells[key] = {k: v for k, v in s.items() if k not in ("eqs", "nets", "take")}
            cells[key].update({
                "n_vs_base": s["n"] - base["n"],
                "per_trade_vs_base": s["per_trade"] - base["per_trade"],
                "win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
                "diff_median": st.median(d), "diff_ci": list(ci(d))})
            c = cells[key]
            print("  %-8s 진입 %4d (%+5d) · 거래당 %+7.4f (%+7.4f) · 승률 %5.2f%% · "
                  "슬롯5 %+7.1f%% · 폭 %6.1f · 우세율(참고) %5.1f%% · 차이중앙 %+7.1f%%p"
                  % (key, c["n"], c["n_vs_base"], c["per_trade"], c["per_trade_vs_base"],
                     c["win_rate"], c["slot5_median"], c["band_width"],
                     c["win_pct"], c["diff_median"]), flush=True)
    res["base"] = {k: v for k, v in base.items() if k not in ("eqs", "nets", "take")}
    res["cells"] = cells

    # ── ★ (i)의 핵심 소견 확인: 플러스 칸이 2021 한 해에 실려 있는가 ──
    print("\n[한 해 제거 · 거래당 순수익] (i)에서는 플러스 여섯 칸이 6/6 전부 2021을 빼면 마이너스였다",
          flush=True)
    plus = [(k, v) for k, v in cells.items() if v["per_trade"] > 0]
    print("  자체 진입 판에서 거래당 플러스인 칸: **%d개 / 24**" % len(plus), flush=True)
    flip21 = 0
    for k, v in sorted(plus, key=lambda kv: -kv[1]["per_trade"]):
        d21 = v["drop_year"]["2021"]
        worst = min((yy for yy in YEARS if v["drop_year"][yy] is not None),
                    key=lambda yy: v["drop_year"][yy])
        flip21 += (d21 is not None and d21 <= 0)
        print("   %-8s 전체 %+7.4f · 2021 제거 %+7.4f %s · 최악연도(%s) 제거 %+7.4f %s"
              % (k, v["per_trade"], d21, "(부호 반전)" if d21 <= 0 else "(유지)",
                 worst, v["drop_year"][worst],
                 "(부호 반전)" if v["drop_year"][worst] <= 0 else "(유지)"), flush=True)
    print("  → **2021을 빼면 부호가 뒤집히는 칸 %d개 / 플러스 %d개**" % (flip21, len(plus)),
          flush=True)
    res["drop_2021"] = {"n_plus_cells": len(plus), "n_flip_on_2021": flip21,
                        "cells": {k: {"per_trade": v["per_trade"],
                                      "drop_2021": v["drop_year"]["2021"],
                                      "by_year": v["by_year"]} for k, v in plus}}

    # ── 진입 증감이 어디서 오는가 ──
    print("\n[진입 증감의 원천] 손절폭이 좁을수록 빨리 결착 → 겹침이 풀려 더 산다", flush=True)
    tbl = {}
    for sp in STOPS:
        row = {}
        for tg in TARGETS:
            row["+%d" % tg] = cells["+%d/-%d" % (tg, sp)]["n"]
        tbl["-%d" % sp] = row
        print("  손절 -%2d%% : %s" % (sp, " ".join("%d→%d" % (tg, row["+%d" % tg])
                                                 for tg in TARGETS)), flush=True)
    res["n_by_cell"] = tbl

    # ── M29-3 ──
    same = sum(1 for t in cands
               if len({t["res"][(tg, sp)][0] for tg in TARGETS for sp in STOPS}) == 1)
    res["m29_3"] = {"same_resolve_all_cells": same, "pct": same / len(cands) * 100}
    print("\n[M29-3] 24칸 **전부에서 결착일이 같은** 후보 %d건 / %d = **%.1f%%** — "
          "그 건들에는 청산 규칙이 닿지 않는다"
          % (same, len(cands), same / len(cands) * 100), flush=True)

    (OUT / "12ii-self-entry-grid.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12ii-self-entry-grid.json")


if __name__ == "__main__":
    main()
