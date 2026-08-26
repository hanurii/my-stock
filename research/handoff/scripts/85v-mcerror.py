# -*- coding: utf-8 -*-
"""85v 부속 4 — **96.7 vs 97.7 은 «몬테카를로 잡음» 안에서 갈리고 있다.**

무엇이 문제인가
---------------
㉮ 의 「연도 안 섞기 · 10칸 중 최선」 백분위가 세 판에서 이렇게 나왔다:
```
두뇌 세션 300판        **96.7**   → 본페로니 문턱 97.5 «미달»
내 timeblock 300판     **97.7**   → 97.5 «초과»
내 fragility 300판     98.3       ← 🚨 내 버그(표본안을 통째로 섞음). 폐기.
```
**판정이 «문턱을 사이에 두고» 갈린다. 그런데 셋 다 300판이다.**

귀무 300판에서 「관측 이상」이 나오는 건수는 7~10건뿐이다. 이항 잡음이
`100·√(p(1−p)/N)` = **±0.90%p**(p=0.025, N=300) 라 **셋은 서로 1 표준오차 안이다.**
→ **지금 셋은 «다른 답»이 아니라 «같은 값의 세 번 뽑기»다.**

그래서 판수를 크게 올려 **구간**을 낸다. 구간이 97.5 를 «품으면»
**「이 자료로는 어느 쪽인지 못 가린다」**가 정답이고, 어느 한쪽을 고르는 건
자가 아니라 **뽑기가 결론을 만드는 것**이다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85v-mcerror.py [N] [which]
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import os
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s)
_s.loader.exec_module(r85)
FEATS, SPLIT = r85.FEATS, r85.SPLIT
CACHE = Path(os.environ.get("TEMP", "/tmp")) / "85v-feat-cache.json"

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4000
ONLY = sys.argv[2] if len(sys.argv) > 2 else "both"


def wilson(k, n, z=1.96):
    """이항 비율의 윌슨 구간 — 꼬리가 얇을 때 정규근사보다 낫다."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def best_of(ins, outs):
    bb = st.mean([y for _r, y in outs])
    best = None
    for f in FEATS:
        rr = r85.test_one(ins, outs, f, "")
        if rr:
            v = rr[0] - bb
            best = v if best is None else max(best, v)
    return best


def shuffled(pairs, rnd, blocks):
    ys = [y for _r, y in pairs]
    z = ys[:]
    idx = defaultdict(list)
    for i, b in enumerate(blocks):
        idx[b].append(i)
    for _b, ii in idx.items():
        vals = [ys[i] for i in ii]
        rnd.shuffle(vals)
        for i, v in zip(ii, vals):
            z[i] = v
    return [(r, y2) for (r, _y), y2 in zip(pairs, z)]


def main() -> int:
    if not CACHE.exists():
        print("🚨 캐시가 없다 — `85v-fragility.py` 를 먼저 돌린다")
        return 2
    recs = json.loads(CACHE.read_text(encoding="utf-8"))["recs"]
    print("=" * 98)
    print("85v ④ — 귀무 판수를 %d 로 올려 **백분위의 «구간»**을 낸다" % N)
    print("   섞기 = 연도 «안» (표본안·표본밖 «둘 다») — 두뇌 세션 구현과 같은 규약")
    print("=" * 98, flush=True)

    for nm, thr in (("㉮ MFE≥+20%", 20.0), ("㉯ MFE≥+100%", 100.0)):
        if ONLY != "both" and ONLY not in nm:
            continue
        ins, outs, di, do = [], [], [], []
        for r in recs:
            y = 1.0 if r["mfe"] >= thr else 0.0
            if r["d"] < SPLIT:
                ins.append((r["f"], y))
                di.append(r["d"][:4])
            else:
                outs.append((r["f"], y))
                do.append(r["d"][:4])
        obs = best_of(ins, outs)
        print("\n▶ %s — 관측 최선 **%+.2f%%p**" % (nm, obs * 100), flush=True)
        rnd = random.Random(20260827)
        ge = 0
        vals = []
        for it in range(N):
            b = best_of(shuffled(ins, rnd, di), shuffled(outs, rnd, do))
            if b is not None:
                vals.append(b)
                ge += (b >= obs)
            if it and it % 500 == 0:
                p = ge / it
                print("   %d/%d — 지금까지 «관측 이상» %d건 → 백분위 %.2f"
                      % (it, N, ge, 100 * (1 - p)), flush=True)
        n = len(vals)
        lo, hi = wilson(ge, n)
        a = sorted(vals)
        print("   귀무 %d판 — 보통 %+.2f%%p · 95%% %+.2f%%p · **97.5%% %+.2f%%p** · 최대 %+.2f%%p"
              % (n, a[n // 2] * 100, a[int(n * .95)] * 100, a[int(n * .975)] * 100,
                 a[-1] * 100), flush=True)
        print("   「관측 이상」 **%d / %d**" % (ge, n), flush=True)
        print("   → 백분위 **%.2f**  ·  95%% 구간 **[%.2f, %.2f]**"
              % (100 * (1 - ge / n), 100 * (1 - hi), 100 * (1 - lo)), flush=True)
        thr975 = 97.5
        p_lo, p_hi = 100 * (1 - hi), 100 * (1 - lo)
        if p_lo <= thr975 <= p_hi:
            print("   🚨 **구간이 본페로니 문턱 97.5 를 «품는다» → 「어느 쪽인지 못 가린다」**",
                  flush=True)
            print("      → 300판 셋(96.7 · 97.7 · 98.3)이 갈린 것은 «자»가 아니라 **뽑기**다.",
                  flush=True)
        elif p_lo > thr975:
            print("   → 구간이 전부 97.5 «위» = 통과로 읽을 수 있다", flush=True)
        else:
            print("   → 구간이 전부 97.5 «아래» = 미통과로 읽을 수 있다", flush=True)
        print("   (참고: 순열 p = (1+%d)/%d = **%.4f**)" % (ge, n + 1, (1 + ge) / (n + 1)),
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
