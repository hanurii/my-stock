# -*- coding: utf-8 -*-
"""75 — **리버모어식 피라미딩: 「위에 얹어 크게 만든다」**
사전등록 `tasks/75-livermore-pyramid.md` (커밋 `40d4b8e6`)

🚨 `shares` 단위가 74번과 다르다 — 74번 «목표 대비 몫» / 75번 **«평소 한 칸 대비 배수»**.
🚨 주지표는 **노출 맞춘 짝비교**(§1). 안 맞춘 값은 참고로만.
🚨 A 판정 «전»에 75a 의 **필요 T** 를 먼저 찍는다 — 크게 1 을 넘으면 「못 답한다」가 결론.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/75-livermore.py [--quick]
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
BASE_CAP = 0.20              # 「평소 한 칸」 = 자산의 20%
N_SEED = 200
FIX = dict(h_lag=True, stay_on="close", px_round=2)   # §2 방아쇠 + §3① 가격 격자

# ── §2 변형 — 헤드라인 한 칸(★)은 값 보기 «전»에 고정됐다 ────────────────
VARIANTS = (
    ("P0 한 번에",     (1.0,),            "floor_entry", "대조 · 1.0배"),
    ("★ L1 1.5배",     (1.0, 0.5),        "floor_entry", "헤드라인"),
    ("L1-avgstop",     (1.0, 0.5),        "avg",         "부수 · 손절 축"),
    ("L2 1.75배",      (1.0, 0.5, 0.25),  "floor_entry", "부수 · 감소 증액"),
    ("L1-half(74판)",  (0.5, 0.5),        "floor_entry", "부수 · 74번 H′ 와 같은 판"),
)
CAPS = (0.20, 0.24, 0.28, 0.32, 0.36, 0.40)      # P0 를 «크게» 사게 만든 곡선


def replay(by2, shares, add_stop, tkw):
    ev, blk, spread = [], 0, 0
    allT = (True,) * (len(shares) - 1)
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blk += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 shares=shares, add_stop=add_stop, **tkw)
            if len({m["resolve_date"] for m in t["masks"].values()}) > 1:
                spread += 1
            open_until[c] = t["masks"][allT]["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blk, spread


def sim(ev, cap, n_seed):
    """🚨 `risk=1.0` 이라 «cap 이 항상 구속»한다 — stop_frac 이 0.08 로 상수이므로
       `cap=0.20` 은 74번 P0(risk 0.02·cap 0.20 → lim 0.20·eq)와 «정확히 같다»."""
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=1.0, cap=cap,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def summ(rs, n_seed):
    eq = sorted(x["equity_pct"] for x in rs)
    return {"equity": st.median(eq), "p5": eq[int(n_seed * .05)],
            "mdd": st.median(x["mdd_pct"] for x in rs),
            "n_filled": st.median(x["n_filled"] for x in rs),
            "conc": st.median(x["conc_median"] for x in rs),
            "expo": st.median(x["expo_mean"] for x in rs),
            "added": st.median(x["n_added"] for x in rs),
            "win": st.median(x["win_rate"] for x in rs),
            "per_trade": st.median(x["filled_per_trade"] for x in rs)}


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2
    n_seed = 20 if "--quick" in sys.argv else N_SEED
    print("=" * 104, flush=True)
    print("75 — 리버모어식 피라미딩 「위에 얹어 크게 만든다」 (사전등록 tasks/75)", flush=True)
    print("=" * 104, flush=True)
    by2, n_all, n_sel, n_ext = r74.load_filtered()
    print("경로 %d → 조합 %d (%.1f%%) · 250봉 연장 %d · 우대수수료 %s · seed %d\n"
          % (n_all, n_sel, 100.0 * n_sel / n_all, n_ext, COST, n_seed), flush=True)

    # ── 관문 ①② ────────────────────────────────────────────────────────
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, STOP, TARGET))
    # 🚨 관문 ① 은 «기계»(sim_lots ≡ sim_frac)를 재는 것이지 «규약»을 재는 게 아니다.
    #    그래서 반올림을 «끈» 판으로 건다. 첫 판에서 FIX(px_round=2)를 넣었다가
    #    1.428e-01 로 깨졌는데, 그건 기계가 아니라 §3① 의 «의도한 규약 변경» 탓이었다.
    #    (2026-08-26 자기 정정 — 규약 변경을 관문 경로에 섞어 넣은 것이 잘못이었다.)
    NOROUND = {k: v for k, v in FIX.items() if k != "px_round"}
    ev_p0n, _b2, _s2 = replay(by2, (1.0,), "floor_entry", NOROUND)
    ev_p0, _b2b, _s2b = replay(by2, (1.0,), "floor_entry", FIX)
    worst = worst_r = 0.0
    with r41.Cost(*COST):
        for s in range(min(20, n_seed)):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_p0n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            c2 = sl.sim_lots(ev_p0, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            worst = max(worst, abs(a - b) / max(1e-12, abs(a)))
            worst_r = max(worst_r, abs(a - c2) / max(1e-12, abs(a)))
    print("관문 ①  shares=(1.0,) = sim_frac(5칸·현금제약) · **반올림 끈 판**"
          "  최대 상대오차 %.3e → **%s**"
          % (worst, "통과" if worst < 1e-9 else "🚨 미통과"), flush=True)
    print("        (참고) 반올림 «켠» 판은 %.3e — 기계가 아니라 §3① 규약이 만든 차이다"
          % worst_r, flush=True)
    print("        진입 옛 %d · 새 %d\n" % (len(ev_ref), len(ev_p0)), flush=True)

    # ── 관문 ③ 반올림 있음/없음 ─────────────────────────────────────────
    ev_nr, _b3, _s3 = replay(by2, (1.0, 0.5), "floor_entry",
                             dict(h_lag=True, stay_on="close"))
    ev_r, _b4, _s4 = replay(by2, (1.0, 0.5), "floor_entry", FIX)
    diff = sum(1 for a, b in zip(ev_nr, ev_r)
               for m in a["masks"]
               if (a["masks"][m]["resolve_date"], a["masks"][m]["result"])
               != (b["masks"][m]["resolve_date"], b["masks"][m]["result"]))
    tot = sum(len(a["masks"]) for a in ev_nr)
    print("관문 ③  가격 2자리 반올림 있음/없음 — 결착이 갈린 해결 **%d / %d (%.4f%%)**"
          % (diff, tot, 100.0 * diff / max(1, tot)), flush=True)
    print("        (74번에 남아 있는 「칼끝」의 크기다. 75번은 반올림 판을 쓴다.)", flush=True)
    # 🚨 «건수»만으로 「작다」고 읽으면 안 된다 — 자산에 얼마나 번지는지 같이 잰다.
    rel = []
    with r41.Cost(*COST):
        for s in range(min(60, n_seed)):
            a = sl.sim_lots(ev_p0n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            b = sl.sim_lots(ev_p0, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            rel.append(abs(a - b) / max(1e-12, abs(a)) * 100)
    rel.sort()
    m = len(rel)
    print("관문 ③′ 그 규약이 «자산»에 번지는 크기 (P0 · %d판): 중앙 %.2f%% · P90 %.2f%% · "
          "**최대 %.2f%%** · 1%% 넘는 판 %d/%d"
          % (m, rel[m // 2], rel[9 * m // 10], rel[-1],
             sum(1 for x in rel if x > 1.0), m), flush=True)
    print("        🚨 **한 판 한 판은 최대 14%% 까지 움직인다** — 중앙은 거의 안 움직여도"
          " «내가 겪는 한 판»은 크게 달라진다.\n", flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    print("  %-16s %6s %5s %11s %11s %8s %6s %6s %6s %6s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률", "동시", "노출", "증액"),
          flush=True)
    print("  " + "─" * 96, flush=True)
    res, curves, evs = {}, {}, {}
    for nm, shares, add_stop, _note in VARIANTS:
        ev, blk, spread = replay(by2, shares, add_stop, FIX)
        evs[nm] = ev
        rs = sim(ev, BASE_CAP, n_seed)
        res[nm] = summ(rs, n_seed)
        res[nm]["n_entry"] = len(ev)
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-16s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %6d %5.1f%% %6d"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["conc"], r["expo"], r["added"]), flush=True)

    # ── 노출 곡선 (P0 를 «크게») ────────────────────────────────────────
    print("\n★ 노출 맞춘 대조 — P0 를 «크게» 사게 만든 곡선 (한 칸을 고르지 않는다)",
          flush=True)
    print("  %-16s %8s %11s %11s %8s %6s" % ("판", "노출", "자산중앙", "운나쁠때", "MDD", "동시"),
          flush=True)
    big, big_curves = {}, {}
    for c in CAPS:
        rs = sim(evs["P0 한 번에"], c, n_seed)
        big["P0 cap %.2f" % c] = summ(rs, n_seed)
        big_curves["P0 cap %.2f" % c] = [x["curve"] for x in rs]
        v = big["P0 cap %.2f" % c]
        print("  P0 · 크기 %.2f   %7.2f%% %+10.2f%% %+10.2f%% %7.1f%% %6d"
              % (c, v["expo"], v["equity"], v["p5"], v["mdd"], v["conc"]), flush=True)
    for nm in ("★ L1 1.5배", "L1-avgstop", "L2 1.75배", "L1-half(74판)"):
        v = res[nm]
        print("  %-16s %7.2f%% %+10.2f%% %+10.2f%% %7.1f%% %6d   ← 곡선 «어디»에"
              % (nm, v["expo"], v["equity"], v["p5"], v["mdd"], v["conc"]), flush=True)

    # ── 🚨 A 판정 «전»에 — 답할 수 있는 질문인가 ────────────────────────
    L1 = res["★ L1 1.5배"]
    match = min(big, key=lambda k: abs(big[k]["expo"] - L1["expo"]))
    print("\n" + "─" * 104, flush=True)
    print("🚨 A 판정 «전» — 답할 수 있는 질문인가 (노출 %.2f%% vs %s %.2f%%)"
          % (L1["expo"], match, big[match]["expo"]), flush=True)
    sw = da.sweep(curves["★ L1 1.5배"], big_curves[match])
    m = r75a.mde(sw)
    for b in da.BLOCKS:
        v = m[b]
        if v is None:
            print("  블록 %2d  (로그 불가)" % b, flush=True)
            continue
        print("  블록 %2d  관측 %+8.2f%% · 필요 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
              % (b, v["median"], v["need_pct"], v["T"], v["years"],
                 "✅" if v["excl0"] else "❌",
                 "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)
    print(da.fmt(sw, "L1 − %s" % match), flush=True)

    # ── §4 합격선 ───────────────────────────────────────────────────────
    M = big[match]
    A = sw[sw["_widest"]]["excl0"] and sw[sw["_widest"]]["median"] > 0
    B = L1["equity"] > M["equity"]
    C = L1["p5"] > M["p5"]
    print("\n§4 합격선 (대조 = 노출 맞춘 %s)" % match, flush=True)
    print("  A★ 자료 축 0 배제(양)                                    → **%s**"
          % ("통과" if A else "미통과"), flush=True)
    print("  B  자산   L1 %+.2f%% vs %+.2f%%  (차 %+.2f%%p)           → **%s**"
          % (L1["equity"], M["equity"], L1["equity"] - M["equity"],
             "통과" if B else "미통과"), flush=True)
    print("  C  하단   L1 %+.2f%% vs %+.2f%%  (차 %+.2f%%p)           → **%s**"
          % (L1["p5"], M["p5"], L1["p5"] - M["p5"], "통과" if C else "미통과"), flush=True)
    print("  D  「하루당 효과 유지」 검사 → 75b 를 이 짝으로 다시 돌린다(별도)", flush=True)

    (OUT / "75-livermore.json").write_text(json.dumps(
        {"res": res, "big": big, "match": match, "mde": {str(k): v for k, v in m.items()},
         "verdict": {"A": A, "B": B, "C": C}, "round_diff": diff, "round_tot": tot,
         "n_seed": n_seed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 75-livermore.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
