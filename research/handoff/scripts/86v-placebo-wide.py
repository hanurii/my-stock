# -*- coding: utf-8 -*-
"""86v 부속 3 — **가짜약 판수를 늘린다.**

왜 — 12판에서 낸 「75 백분위」는 **유형 25**(문턱에도 표준오차가 있다)에 그대로 걸린다.
     12판의 백분위는 눈금이 8%p 다. 그 눈금으로 「구분 안 된다」를 말할 수 없다.
     가짜약은 **특징이 필요 없다**(종목코드 해시뿐) → 가격 적재를 건너뛰어 싸게 많이 돈다.

같이 재는 것
  ㉠ 가짜약 N판의 분포 — 「뜻 없는 결정적 규칙」이 무작위 대비 얼마나 흔들리나
  ㉡ 등록된 (b) `prior6m 1분위`(+8.60%)가 그 분포의 어디인가 + **구간**
  ㉢ 「뜻 없는 규칙」이 이기는 판 비율 — 「결정적이면 낫다」가 성립하나

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/86v-placebo-wide.py [N_PLACEBO] [N_SEED]
"""
from __future__ import annotations

import hashlib
import importlib.util as _u
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r86", HERE / "86-slots-and-tails.py")
r86 = _u.module_from_spec(_s)
_s.loader.exec_module(r86)
r84, r74, r41, sl = r86.r84, r86.r74, r86.r41, r86.sl

NP = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
NS = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 200

OBS = {"(b) prior6m 1분위 [등록]": 8.60, "hi52 1분위": 18.69,
       "logpx 1분위": 38.57, "base_depth 5분위": 23.00,
       "알파벳 A~C (뜻 없음)": 29.83}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    print("=" * 100)
    print("86v — 가짜약 **%d판** × seed %d  (특징 불필요 → 가격 적재 없음)" % (NP, NS))
    print("=" * 100, flush=True)

    base = r86.run(ev, 5, NS, cap=r74.CAP)
    beq = [r["equity_pct"] for r in base]
    print("기준선 (a) 무작위 자산 중앙 %+.2f%%\n" % st.median(beq), flush=True)

    def mk(salt):
        def fn(seed, t):
            h = int(hashlib.md5(("%s|%s" % (salt, t["code"])).encode()).hexdigest()[:8], 16)
            return (0 if h % 5 == 0 else 1, sl.order_key(seed, t))
        return fn

    vals, wins = [], []
    for i in range(NP):
        fn = mk("P%d" % i)
        rs = r86.run(ev, 5, NS, order_fn=fn, cap=r74.CAP)
        eq = [r["equity_pct"] for r in rs]
        pr = sorted(((1 + x / 100) / (1 + y / 100) - 1) * 100 for x, y in zip(eq, beq))
        m = pr[len(pr) // 2]
        w = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
        vals.append(m)
        wins.append(w)
        if i % 10 == 0:
            print("   %d/%d  (지금까지 보통 %+.2f%%)" % (i, NP, st.median(vals)), flush=True)

    a = sorted(vals)
    n = len(a)
    print("\n★ **가짜약 %d판** — 뜻 없는 결정적 20%% 앞세우기, 무작위 대비 짝 중앙" % n,
          flush=True)
    print("   보통 %+.2f%% · 5%% %+.2f%% · **95%% %+.2f%%** · 최소 %+.2f%% · 최대 %+.2f%%"
          % (a[n // 2], a[int(n * .05)], a[int(n * .95)], a[0], a[-1]), flush=True)
    k = sum(1 for w in wins if w > 50)
    lo, hi = wilson(k, n)
    print("   「이기는 판 > 50%%」인 가짜약 **%d/%d** = %.0f%% [%.0f, %.0f]"
          % (k, n, 100.0 * k / n, 100 * lo, 100 * hi), flush=True)
    print("   → 「결정적이면 낫다」가 성립하면 이 값이 «크게» 50%%를 넘어야 한다.", flush=True)

    print("\n★ 각 규칙이 가짜약 분포의 어디인가", flush=True)
    print("   %-26s %9s %11s %s" % ("규칙", "짝 중앙", "백분위", "95% 구간"), flush=True)
    print("   " + "-" * 66, flush=True)
    for nm, o in sorted(OBS.items(), key=lambda x: -x[1]):
        ge = sum(1 for x in a if x >= o)
        pct = 100.0 * (n - ge) / n
        wl, wh = wilson(ge, n)
        print("   %-26s %+8.2f%% %10.1f %s"
              % (nm, o, pct, "[%.1f, %.1f]" % (100 * (1 - wh), 100 * (1 - wl))), flush=True)
    print("\n   ★ 등록된 (b) 가 구간으로도 95 아래면 **가짜약과 구분되지 않는다.**", flush=True)
    print("   ★ «뜻 없는» 알파벳판이 (b) 보다 위면, 이 축에서 «뜻»은 값을 못 한다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
