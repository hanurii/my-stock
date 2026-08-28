# -*- coding: utf-8 -*-
r"""96 — **「소수 종목에 크게 넣으면」 달라지는가.** 사용자 물음(2026-08-28).

> 「미너비니는 소수 종목에 크게 넣는다. 우리는 5칸 균등인데 뭐가 다른가?」

«집중»이 두 가지로 갈린다 — **둘 다 잰다:**
```
(A) 위험 2% 규칙 유지 · 칸 수만 줄임   한 종목 상한 25% 라 칸이 적으면 «현금이 남는다»
(B) 자본을 칸 수로 나눔(cap = 1/slots)  진짜 집중. 「크게 넣는다」에 가깝다
```
🚨 **이것은 «판정»이 아니라 «서술»이다.** 문턱이 없다 — 사용자 물음에 답하는 것이고,
   여기서 나온 값으로 규칙을 고치면 그때 창이 사라진다.
🚨 **낙폭을 «반드시» 함께 찍는다** — 집중은 수익과 낙폭을 «둘 다» 키운다.
   수익만 보면 반드시 「집중이 낫다」가 나온다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/96-concentration.py [--quick]
"""
from __future__ import annotations

import datetime as _dt
import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim_lots as sl                                     # noqa: E402
import _lean_load as LL                                        # noqa: E402

r91 = LL.r91
r41 = r91.r41

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
N_SEED = 200
SLOTS = (1, 2, 3, 5, 8, 10)


def cagr(total, yrs):
    b = 1 + total / 100.0
    return (b ** (1 / yrs) - 1) * 100 if b > 0 else float("nan")


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    print("=" * 104, flush=True)
    print("96 — 「소수 종목에 크게 넣으면」 달라지는가  (**서술 · 문턱 없음 · 판정 아님**)", flush=True)
    print("=" * 104, flush=True)
    print("창 %s ~ %s · seed %d · 규칙은 91 정본(−8%% / +20%% 절반 → 추격)\n" % (D0, D1, n_seed),
          flush=True)

    # 🚨 28년치를 통째로 올리면 MemoryError (실측 ≈5.8GB). 해마다 걸러 버리며 올린다.
    by2, _cand, n_all = LL.load_combo(YEARS, D0, D1)
    ev, blk, _t = r91.replay(by2)          # 사다리 ② = 91·93 의 정본 조합
    yrs = (r91._ord(D1) - r91._ord(D0)) / 365.25
    print("조합 거래 %s · %.2f년\n" % ("{:,}".format(len(ev)), yrs), flush=True)

    out = {}
    for mode, lab in (("A", "(A) 위험 2%% 유지 · 칸 수만 줄임"),
                      ("B", "(B) 자본을 칸 수로 나눔 — «진짜 집중»")):
        print("─" * 104, flush=True)
        print("### %s" % (lab % () if "%%" in lab else lab), flush=True)
        print("  %-6s %-9s %13s %11s %11s %10s %8s %9s"
              % ("칸", "한종목상한", "자산중앙", "연환산", "운나쁠때5%", "MDD중앙",
                 "체결", "묶인돈%"), flush=True)
        print("  " + "-" * 96, flush=True)
        for s_ in SLOTS:
            if mode == "A":
                risk, cap = 0.02, 0.20 if s_ >= 5 else 1.0 / s_
                cap = min(cap, 1.0)
            else:
                risk, cap = 1.0, 1.0 / s_          # 위험 상한을 풀어 cap 이 결정하게
            with r41.Cost(*r91.COST):
                rs = [sl.sim_lots(ev, seed=k, slots=s_, risk=risk, cap=cap,
                                  reserve=False, fill_rule="truncate",
                                  cash_rule="per_slot") for k in range(n_seed)]
            eq = sorted(x["equity_pct"] for x in rs)
            med = st.median(eq)
            row = {"slots": s_, "cap": cap, "med": med, "cagr": cagr(med, yrs),
                   "p5": eq[int(n_seed * .05)],
                   "mdd": st.median(x["mdd_pct"] for x in rs),
                   "n_filled": st.median(x["n_filled"] for x in rs),
                   "expo": st.median(x["expo_mean"] for x in rs)}
            out["%s%d" % (mode, s_)] = row
            print("  %-6d %8.0f%% %+12.2f%% %+10.2f%% %+10.2f%% %9.1f%% %8.0f %8.1f%%"
                  % (s_, cap * 100, med, row["cagr"], row["p5"], row["mdd"],
                     row["n_filled"], row["expo"]), flush=True)
        print("", flush=True)

    # 지수 대조
    b = r91.bench("SPY", D0, D1)
    q = r91.bench("QQQ", D0, D1)
    print("─" * 104, flush=True)
    print("  대조  S&P500 %+.2f%% (연 %+.2f%%) MDD %.1f%%  ·  나스닥100 %+.2f%% (연 %+.2f%%) MDD %.1f%%"
          % (b["total"], b["cagr"], b["mdd"], q["total"], q["cagr"], q["mdd"]), flush=True)
    print("\n  1,000만원 기준", flush=True)
    for k in sorted(out, key=lambda x: (x[0], int(x[1:]))):
        r = out[k]
        print("     %-4s %2d칸  %14s원   최악 %.1f%%   수익÷낙폭 %5.2f"
              % (k[0], r["slots"], "{:,.0f}".format(1000e4 * (1 + r["med"] / 100)),
                 r["mdd"], abs(r["med"] / r["mdd"]) if r["mdd"] else float("nan")), flush=True)
    print("     %-4s      %14s원   최악 %.1f%%   수익÷낙폭 %5.2f"
          % ("SPY", "{:,.0f}".format(1000e4 * (1 + b["total"] / 100)), b["mdd"],
             abs(b["total"] / b["mdd"])), flush=True)
    print("     %-4s      %14s원   최악 %.1f%%   수익÷낙폭 %5.2f"
          % ("QQQ", "{:,.0f}".format(1000e4 * (1 + q["total"] / 100)), q["mdd"],
             abs(q["total"] / q["mdd"])), flush=True)

    print("\n🚨 읽는 법 — **수익만 보면 반드시 「집중이 낫다」가 나온다.**", flush=True)
    print("   집중은 수익과 낙폭을 «둘 다» 키운다. **수익÷낙폭**과 **운 나쁠 때**를 함께 본다.",
          flush=True)
    (r91.OUT / "96-concentration.json").write_text(
        json.dumps({"rows": out, "spy": b, "qqq": q, "years": yrs, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
