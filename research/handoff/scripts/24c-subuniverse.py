# -*- coding: utf-8 -*-
"""24c — 축소 유니버스 결과 분석. 사전등록 폐기 기준 A·B·C로 채점한다.

사전등록: research/handoff/results/24c-subuniverse.md (결과 보기 전에 작성)
실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/24c-subuniverse.py
난수 seed: 슬롯 순서 0~199 · 날짜 블록 240300
"""
from __future__ import annotations
import importlib.util, json, random, statistics as st, sys
from collections import defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
SUB = BT / "sub"
OUT = BT / "out"
N_SEED, MDE_K = 200, 2.80
CFGS = [(500, 1), (500, 2), (1000, 1), (1000, 2), (2000, 1)]
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs); return s[int(len(s)*lo/100)], s[int(len(s)*hi/100)-1]


def load(files):
    tr, seen, nev, ncand = [], set(), [], 0
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        for r in d.get("per_date", []):
            nev.append(r["n_eval"]); ncand += r["n_candidates"]
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen: continue
            seen.add(k)
            tr.append({"code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
                       "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"] or e["entry_date"],
                       "gain": e["gain_at_resolve_pct"], "result": e["result"],
                       "year": int(e["entry_date"][:4])})
    return tr, nev, ncand


def stats(tr, label):
    nets = [slot_sim.net(t["gain"]) for t in tr]
    eqs = [slot_sim.sim(tr, seed=s) for s in range(N_SEED)]
    e = [x["equity_pct"] for x in eqs]
    return {"label": label, "n": len(tr), "per_trade": st.mean(nets),
            "sd": st.pstdev(nets),
            "win_rate": sum(1 for t in tr if t["result"] == "win")/len(tr)*100,
            "slot5_median": st.median(e), "slot5_band": list(ci(e, 5, 95)),
            "n_filled": st.median([x["n_filled"] for x in eqs]),
            "mdd": st.median([x["mdd_pct"] for x in eqs])}


def main():
    full, fev, fcand = load([BT / ("bt_%d.json" % y) for y in YEARS])
    F = stats(full, "전수")
    print("전수: 거래 %d · 거래당 %+.4f%%p · SD %.2f · 승률 %.2f%% · 슬롯5 %+.2f%% · 체결 %.0f · n_eval 중앙 %.0f · 후보 %d"
          % (F["n"], F["per_trade"], F["sd"], F["win_rate"], F["slot5_median"],
             F["n_filled"], st.median(fev), fcand), flush=True)
    res = {"full": F, "full_n_eval_median": st.median(fev), "full_n_cand": fcand, "cells": []}
    print("\n%-12s %6s %7s %10s %10s %9s %9s %10s %9s"
          % ("설정", "거래", "후보", "거래당", "차이(vs전수)", "MDE", "부호", "슬롯5", "n_eval"), flush=True)
    rows = {}
    for N, sd_ in CFGS:
        files = [SUB / ("n%ds%d_%d.json" % (N, sd_, y)) for y in YEARS]
        if not all(Path(f).exists() for f in files):
            print("  n%ds%d — 파일 없음" % (N, sd_)); continue
        tr, nev, ncand = load(files)
        S = stats(tr, "N=%d seed%d" % (N, sd_))
        diff = S["per_trade"] - F["per_trade"]
        mde = MDE_K * sqrt(F["sd"]**2/F["n"] + S["sd"]**2/S["n"])
        S.update({"N": N, "seed": sd_, "diff": diff, "MDE": mde, "n_cand": ncand,
                  "n_eval_median": st.median(nev),
                  "A_pass": bool(abs(diff) <= mde),
                  "B_pass": bool((S["per_trade"] > 0) == (F["per_trade"] > 0))})
        rows.setdefault(N, []).append(S)
        res["cells"].append(S)
        print("  %-12s %6d %7d %+9.4f %+11.4f %8.4f %8s %+9.2f%% %8.0f"
              % (S["label"], S["n"], ncand, S["per_trade"], diff, mde,
                 "같음" if S["B_pass"] else "**다름**", S["slot5_median"], S["n_eval_median"]),
              flush=True)
    print("\n%-8s %10s %12s %12s %8s %8s %8s"
          % ("N", "seed간 차이", "전수대비 |차이|", "C(뽑기<전수)", "A", "B", "판정"), flush=True)
    for N, arr in rows.items():
        if len(arr) < 2:
            gap = None; cstr = "seed 1개 — 못 잼"
        else:
            gap = abs(arr[0]["per_trade"] - arr[1]["per_trade"])
            mx = max(abs(a["diff"]) for a in arr)
            cstr = "**%s**" % ("통과" if gap <= mx else "실패")
        A = all(a["A_pass"] for a in arr); B = all(a["B_pass"] for a in arr)
        Cp = (gap is not None and gap <= max(abs(a["diff"]) for a in arr))
        verdict = "폐기" if not (A and B and (Cp if gap is not None else True)) else "유지"
        print("  %-8d %10s %12.4f %12s %8s %8s %8s"
              % (N, ("%.4f" % gap) if gap is not None else "—",
                 max(abs(a["diff"]) for a in arr), cstr,
                 "통과" if A else "**실패**", "통과" if B else "**실패**", "**%s**" % verdict), flush=True)
        res.setdefault("verdict", {})[str(N)] = {
            "seed_gap": gap, "max_abs_diff": max(abs(a["diff"]) for a in arr),
            "A": A, "B": B, "C": Cp if gap is not None else None, "verdict": verdict}
    (OUT / "24c-subuniverse.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/24c-subuniverse.json")


if __name__ == "__main__":
    main()
