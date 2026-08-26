# -*- coding: utf-8 -*-
"""82v 부속 2 — **회전 대조군을 «전부» 센다.**

왜 — 82 의 회전판은 `randrange(1, 112)` 라 서로 다른 깃발이 **111개뿐**이다.
     300번 뽑아도 «새로운 판»은 없다. 그러면 **전수로 세는 게 맞다** —
     표집오차가 0 이 되고, 「300판 최대」라는 부풀린 라벨도 사라진다.

무엇을 답하나 — 「진짜 200MA 깃발이 무작위 깃발보다 «나쁜가»」
     82 는 관측 +110.92%(seed 0~4 한 판)를 무작위 «분포»와 견줬다.
     여기서는 **양쪽을 같은 자로** 놓는다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/82v-null-exact.py [seeds]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r82", HERE / "82-index-switch.py")
r82 = _u.module_from_spec(_s)
_s.loader.exec_module(r82)
r74, r41, sl = r82.r74, r82.r41, r82.sl

NS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, *_ = r74.load_filtered()
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}
    ev0, _b, _s2 = r74.replay_masks(by2, (1.0,), "floor_entry")
    cal, v = r82.load_index("US500")
    ipx_d = dict(zip(cal, v))
    ci = sorted(ipx_d)

    def ipx(d):
        return ipx_d[ci[max(0, bisect.bisect_right(ci, d) - 1)]]

    on, _f = r82.month_flags(cal, r82.ma_above(cal, v, 200))
    months = sorted(on)
    lbl = [on[m] for m in months]

    def run(flag_on, ns):
        ih, ne, _n = r82.spans(cal, flag_on)
        ev, _c, _bk, _g = r82.cut_events(ev0, pmap, ne, ih, cal)
        with r41.Cost(*r82.COST):
            rs = [sl.sim_lots(ev, seed=s, slots=r82.SLOTS, risk=r82.RISK, cap=r82.CAP,
                              reserve=False, fill_rule="truncate", cash_rule="per_slot")
                  for s in range(ns)]
        return st.median(r82.eq_of(r82.overlay_fold(
            r82.settled_curve(r), ih, ipx, r82.HEADLINE_COST, cal)[0]) for r in rs)

    print("=" * 96, flush=True)
    print("회전 대조군 **전수 %d판** (k = 1 … %d) · seed %d"
          % (len(lbl) - 1, len(lbl) - 1, NS), flush=True)
    print("=" * 96, flush=True)
    obs = run(on, NS)
    print("관측(진짜 200MA 깃발) seed %d 중앙 = **%+.2f%%**" % (NS, obs), flush=True)

    nulls = []
    for k in range(1, len(lbl)):
        z = lbl[k:] + lbl[:k]
        nulls.append(run(dict(zip(months, z)), NS))
        if k % 20 == 0:
            print("   %d/%d  (지금까지 중앙 %+.2f%%)"
                  % (k, len(lbl) - 1, st.median(nulls)), flush=True)
    a = sorted(nulls)
    n = len(a)
    below = sum(1 for x in a if x < obs)
    print("\n전수 회전 %d판 — 보통 %+.2f%% · 5%% %+.2f%% · 95%% %+.2f%% · 최대 %+.2f%%"
          % (n, a[n // 2], a[int(n * .05)], a[int(n * .95)], a[-1]), flush=True)
    print("관측이 **%d/%d 판보다 위 = %.1f 백분위**" % (below, n, 100.0 * below / n), flush=True)
    print("\n판정:", flush=True)
    print("  B(등록된 문턱: 관측 > 무작위 최대) → **%s**"
          % ("통과" if obs > a[-1] else "❌ 미통과"), flush=True)
    lo, hi = 100.0 * below / n, 100.0 * below / n
    if hi < 5:
        v2 = "**무작위보다 나쁘다**고 말할 수 있다"
    elif lo > 95:
        v2 = "무작위보다 좋다"
    else:
        v2 = "**무작위와 «구분 안 된다»** — 「해롭다」는 말할 수 없다"
    print("  「진짜 깃발이 무작위보다 나쁜가」 → %.1f 백분위 → %s" % (lo, v2), flush=True)
    (Path(__file__).resolve().parents[3] / "_82v-null-exact.json").write_text(json.dumps(
        {"obs": obs, "n_seed": NS, "nulls": nulls,
         "pct": 100.0 * below / n}, indent=1), encoding="utf-8")
    print("\n저장: _82v-null-exact.json (저장소 뿌리 · .cache 미접촉)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
