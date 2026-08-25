# -*- coding: utf-8 -*-
"""59번 — **국면 필터를 1a 위에 직접, 9년으로**. 사전등록: `tasks/59-regime-9y.md`

🚨 짝비교는 **자료 축**(`dataaxis`)이다. 58번에서 seed 축으로 재서 없는 통과를 보고했다.
🚨 국면은 **스캔일 종가**까지만 본다 (하네스는 이튿날 진입 → 룩어헤드 아님).

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 59-regime-9y.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                         # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_STREAM = da.N_STREAM
HLD0, HLD1 = "2017-01-01", "2021-01-31"


def ma_flags(curve, wins=(20, 50, 200)):
    """날짜 → {창: 그날 종가가 그 창 이평 «이상»인가}. 자료 부족이면 None."""
    d = [x[0] for x in curve]
    v = [x[1] for x in curve]
    out = {}
    for i, day in enumerate(d):
        f = {}
        for w in wins:
            f[w] = None if i + 1 < w else (v[i] >= st.mean(v[i - w + 1:i + 1]))
        out[day] = f
    return out


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.", flush=True)
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us9y.json").read_text(encoding="utf-8"))
    idx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))
    spx = idx["US500"]
    ef = ma_flags(eqw["curve_harness_filt"])
    sf_ = ma_flags([(k, spx[k]) for k in sorted(spx)])
    print("=" * 80, flush=True)
    print("59번 — **국면 필터 · 1a 위에 직접 · 9년** (사전등록 tasks/59)", flush=True)
    print("=" * 80, flush=True)
    print("등가중 %d일 · S&P %d일" % (len(ef), len(sf_)), flush=True)

    FILTERS = (
        ("R0 없음", None),
        ("R1 등가중<20MA", lambda d: (ef.get(d, {}).get(20) is not False)),
        ("R2 S&P<50MA", lambda d: (sf_.get(d, {}).get(50) is not False)),
        ("R3 S&P<200MA", lambda d: (sf_.get(d, {}).get(200) is not False)),
    )
    # 국면이 «켜진» 날 비율 (서술)
    on20 = sum(1 for f in ef.values() if f[20]) / len(ef) * 100
    on50 = sum(1 for f in sf_.values() if f[50]) / len(sf_) * 100
    on200 = sum(1 for f in sf_.values() if f[200]) / len(sf_) * 100
    print("국면이 «켜진» 날 — 등가중≥20MA %.1f%% · S&P≥50MA %.1f%% · S&P≥200MA %.1f%%"
          % (on20, on50, on200), flush=True)

    RES = {}
    for vname, fn, vlabel, _h in r41.VARIANTS:
        if vname != "1a":
            continue
        r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
        ev_all, _b = r41.replay(by, fn)
        for rname, fb, fsell in r41.REGIMES:
            print("\n" + "─" * 80, flush=True)
            print("[1a · %s] %s" % (rname, vlabel), flush=True)
            cur, info = {}, {}
            for fname, ff in FILTERS:
                # 🚨 국면은 «스캔일» 로 본다
                ev = ev_all if ff is None else [e for e in ev_all if ff(e["scan_date"])]
                with r41.Cost(fb, fsell):
                    rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash")
                          for i in range(N_STREAM)]
                cur[fname] = [r["curve"] for r in rs]
                eq = sorted(r["equity_pct"] for r in rs)
                info[fname] = {"n_entry": len(ev),
                               "n_filled": st.median(r["n_filled"] for r in rs),
                               "eq": st.median(eq), "p5": eq[0], "p95": eq[-1],
                               "mdd": st.median(r["mdd_pct"] for r in rs),
                               "fpt": st.median(r["filled_per_trade"] for r in rs)}
                i2 = info[fname]
                print("  %-16s 진입 %5d (%.0f%%) · 체결 %3d · 체결분거래당 %+.3f%% · "
                      "자산중앙 %+8.2f%% · MDD %.1f%%"
                      % (fname, i2["n_entry"], 100.0 * i2["n_entry"] / len(ev_all),
                         i2["n_filled"], i2["fpt"], i2["eq"], i2["mdd"]), flush=True)
            print("  ── A. **자료 축** 짝비교 (vs R0) — 블록 20/40/80 중 가장 넓은 구간 ──",
                  flush=True)
            for fname, _ff in FILTERS[1:]:
                sw = da.sweep(cur[fname], cur["R0 없음"])
                w = sw["_widest"]
                r = sw[w]
                print("    %-16s 블록%-3d 중앙 %+8.2f%%  95%% %+8.2f ~ %+8.2f  → **%s**"
                      % (fname, w, r["median"], r["lo"], r["hi"],
                         "0 배제" if r["excl0"] else "0 포함"), flush=True)
                RES["1a|%s|%s" % (rname, fname)] = {**info[fname], "block": w,
                                                    "median": r["median"], "lo": r["lo"],
                                                    "hi": r["hi"], "excl0": r["excl0"]}
            # ── B. 확인 구간 단독 ────────────────────────────────────────
            if rname == r41.REGIMES[0][0]:
                print("  ── B. **확인 구간 단독** (2017-09 ~ 2021-01) ──", flush=True)
                curh = {}
                for fname, ff in FILTERS:
                    ev = [e for e in ev_all if HLD0 <= e["entry_date"] <= HLD1
                          and (ff is None or ff(e["scan_date"]))]
                    with r41.Cost(fb, fsell):
                        rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash")
                              for i in range(N_STREAM)]
                    curh[fname] = [r["curve"] for r in rs]
                    print("    %-16s 진입 %4d · 자산중앙 %+8.2f%%"
                          % (fname, len(ev), st.median(r["equity_pct"] for r in rs)),
                          flush=True)
                for fname, _ff in FILTERS[1:]:
                    sw = da.sweep(curh[fname], curh["R0 없음"])
                    w = sw["_widest"]
                    r = sw[w]
                    print("    %-16s 짝비교 중앙 %+8.2f%%  95%% %+8.2f ~ %+8.2f  → %s"
                          % (fname, r["median"], r["lo"], r["hi"],
                             "**0 배제**" if r["excl0"] else "0 포함"), flush=True)
                    RES["1a|확인|%s" % fname] = {"median": r["median"], "lo": r["lo"],
                                                 "hi": r["hi"], "excl0": r["excl0"]}
    (OUT / "59-regime-9y.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 59-regime-9y.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
