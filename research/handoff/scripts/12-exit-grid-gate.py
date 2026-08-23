# -*- coding: utf-8 -*-
"""12 (시작 관문) — 기존 청산 9칸을 01번 경로 자료로 재현해 대조.

지시서: research/handoff/tasks/12-exit-grid.md 1단계
사전등록: research/handoff/tasks/00-preregistration.md

한계(결과 파일에 그대로 적는다):
  하네스의 중복보유 차단(open_until)이 결착일에 의존해서 칸마다 **진입 집합이 다르다**.
  01번 경로는 기준선(+20/-10)의 진입 집합 3,681건뿐이므로, 각 칸에서 대조 가능한 것은
  '그 칸과 기준선의 교집합'뿐이다. 교집합 밖 건수도 함께 센다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12-exit-grid-gate.py
난수: 사용하지 않음(seed 없음)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"

CELLS = [
    ("+20/-10 (기준선)", 20.0, 10.0, "bt_*.json", ""),
    ("+15/-10", 15.0, 10.0, "t15s10_*.json", "exit/"),
    ("+20/-7", 20.0, 7.0, "t20s7_*.json", "exit/"),
    ("+25/-12", 25.0, 12.0, "t25s12_*.json", "exit/"),
    ("+30/-5", 30.0, 5.0, "t30s5_*.json", "exit/"),
    ("+30/-7", 30.0, 7.0, "t30s7_*.json", "exit/"),
    ("+30/-10", 30.0, 10.0, "t30s10_*.json", "exit/"),
    ("+40/-10", 40.0, 10.0, "t40s10_*.json", "exit/"),
    ("+50/-10", 50.0, 10.0, "t50s10_*.json", "exit/"),
    ("+40/-7 (2021년만)", 40.0, 7.0, "t40s7_*.json", "exit/"),
]


def replay(h, l, c, base, target_pct, stop_pct):
    """pivot_backtest.simulate_pivot_trade 와 동일한 선착 판정."""
    n = len(c)
    T = base * (1 + target_pct / 100)
    S = base * (1 - stop_pct / 100)

    def res(kind, i):
        return {"result": kind, "days_held": i,
                "gain_at_resolve_pct": round((c[i] / base - 1) * 100, 2),
                "max_gain_pct": round((max(h[:i + 1]) / base - 1) * 100, 2),
                "max_dd_pct": round((min(l[:i + 1]) / base - 1) * 100, 2)}

    hit_t, hit_s = h[0] >= T, l[0] <= S
    if hit_t and hit_s:
        return res("ambiguous", 0)
    if hit_t:
        return res("win", 0)
    if hit_s:
        return res("ambiguous", 0)
    for i in range(1, n):
        hit_t, hit_s = h[i] >= T, l[i] <= S
        if hit_t and hit_s:
            return res("ambiguous", i)
        if hit_t:
            return res("win", i)
        if hit_s:
            return res("loss", i)
    return res("unresolved", n - 1)


def main():
    paths = {}
    for f in sorted(OUT.glob("paths_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["paths"]:
            paths[(p["scan_date"], p["code"], p["pattern"])] = (
                p["entry_price"], p["h"], p["l"], p["c"])
        print("읽음 %s · 누적 %d" % (f.name, len(paths)), flush=True)

    report = []
    for label, tgt, stp, pat, folder in CELLS:
        files = sorted((BT / folder).glob(pat))
        rows = {"cell": label, "target": tgt, "stop": stp, "n_files": len(files)}
        n_cell = n_common = 0
        m = {"result": 0, "days_held": 0, "gain": 0, "max_gain": 0, "max_dd": 0,
             "entry_price": 0}
        mism = defaultdict(int)
        examples = []
        by_result = defaultdict(int)
        for f in files:
            d = json.loads(f.read_text(encoding="utf-8"))
            for e in d["events"]:
                n_cell += 1
                k = (e["scan_date"], e["code"], e["pattern"])
                if k not in paths:
                    continue
                n_common += 1
                base, h, l, c = paths[k]
                by_result[e["result"]] += 1
                r = replay(h, l, c, base, tgt, stp)
                chk = {
                    "result": (r["result"], e["result"]),
                    "days_held": (r["days_held"], e["days_held"]),
                    "gain": (r["gain_at_resolve_pct"], e["gain_at_resolve_pct"]),
                    "max_gain": (r["max_gain_pct"], e["max_gain_pct"]),
                    "max_dd": (r["max_dd_pct"], e["max_dd_pct"]),
                    "entry_price": (round(base, 2), e["entry_price"]),
                }
                bad = []
                for key, (mine, orig) in chk.items():
                    if mine == orig:
                        m[key] += 1
                    else:
                        mism[key] += 1
                        bad.append({"field": key, "mine": mine, "orig": orig})
                if bad and len(examples) < 20:
                    examples.append({"code": e["code"], "name": e.get("name"),
                                     "scan_date": e["scan_date"],
                                     "entry_date": e["entry_date"],
                                     "pattern": e["pattern"], "diffs": bad})
        rows.update({"n_cell_events": n_cell, "n_common": n_common,
                     "n_cell_only": n_cell - n_common,
                     "common_by_result": dict(by_result),
                     "match": m, "mismatch": dict(mism), "examples": examples})
        report.append(rows)
        print("%-20s 칸 %5d · 대조가능 %5d · 칸에만 %4d | 불일치 %s"
              % (label, n_cell, n_common, n_cell - n_common,
                 dict(mism) or "없음"), flush=True)

    (OUT / "12-exit-grid-gate.json").write_text(
        json.dumps({"n_paths": len(paths), "cells": report},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12-exit-grid-gate.json")


if __name__ == "__main__":
    main()
