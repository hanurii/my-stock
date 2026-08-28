# -*- coding: utf-8 -*-
r"""97b — **시장 폭 신호가 「같은 비율로 무작위로 쉬기」를 이기는가.** (가짜약)

97 1단계에서 여섯 신호 중 **⑥ 시장 폭만 세 구간 모두 플러스**(+72.21 / +61.38 / +2.30)였다.

🚨 **그런데 그것만으로는 아무 뜻이 없다:**
```
각 구간에서 우연히 플러스일 확률 0.5  →  3/3 = 12.5%
6개 중 «적어도 하나»가 3/3 일 확률 ≈ **55%** — 거의 반반이다
```
🚨 그리고 **⑥ 은 «우리 자신의 후보 수»**다. 「후보가 많은 날에만 산다」는 것이고,
   후보가 많은 날엔 **여러 후보 중 골라 담게 되어 «슬롯 경쟁»이 달라진다.**
   신호와 «무관하게» 성과가 날 수 있다.

## 가짜약 — **형태를 맞추고 «내용»만 없앤다**
```
형태  같은 구간에서 «같은 비율»의 날을 쉰다
내용  그 날이 「후보가 많은 날」이라는 것        ← 이것만 없앤다 (무작위로 고른다)
```
관측이 가짜약 분포 «밖»이면 신호에 «내용»이 있는 것이고,
**분포 «안»이면 「그냥 덜 사는 것」이 값을 낸 것**이다.

🚨 관측을 **같은 판수**로 다시 잰다(유형 25). 🚨 이건 여전히 «1단계»다 — 문턱을 안 건다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _lean_load as LL                                        # noqa: E402

r91 = LL.r91
_s = _u.spec_from_file_location("r97", HERE / "97-regime-signals.py")
r97 = _u.module_from_spec(_s)
_s.loader.exec_module(r97)

N_NULL = 200
N_SEED = 50          # 가짜약과 관측이 «같은» 판수 (유형 25)


def main() -> int:
    print("=" * 100, flush=True)
    print("97b — 시장 폭이 «같은 비율로 무작위로 쉬기»를 이기는가 (가짜약 · 1단계)", flush=True)
    print("=" * 100, flush=True)

    by2, cand, n_all = LL.load_combo(r97.YEARS, r97.D0, r97.D1)
    ev_all, _b, _t = r91.replay(by2)
    brd = r97.breadth_ok(cand)
    print("조합 거래 %s · 가짜약 %d판 · seed %d\n"
          % ("{:,}".format(len(ev_all)), N_NULL, N_SEED), flush=True)

    rnd = random.Random(0)
    for blab, a, b in r97.BLOCKS:
        ev = [t for t in ev_all if a <= t["entry_date"] <= b]
        dates = sorted({t["entry_date"] for t in ev})
        base = [x["equity_pct"] for x in r97.sim(ev, N_SEED)]

        # ── 관측 ────────────────────────────────────────────────────────
        skip = {d for d in dates if not brd.get(d, True)}
        obs_ev = [t for t in ev if t["entry_date"] not in skip]
        obs = st.median([x - y for x, y in
                         zip([z["equity_pct"] for z in r97.sim(obs_ev, N_SEED)], base)])
        rate = len(skip) / len(dates)

        # ── 가짜약: «같은 개수»의 날을 무작위로 쉰다 ──────────────────────
        nulls = []
        for k in range(N_NULL):
            rd = set(rnd.sample(dates, len(skip)))
            e = [t for t in ev if t["entry_date"] not in rd]
            nulls.append(st.median([x - y for x, y in
                                    zip([z["equity_pct"] for z in r97.sim(e, N_SEED)], base)]))
            if (k + 1) % 50 == 0:
                ns = sorted(nulls)
                print("      %s 가짜약 %3d/%d … 중앙 %+.2f · 95%% %+.2f"
                      % (blab, k + 1, N_NULL, ns[len(ns) // 2], ns[int(len(ns) * .95)]),
                      flush=True)
        ns = sorted(nulls)
        pct = 100.0 * sum(1 for x in nulls if x < obs) / N_NULL
        print("\n   ### %s  (쉬는 날 %.1f%% · %d/%d일)"
              % (blab, 100 * rate, len(skip), len(dates)), flush=True)
        print("      관측 **%+.2f%%p**  ·  가짜약 중앙 %+.2f · 95%% %+.2f · 최대 %+.2f"
              % (obs, ns[len(ns) // 2], ns[int(N_NULL * .95)], ns[-1]), flush=True)
        print("      → **%.1f 백분위**  %s" % (
            pct, "**밖 — 신호에 «내용»이 있다**" if pct >= 95 else
            ("애매" if pct >= 80 else "**안 — 「그냥 덜 사는 것」이 값을 냈다**")), flush=True)
        print("", flush=True)

    print("🚨 세 구간 «모두» 95 백분위 밖이어야 다음 단계로 간다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
