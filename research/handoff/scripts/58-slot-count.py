# -*- coding: utf-8 -*-
"""58번 — **칸이 병목인가**. 사전등록: `tasks/58-slot-count.md`

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 58-slot-count.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                               # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
SLOTS = (4, 5, 6, 8, 12, 20)          # 🚨 사전등록에서 고정. 늘리지 않는다.
BASE = 5
N_BOOT = 2000
BOOT_SEED = 580825


def paired_ci(diffs):
    """짝비교 — seed 축 부트스트랩. 같은 seed 끼리 뺀 값의 분포."""
    rnd = random.Random(BOOT_SEED)
    n = len(diffs)
    ms = []
    for _ in range(N_BOOT):
        ms.append(st.mean(rnd.choice(diffs) for _ in range(n)))
    ms.sort()
    lo, hi = ms[int(N_BOOT * .025)], ms[int(N_BOOT * .975)]
    return lo, hi, (hi - lo) / 2


def run(ev, slots, regime):
    fb, fs = regime
    with r41.Cost(fb, fs):
        rs = [sf.sim_frac(ev, slots=slots, seed=s, sizing="cash")
              for s in range(N_SEED)]
    eq = sorted(r["equity_pct"] for r in rs)
    return {"rs": rs,
            "median": st.median(eq), "p5": eq[int(N_SEED * .05)],
            "p95": eq[int(N_SEED * .95)],
            "width": eq[int(N_SEED * .95)] - eq[int(N_SEED * .05)],
            "n_filled": st.median(r["n_filled"] for r in rs),
            "fpt": st.median(r["filled_per_trade"] for r in rs),
            "mdd": st.median(r["mdd_pct"] for r in rs),
            "win": st.median(r["win_rate"] for r in rs)}


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.", flush=True)
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"

    print("=" * 82, flush=True)
    print("58번 — **칸이 병목인가** (사전등록 tasks/58) · 미국 9년", flush=True)
    print("=" * 82, flush=True)
    RES = {}
    for vname, fn, vlabel, _h in r41.VARIANTS:
        if vname not in ("0회차", "1a"):
            continue
        ev, _b = r41.replay(by, fn)
        for rname, fb, fsell in r41.REGIMES:
            print("\n" + "─" * 82, flush=True)
            print("[%s · %s] %s — 진입 %d건" % (vname, rname, vlabel, len(ev)),
                  flush=True)
            print("  칸  체결   체결분거래당   자산중앙      5%하단     95%상단   "
                  "**폭**    MDD    vs 5칸 짝비교", flush=True)
            cells = {}
            for s in SLOTS:
                cells[s] = run(ev, s, (fb, fsell))
            base = cells[BASE]
            for s in SLOTS:
                c = cells[s]
                if s == BASE:
                    tail = "     (기준)"
                else:
                    d = [math.log1p(a["equity_pct"] / 100) - math.log1p(b["equity_pct"] / 100)
                         for a, b in zip(c["rs"], base["rs"])]
                    lo, hi, mde = paired_ci(d)
                    m = st.mean(d)
                    tail = ("  %+.4f [%+.4f~%+.4f] MDE±%.4f %s"
                            % (m, lo, hi, mde,
                               "**0배제**" if (lo > 0 or hi < 0) else "0포함"))
                    c["paired"] = {"mean": m, "lo": lo, "hi": hi, "mde": mde,
                                   "excl0": (lo > 0 or hi < 0)}
                print("  %2d  %4d   %+8.4f%%   %+9.2f%%  %+9.2f%%  %+9.2f%%  "
                      "%7.1f  %6.1f%%%s"
                      % (s, c["n_filled"], c["fpt"], c["median"], c["p5"],
                         c["p95"], c["width"], c["mdd"], tail), flush=True)
                RES["%s|%s|%d" % (vname, rname, s)] = {
                    k: v for k, v in c.items() if k != "rs"}
    (OUT / "58-slot-count.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 58-slot-count.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
