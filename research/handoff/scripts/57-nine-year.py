# -*- coding: utf-8 -*-
"""57번 — **미국 9년: 실효성이 있는가**. 사전등록: `tasks/57-nine-year.md`

🚨 이 스크립트는 **38번의 확인 구간(2017-09~2021-01)을 쓴다.** 이후 표본 밖은 없다.
🚨 `BT_Y0=2017` 로 «명시해서» 돌린다. 안 주면 옛 5.6년 범위가 돈다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 57-nine-year.py
"""
from __future__ import annotations

import importlib.util as _u
import json
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

_s2 = _u.spec_from_file_location("r54", HERE / "54-exposure-benchmark.py")
r54 = _u.module_from_spec(_s2)
_s2.loader.exec_module(r54)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200

DEV0, DEV1 = "2021-02-01", "2026-12-31"      # 개발 구간 (이미 본 자료)
HLD0, HLD1 = "2017-01-01", "2021-01-31"      # 확인 구간 (**새 정보는 여기뿐**)
REGIMES_D = (("2018 조정", "2018-10-01", "2018-12-31"),
             ("2020 코로나 폭락", "2020-02-19", "2020-03-23"),
             ("2020 회복", "2020-03-24", "2020-12-31"))


def summarize(ev, spx, cal, label, tag, res):
    """한 부분집합의 자산·거래당·노출맞춤 벤치마크."""
    if len(ev) < 30:
        print("  %-14s 진입 %d건 — **표본 부족, 판정 안 함**" % (label, len(ev)), flush=True)
        return
    pt = r41.per_trade(ev)
    lo, hi, mde = r41.boot(ev)
    rows = []
    for s in range(N_SEED):
        r = r54.sim_calendar(ev, cal, seed=s)
        bm, _ = r54.matched_bench(r["expo"], spx)
        vol, shp = r54.vol_sharpe(r["daily"])
        rows.append({"eq": r["equity_pct"], "bm": bm, "gap": r["equity_pct"] - bm,
                     "w": st.mean(w for _d, w in r["expo"]),
                     "mdd": r54.mdd_of(r["daily"]), "n": r["n_filled"],
                     "sharpe": shp})
    eqs = sorted(x["eq"] for x in rows)
    g = sorted(x["gap"] for x in rows)
    spx_r = (spx[cal[-1]] / spx[cal[0]] - 1) * 100
    d = {"label": label, "n_entry": len(ev),
         "per_trade": st.mean(pt), "pt_lo": lo, "pt_hi": hi, "pt_mde": mde,
         "pt_excl0": (lo > 0) or (hi < 0),
         "equity_median": st.median(eqs), "equity_p5": eqs[int(N_SEED * .05)],
         "bench_median": st.median(x["bm"] for x in rows),
         "gap_median": st.median(g), "gap_pos": 100.0 * sum(1 for x in g if x > 0) / N_SEED,
         "expo": st.median(x["w"] for x in rows), "mdd": st.median(x["mdd"] for x in rows),
         "sharpe": st.median(x["sharpe"] for x in rows),
         "n_filled": st.median(x["n"] for x in rows), "spx": spx_r,
         "spx_mdd": r54.mdd_of([(x, spx[x]) for x in cal]), "days": len(cal)}
    res[tag] = d
    print("  %-14s 진입 %5d · 체결 %3d · 거래당 **%+.4f%%** [%+.3f~%+.3f] MDE ±%.3f → %s"
          % (label, d["n_entry"], d["n_filled"], d["per_trade"], lo, hi, mde,
             "**0 배제**" if d["pt_excl0"] else "0 포함"), flush=True)
    print("  %-14s 자산 중앙 %+8.2f%% (하단 %+8.2f%%) · S&P %+7.2f%% · "
          "노출맞춤 %+7.2f%% → 격차 %+8.2f%%p · 노출 %.0f%% · MDD %.1f%% (S&P %.1f%%)"
          % ("", d["equity_median"], d["equity_p5"], d["spx"], d["bench_median"],
             d["gap_median"], d["expo"] * 100, d["mdd"], d["spx_mdd"]), flush=True)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다. 옛 범위로 돈다 — 멈춘다.", flush=True)
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    idx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))
    spx = idx["US500"]

    print("=" * 78, flush=True)
    print("57번 — **미국 9년** (사전등록 tasks/57) · 🚨 확인 구간을 쓴다", flush=True)
    print("=" * 78, flush=True)
    nby = {y: len(ps) for y, ps in sorted(by.items())}
    print("연도별 방아쇠 %s" % nby, flush=True)
    if any(v == 0 for v in nby.values()):
        print("🚨 방아쇠가 0 인 해가 있다 — 관문 3 미통과. 멈춘다.", flush=True)
        return 3

    RES = {"n_paths": sum(nby.values()), "by_year_triggers": nby}
    for cname, ft, fs in (("종가판", "close", "close"), ("실집행", "limit", "market")):
        r41.TARGET_FILL, r41.STOP_FILL = ft, fs
        for vname, fn, vlabel, _ in r41.VARIANTS:
            if vname not in ("0회차", "1a"):
                continue
            ev, _b = r41.replay(by, fn)
            with r41.Cost(0.0, 0.0):
                print("\n" + "─" * 78, flush=True)
                print("[%s · %s] %s — 진입 **%d건**" % (cname, vname, vlabel, len(ev)),
                      flush=True)

                def sub(a, b):
                    return [e for e in ev if a <= e["entry_date"] <= b]

                def cal_of(sel):
                    if not sel:
                        return []
                    lo = min(e["entry_date"] for e in sel)
                    hi = max((e["resolve_date"] or e["entry_date"]) for e in sel)
                    return [d for d in sorted(spx) if lo <= d <= hi]

                pre = "%s|%s" % (cname, vname)
                summarize(ev, spx, cal_of(ev), "9년 전체", pre + "|all", RES)
                print("  " + "·" * 60, flush=True)
                print("  ★ C(주판정) — 구간을 갈라 «부호가 재현되나»", flush=True)
                for nm, a, b, tag in (("개발(본 자료)", DEV0, DEV1, "dev"),
                                      ("**확인(새 정보)**", HLD0, HLD1, "hld")):
                    summarize(sub(a, b), spx, cal_of(sub(a, b)), nm, pre + "|" + tag, RES)
                # ── 연도별 ────────────────────────────────────────────────
                if cname == "종가판":
                    print("  " + "·" * 60, flush=True)
                    print("  연도별 거래당(진입 집합)", flush=True)
                    byy = defaultdict(list)
                    for e, v in zip(ev, r41.per_trade(ev)):
                        byy[e["entry_date"][:4]].append(v)
                    line = []
                    for y in sorted(byy):
                        line.append("%s %+.3f%%(n=%d)" % (y, st.mean(byy[y]), len(byy[y])))
                    print("    " + " · ".join(line), flush=True)
                    RES[pre + "|by_year"] = {y: [st.mean(v), len(v)] for y, v in byy.items()}
                # ── D. 국면 서술 ──────────────────────────────────────────
                if vname == "1a" and cname == "종가판":
                    print("  " + "·" * 60, flush=True)
                    print("  D. 국면 서술 (문턱 없음)", flush=True)
                    for nm, a, b in REGIMES_D:
                        sel = sub(a, b)
                        if not sel:
                            print("    %-16s 진입 0건" % nm, flush=True)
                            continue
                        v = r41.per_trade(sel)
                        sp = (spx[max(d for d in spx if d <= b)]
                              / spx[min(d for d in spx if d >= a)] - 1) * 100
                        print("    %-16s 진입 %4d · 거래당 %+7.3f%% · 승률 %.1f%% "
                              "· S&P %+.1f%%"
                              % (nm, len(sel), st.mean(v),
                                 100.0 * sum(1 for e in sel if e["result"] == "win") / len(sel),
                                 sp), flush=True)
                        RES["%s|%s" % (pre, nm)] = {"n": len(sel), "pt": st.mean(v), "spx": sp}

    (OUT / "57-nine-year.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 57-nine-year.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
