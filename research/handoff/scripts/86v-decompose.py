# -*- coding: utf-8 -*-
"""86v — **「칸 수」 축이 «한 손잡이»가 아니다.** 검증 세션.

무엇을 재나
-----------
  ㉠ **격자가 «자기 사양»대로 안 돈다** — `종목당 상한 = 1/칸` 인데 3·4칸에서는
     위험규칙(`risk/stop_frac`)이 먼저 물려서 «1/칸»이 안 된다.
     🚨 그리고 그게 두뇌 세션이 본 「폭이 단조가 아니다(4칸 > 3칸)」의 정체로 보인다.
  ㉡ **2×2 분해** — 「칸 수」와 「한 종목에 넣는 돈」을 «따로» 돌린다.
     86 은 둘을 «같이» 움직였으므로 −209%p 가 어느 쪽 몫인지 모른다.
  ㉢ **㉮ 의 「먼저 온 것을 산다」** — BTU 한 건(n=1) 말고 «초반 vs 후반» 체결률을 센다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/86v-decompose.py [N_SEED]
"""
from __future__ import annotations

import importlib.util as _u
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r86", HERE / "86-slots-and-tails.py")
r86 = _u.module_from_spec(_s)
_s.loader.exec_module(r86)
r85, r84, r74, r41, sl = r86.r85, r86.r84, r86.r74, r86.r41, r86.sl

NS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200


def hr(t):
    print("\n" + "=" * 100, flush=True)
    print(t, flush=True)
    print("=" * 100, flush=True)


def summ(rs):
    e = sorted(r["equity_pct"] for r in rs)
    n = len(e)
    return {"med": st.median(e), "p5": e[int(n * .05)], "p95": e[int(n * .95)],
            "width": e[int(n * .95)] - e[int(n * .05)],
            "mdd": st.median(r["mdd_pct"] for r in rs),
            "filled": int(st.median(r["n_filled"] for r in rs))}


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    print("진입 %d건 · seed %d" % (len(ev), NS), flush=True)

    # ── ㉠ 격자가 사양대로 도나 ─────────────────────────────────────────
    hr("㉠ 격자가 «자기 사양»대로 도나 — `종목당 상한 = 1/칸` 이 정말 «1/칸»인가")
    sfs = [t.get("stop_frac") or 0.10 for t in ev]
    sf_med = st.median(sfs)
    print("  `slot_sim_lots:221`  **lim = min(eq × risk / stop_frac , eq × cap)**", flush=True)
    print("  risk = %.3f · stop_frac 중앙 %.4f → **위험규칙 상한 = %.1f%%**"
          % (r74.RISK, sf_med, 100.0 * r74.RISK / sf_med), flush=True)
    print("\n  %4s %10s %12s %14s %s" % ("칸", "cap=1/칸", "위험규칙", "«실제» 한도", "무엇이 무나"),
          flush=True)
    print("  " + "-" * 66, flush=True)
    risk_lim = r74.RISK / sf_med
    kink = None
    for k in r86.SLOTS_GRID:
        cap = 1.0 / k
        eff = min(cap, risk_lim)
        who = "**위험규칙**" if risk_lim < cap - 1e-12 else ("동률" if abs(risk_lim - cap) < 1e-12
                                                          else "cap")
        if risk_lim < cap - 1e-12:
            kink = k
        print("  %4d %9.1f%% %11.1f%% %13.1f%% %s"
              % (k, 100 * cap, 100 * risk_lim, 100 * eff, who), flush=True)
    print("\n  → **%s칸 이하에서는 «1/칸»이 아니다.** 사전등록 §2 의 「자본을 고르게 나눈다」가"
          % kink, flush=True)
    print("     그 칸들에서는 **성립하지 않는다.**", flush=True)
    print("  🚨 그래서 「폭이 단조가 아니다(4칸 446.9 > 3칸 380.7)」는 **자료의 성질이 아니라**",
          flush=True)
    print("     **3칸이 «덜 집중»되게 돌아간 결과**일 수 있다 — 아래 ㉡에서 잰다.", flush=True)

    # ── ㉡ 2×2 분해 ────────────────────────────────────────────────────
    hr("㉡ **2×2 분해** — 「칸 수」와 「한 종목에 넣는 돈」을 «따로» 움직인다")
    print("  86 은 둘을 «같이» 움직였다(칸 5→20 이면 cap 20%→5%).", flush=True)
    print("  그러면 −209%p 가 «칸» 몫인지 «금액» 몫인지 못 가린다. 네 칸을 다 돈다.\n", flush=True)
    print("  %-28s %7s %11s %11s %9s %9s"
          % ("칸", "체결", "자산중앙", "5% 하단", "폭", "MDD"), flush=True)
    print("  " + "-" * 78, flush=True)
    CELLS = (("① 5칸 · cap 20%  (=86 의 5칸)", 5, 0.20),
             ("② 20칸 · cap 5%  (=86 의 20칸)", 20, 0.05),
             ("③ **20칸 · cap 20%** (칸만 늘림)", 20, 0.20),
             ("④ **5칸 · cap 5%** (금액만 줄임)", 5, 0.05))
    R = {}
    for nm, k, cap in CELLS:
        rs = r86.run(ev, k, NS, cap=cap)
        s = summ(rs)
        R[nm] = s
        print("  %-28s %7d %+10.2f%% %+10.2f%% %8.1f %8.1f%%"
              % (nm, s["filled"], s["med"], s["p5"], s["width"], s["mdd"]), flush=True)
    a, b = R[CELLS[0][0]], R[CELLS[1][0]]
    c, d = R[CELLS[2][0]], R[CELLS[3][0]]
    print("\n  ★ 분해 (자산 중앙, ① 기준):", flush=True)
    print("     86 이 «한꺼번에» 잰 것        ① → ②   **%+.2f%%p**" % (b["med"] - a["med"]),
          flush=True)
    print("     «칸»만 늘렸을 때             ① → ③   **%+.2f%%p**" % (c["med"] - a["med"]),
          flush=True)
    print("     «금액»만 줄였을 때           ① → ④   **%+.2f%%p**" % (d["med"] - a["med"]),
          flush=True)
    inter = (b["med"] - a["med"]) - (c["med"] - a["med"]) - (d["med"] - a["med"])
    print("     상호작용                              %+.2f%%p" % inter, flush=True)
    print("\n  ★ 폭(운) 도 같이:", flush=True)
    print("     ① → ②  %.1f → %.1f   ·   «칸»만 %.1f   ·   «금액»만 %.1f"
          % (a["width"], b["width"], c["width"], d["width"]), flush=True)
    big = "칸" if abs(c["med"] - a["med"]) > abs(d["med"] - a["med"]) else "금액"
    print("\n  → 자산에서 지배적인 것은 **«%s»** 쪽이다." % big, flush=True)

    # ── ㉢ ㉮ 의 「먼저 온 것을 산다」 ───────────────────────────────────
    hr("㉢ ㉮ — 「시작 직후엔 칸이 비어 먼저 온 것을 산다」를 **세어서** 확인한다")
    print("  86 은 BTU **한 건**(체결률 100%)으로 이 기전을 적었다. n=1 이다.", flush=True)
    ev2 = [t for t in ev if t["entry_date"] >= r86.START]
    print("  %s 이후 진입 **%d건**" % (r86.START, len(ev2)), flush=True)
    rs2 = r86.run(ev2, 5, NS, cap=r74.CAP)
    f = Counter()
    for r in rs2:
        for key, kind, _k, _d, _p, _a, _t in r["fill_log"]:
            if kind == "pilot":
                f[key] += 1
    ds = sorted({t["entry_date"] for t in ev2})
    print("\n  %-14s %7s %11s" % ("구간", "진입 수", "체결률"), flush=True)
    print("  " + "-" * 36, flush=True)
    for lab, lo, hi in (("첫 5거래일", 0, 5), ("6~10일", 5, 10), ("11~20일", 10, 20),
                        ("21~40일", 20, 40), ("41일~", 40, len(ds))):
        win = set(ds[lo:hi])
        sub = [t for t in ev2 if t["entry_date"] in win]
        if not sub:
            continue
        rate = 100.0 * sum(f.get((t["scan_date"], t["code"], t["pattern"]), 0)
                           for t in sub) / (NS * len(sub))
        print("  %-14s %7d %10.1f%%" % (lab, len(sub), rate), flush=True)
    print("\n  ★ 첫 구간이 뒤 구간보다 «뚜렷이» 높으면 그 기전이 선다. 비슷하면 BTU 는 한 건일 뿐이다.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
