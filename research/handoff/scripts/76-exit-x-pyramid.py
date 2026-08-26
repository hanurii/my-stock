# -*- coding: utf-8 -*-
"""76 — **「청산」과 「피라미딩」은 같은 질문이었다**
사전등록 `tasks/76-exit-x-pyramid.md` (커밋 `855090af`)

🚨 예측 P 를 «먼저» 등록했다 — 「덜 일찍 파는」 청산이면 (피라미딩 − 한 번에)가
   1a 판(**−67.79%p**)보다 «위»로 올라간다. 아니면 「청산 탓」이라는 변명이 죽는다.
🚨 주지표 = 노출 맞춘 짝비교. 오래 들면 노출이 «기계적으로» 오른다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/76-exit-x-pyramid.py [--quick]
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
import pyr_trigger as pt                                      # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r75a", HERE / "75a-mde.py")
r75a = _u.module_from_spec(_s)
_s.loader.exec_module(r75a)
r74, r41 = r75a.r74, r75a.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS = r74.COST, r74.SLOTS
STOP, TARGET = r74.STOP, r74.TARGET
BASE_CAP = 0.20
N_SEED = 200
TRIG = dict(h_lag=True, stay_on="close", px_round=2)          # 방아쇠 + 가격 격자
HALF_EXIT = dict(exit_mode="half_trail")
RUN_EXIT = dict(exit_mode="runner", run_trail=25.0)           # 67번 격자의 끝
RUN15 = dict(exit_mode="runner", run_trail=15.0)              # 부수 — 격자 안쪽

ONE, PYR = (1.0,), (1.0, 0.5)
VARIANTS = (
    ("A0 지금(1a·한번에)", ONE, HALF_EXIT),
    ("A1 1a·1.5배",       PYR, HALF_EXIT),
    ("B0 끝까지·한번에",    ONE, RUN_EXIT),
    ("★ B1 끝까지·1.5배",  PYR, RUN_EXIT),
    ("B0′ −15%·한번에",    ONE, RUN15),
    ("B1′ −15%·1.5배",    PYR, RUN15),
)
CAPS = (0.16, 0.20, 0.24, 0.28, 0.32, 0.36)


def replay(by2, shares, ekw, tkw=None):
    ev, blk = [], 0
    allT = (True,) * (len(shares) - 1)
    kw = dict(TRIG if tkw is None else tkw, **ekw)
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blk += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 shares=shares, add_stop="floor_entry", **kw)
            t["_path"] = p
            open_until[c] = t["masks"][allT]["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blk


def mfe_capture(ev):
    """관문 ③ — 「최고점의 몇 %를 챙기나」. 65번(38%)과 같은 자리."""
    mfes, rels, holds = [], [], []
    for t in ev:
        p, m = t["_path"], t["masks"][(True,) * (len(t["shares"]) - 1)]
        rd = m["resolve_date"]
        try:
            j = p["d"].index(rd)
        except ValueError:
            j = len(p["d"]) - 1
        hs = [x for x in p["h"][:j + 1] if x is not None]
        if not hs:
            continue
        epx = t["entry_px"]
        mfe = (max(hs) / epx - 1) * 100
        tot = sum(w for _d, _px, w, _k in m["lots"])
        a = sum(px * w for _d, px, w, _k in m["lots"]) / max(1e-12, tot)
        real = sum(fr * (px / a - 1) for _d, fr, px in m["exits"]) * 100
        mfes.append(mfe)
        rels.append(real)
        holds.append(j)
    cap = 100.0 * st.mean(rels) / max(1e-9, st.mean(mfes))
    return {"mfe": st.mean(mfes), "real": st.mean(rels), "capture": cap,
            "hold": st.median(holds), "n": len(mfes)}


def sim(ev, cap, n_seed):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=1.0, cap=cap,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def summ(rs, n):
    eq = sorted(x["equity_pct"] for x in rs)
    return {"equity": st.median(eq), "p5": eq[int(n * .05)],
            "mdd": st.median(x["mdd_pct"] for x in rs),
            "n_filled": st.median(x["n_filled"] for x in rs),
            "expo": st.median(x["expo_mean"] for x in rs),
            "win": st.median(x["win_rate"] for x in rs),
            "conc": st.median(x["conc_median"] for x in rs),
            "added": st.median(x["n_added"] for x in rs)}


def match_on(curve_tbl, target_expo):
    return min(curve_tbl, key=lambda k: abs(curve_tbl[k]["expo"] - target_expo))


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2
    n_seed = 20 if "--quick" in sys.argv else N_SEED
    print("=" * 104, flush=True)
    print("76 — 「청산」과 「피라미딩」은 같은 질문이었다 (사전등록 tasks/76)", flush=True)
    print("=" * 104, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d · 우대수수료 %s\n" % (n_all, n_sel, n_seed, COST),
          flush=True)

    # ── 관문 ① ─────────────────────────────────────────────────────────
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, STOP, TARGET))
    ev_n, _b2 = replay(by2, ONE, HALF_EXIT, dict(h_lag=True, stay_on="close"))
    worst = 0.0
    with r41.Cost(*COST):
        for s in range(min(20, n_seed)):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            worst = max(worst, abs(a - b) / max(1e-12, abs(a)))
    print("관문 ①  한 트랜치·1a·반올림 끈 판 = sim_frac  최대 상대오차 %.3e → **%s**\n"
          % (worst, "통과" if worst < 1e-9 else "🚨 미통과"), flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    res, curves, evs, mfe = {}, {}, {}, {}
    print("  %-20s %6s %5s %11s %11s %8s %6s %6s %6s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률", "노출", "증액"),
          flush=True)
    print("  " + "─" * 92, flush=True)
    for nm, shares, ekw in VARIANTS:
        ev, _blk = replay(by2, shares, ekw)
        evs[nm] = ev
        mfe[nm] = mfe_capture(ev)
        rs = sim(ev, BASE_CAP, n_seed)
        res[nm] = summ(rs, n_seed)
        res[nm]["n_entry"] = len(ev)
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-20s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%% %6d"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["expo"], r["added"]), flush=True)

    # ── 관문 ③ — MFE 포획률 ────────────────────────────────────────────
    print("\n관문 ③  「최고점의 몇 %를 챙기나」 (65번 실측 38%) · 진입 집합 · 단순평균",
          flush=True)
    print("  %-20s %9s %9s %9s %8s" % ("변형", "MFE", "실현", "포획률", "보유중앙"), flush=True)
    for nm, _s2, _e in VARIANTS:
        m = mfe[nm]
        print("  %-20s %+8.1f%% %+8.1f%% %8.1f%% %7d일"
              % (nm, m["mfe"], m["real"], m["capture"], m["hold"]), flush=True)

    # ── 노출 곡선 (A0·B0 각각) ─────────────────────────────────────────
    print("\n★ 노출 맞춘 대조 — 「한 번에」를 크게/작게 사게 만든 곡선", flush=True)
    big, bigc = {}, {}
    for base in ("A0 지금(1a·한번에)", "B0 끝까지·한번에"):
        tag = base.split()[0]
        for c in CAPS:
            k = "%s cap %.2f" % (tag, c)
            rs = sim(evs[base], c, n_seed)
            big[k] = summ(rs, n_seed)
            bigc[k] = [x["curve"] for x in rs]
        row = {k: v for k, v in big.items() if k.startswith(tag)}
        print("  [%s] " % tag + " · ".join(
            "%.2f→노출%.1f%%/%+.0f%%" % (float(k.split()[-1]), v["expo"], v["equity"])
            for k, v in row.items()), flush=True)

    # ── ★ 예측 P ────────────────────────────────────────────────────────
    A0, A1 = res["A0 지금(1a·한번에)"], res["A1 1a·1.5배"]
    B0, B1 = res["B0 끝까지·한번에"], res["★ B1 끝까지·1.5배"]
    tblA = {k: v for k, v in big.items() if k.startswith("A0")}
    tblB = {k: v for k, v in big.items() if k.startswith("B0")}
    mA, mB = match_on(tblA, A1["expo"]), match_on(tblB, B1["expo"])
    dA = A1["equity"] - big[mA]["equity"]
    dB = B1["equity"] - big[mB]["equity"]
    print("\n" + "─" * 104, flush=True)
    print("★ 예측 P — 「덜 일찍 파는」 청산이면 (피라미딩 − 한 번에)가 «위»로 올라간다",
          flush=True)
    print("  1a 판   A1 %+.2f%% vs %s %+.2f%% (노출 %.1f vs %.1f)  →  **%+.2f%%p**"
          % (A1["equity"], mA, big[mA]["equity"], A1["expo"], big[mA]["expo"], dA),
          flush=True)
    print("  끝까지  B1 %+.2f%% vs %s %+.2f%% (노출 %.1f vs %.1f)  →  **%+.2f%%p**"
          % (B1["equity"], mB, big[mB]["equity"], B1["expo"], big[mB]["expo"], dB),
          flush=True)
    print("  → 예측 P: %+.2f%%p > %+.2f%%p 인가  →  **%s**"
          % (dB, dA, "통과 — 청산이 바뀌면 피라미딩이 덜 나빠진다" if dB > dA
             else "**미통과 — 「청산 탓」이라는 변명이 죽는다**"), flush=True)

    # ── ★ C: 청산 축 단독 ───────────────────────────────────────────────
    mC = match_on(tblA, B0["expo"])
    dC = B0["equity"] - big[mC]["equity"]
    print("\n★ C — 청산 축 «단독» (한 번에 사기끼리 · 노출 맞춤)", flush=True)
    print("  B0 %+.2f%% (노출 %.1f) vs %s %+.2f%% (노출 %.1f)  →  **%+.2f%%p** → **%s**"
          % (B0["equity"], B0["expo"], mC, big[mC]["equity"], big[mC]["expo"], dC,
             "통과" if dC > 0 else "미통과"), flush=True)

    # ── A: 필요 T 먼저, 그 다음 자료 축 ────────────────────────────────
    print("\n🚨 A 판정 «전» — 답할 수 있는 질문인가", flush=True)
    swB1 = da.sweep(curves["★ B1 끝까지·1.5배"], bigc[mB])
    swC = da.sweep(curves["B0 끝까지·한번에"], bigc[mC])
    for lbl, sw in (("B1 − 맞춘 한번에", swB1), ("★ 청산축 B0 − 맞춘 A0", swC)):
        m = r75a.mde(sw)
        for b in da.BLOCKS:
            v = m[b]
            if v is None:
                continue
            print("  %-20s 블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (lbl if b == da.BLOCKS[0] else "", b, v["median"], v["T"], v["years"],
                     "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)
        print(da.fmt(sw, lbl), flush=True)

    (OUT / "76-exit-x-pyramid.json").write_text(json.dumps(
        {"res": res, "big": big, "mfe": mfe, "match": {"A": mA, "B": mB, "C": mC},
         "dA": dA, "dB": dB, "dC": dC, "n_seed": n_seed}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: 76-exit-x-pyramid.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
