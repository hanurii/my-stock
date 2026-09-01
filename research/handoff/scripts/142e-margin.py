# -*- coding: utf-8 -*-
r"""142e — 「구성원이 왜 안 바뀌었나」를 **증명**한다. 설명이 아니라.

142d 가 밝힌 것
```
경로가 바뀐 건 4,882 · 그중 r_ 가 «실제로» 바뀐 건 **834**  → 다른 것을 읽고 있는 게 맞다
🚨 대박 151 중 «바뀐 경로» **19건** · 그중 r_ 가 바뀐 것 **7건**  → **꼬리에도 변화가 닿았다**
```
그런데도 구성원이 0 변화였다. **왜인가.**

## 증명의 모양 — «폭»과 «여유»를 나란히 놓는다
```
Δ      = |새 r_ − 옛 r_|              ← 변화가 «얼마나 큰가»
여유    = |r_ − 문턱|                  ← 순위가 뒤집히려면 이만큼 움직여야 한다
```
> ### **max Δ  <  min 여유**  이면 **구성원은 «바뀔 수 없었다»**. 그건 설명이 아니라 «증명»이다.
> ### 반대로 겹치면 「우연히 안 바뀐 것」이고, 그때는 그렇게 적어야 한다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/142e-margin.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                        # noqa: E402

OLD = ROOT / ".cache" / "bt5y" / "sub"
NEW = Path("D:/stock-data/uspath-warm/full")
FROZEN = ROOT / "research" / "handoff" / "data" / "142-labels-frozen.json"
BACK_YEARS = tuple(range(2012, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5


def r_of(p):
    t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                         half=HALF, shares=(1.0,), add_stop="floor_entry")
    m = t["masks"][()]
    ep = t["entry_px"]
    if not ep or not m["exits"]:
        return None
    return sum(sh * (px / ep * 100.0 - 100.0) for _d, sh, px in m["exits"])


def key(p):
    return "|".join((p["scan_date"], p["code"], p["pattern"]))


def main() -> int:
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    cut = fz["back"]["cut"]
    print("뒤 구간 문턱 r_ = **%+.4f%%** · 대박 %d건" % (cut, fz["back"]["K"]), flush=True)

    deltas, near = [], []
    for y in BACK_YEARS:
        o = {key(p): p for p in json.loads((OLD / ("uspath_%d.json" % y))
                                           .read_text(encoding="utf-8"))["trigger_paths"]}
        n = {key(p): p for p in json.loads((NEW / ("uspath_%d.json" % y))
                                           .read_text(encoding="utf-8"))["trigger_paths"]}
        for k in (set(o) & set(n)):
            a, b = o[k], n[k]
            if not any(a.get(f) != b.get(f) for f in ("d", "o", "h", "l", "c",
                                                      "pivot", "entry_price")):
                continue
            ra, rb = r_of(a), r_of(b)
            if ra is None or rb is None:
                continue
            d = abs(rb - ra)
            if d > 1e-9:
                deltas.append(d)
            # 문턱 «근처»에 있는 것 — 뒤집힐 수 있었던 후보
            near.append((min(abs(ra - cut), abs(rb - cut)), d, k, ra, rb))
        del o, n
        print("   %d년 처리" % y, flush=True)

    deltas.sort()
    near.sort()
    print("", flush=True)
    print("=" * 92, flush=True)
    print("증명 — «변화 폭» vs «문턱까지의 여유»", flush=True)
    print("=" * 92, flush=True)
    print("① Δ = |새 r_ − 옛 r_| 가 **0 이 아닌** 건 **%s**" % "{:,}".format(len(deltas)),
          flush=True)
    if deltas:
        print("   중앙 **%.4f%%p** · P90 **%.4f%%p** · **최대 %.4f%%p**"
              % (deltas[len(deltas) // 2], deltas[int(len(deltas) * 0.9)], deltas[-1]),
              flush=True)
    print("", flush=True)
    print("② 바뀐 경로 중 **문턱에 가장 가까운** 다섯 (여유 = |r_ − 문턱|)", flush=True)
    for m, d, k, ra, rb in near[:5]:
        print("   여유 **%8.4f%%p** · Δ %8.4f%%p · %s  (%.4f → %.4f)"
              % (m, d, k, ra, rb), flush=True)

    if deltas and near:
        mx, mn = deltas[-1], near[0][0]
        print("", flush=True)
        print("★ **최대 Δ = %.4f%%p**   vs   **최소 여유 = %.4f%%p**" % (mx, mn), flush=True)
        if mx < mn:
            print("   → ✅ **구성원은 «바뀔 수 없었다».** 변화 폭이 여유보다 %.0f배 작다. **증명**"
                  % (mn / max(mx, 1e-12)), flush=True)
        else:
            print("   → 🚨 **겹친다. 「우연히 안 바뀐 것」이다.** 그렇게 적어야 한다", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
