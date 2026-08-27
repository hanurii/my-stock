# -*- coding: utf-8 -*-
"""86v 부속 2 — **① vs ② 가 «같은 노출»에서 붙은 비교인가.**

왜 이걸 재나
------------
내 2×2 에서 ③(20칸·cap 20%)이 ②(20칸·cap 5%)와 «거의 같은» 값을 냈다(+88.75 vs +88.94).
즉 **cap 을 1/칸 «위»로 올리면 아무 일도 안 일어난다** — 현금이 먼저 마르기 때문이다.
그러면 「칸」과 「종목당 금액」은 이 하네스에서 **분리되지 않는다.**

그래서 남는 물음은 하나다 — **86 의 ① → ② 가 «노출이 같은» 비교인가?**
  같으면  → 잃은 209%p 는 **「집중」의 값**이다 (86 의 읽기가 선다)
  다르면  → 그중 일부는 **「돈을 덜 굴린 것」**이고, 그건 다른 이야기다

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/86v-exposure.py [N_SEED]
"""
from __future__ import annotations

import importlib.util as _u
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r86", HERE / "86-slots-and-tails.py")
r86 = _u.module_from_spec(_s)
_s.loader.exec_module(r86)
r84, r74, r41 = r86.r84, r86.r74, r86.r41

NS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    print("=" * 100)
    print("86v — ① vs ② 가 «같은 노출»에서 붙었나  (seed %d)" % NS)
    print("=" * 100, flush=True)
    print("  %-30s %9s %11s %11s %11s"
          % ("칸", "**평균노출**", "자산중앙", "체결", "동시보유중앙"), flush=True)
    print("  " + "-" * 78, flush=True)
    out = {}
    for nm, k, cap in (("① 5칸 · cap 20%", 5, 0.20),
                       ("② 20칸 · cap 5%", 20, 0.05),
                       ("③ 20칸 · cap 20%", 20, 0.20),
                       ("④ 5칸 · cap 5%", 5, 0.05),
                       ("· 10칸 · cap 10%", 10, 0.10)):
        rs = r86.run(ev, k, NS, cap=cap)
        ex = st.median(r.get("expo_mean", float("nan")) for r in rs)
        cc = st.median(r.get("conc_med", r.get("conc_mean", float("nan"))) for r in rs)
        out[nm] = ex
        print("  %-30s %8.1f%% %+10.2f%% %11d %11s"
              % (nm, ex, st.median(r["equity_pct"] for r in rs),
                 int(st.median(r["n_filled"] for r in rs)),
                 ("%.1f" % cc) if cc == cc else "—"), flush=True)
    d = out["② 20칸 · cap 5%"] - out["① 5칸 · cap 20%"]
    print("\n  ★ ② − ① 평균노출 차 = **%+.1f%%p**" % d, flush=True)
    if abs(d) < 5:
        print("     → **같은 노출에서 붙었다.** 잃은 209%p 는 「집중」의 값으로 읽어도 된다.",
              flush=True)
        print("       86 의 헤드라인이 선다.", flush=True)
    else:
        print("     🚨 **노출이 다르다.** 209%p 중 일부는 「집중」이 아니라 «굴린 돈의 양»이다.",
              flush=True)
        print("       그러면 「분산이 돈을 깎는다」로 읽으면 안 된다.", flush=True)
    print("\n  (참고 ④ 는 cap 이 1/칸보다 «작아» 노출이 구조적으로 낮다 — 대조용이다.)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
