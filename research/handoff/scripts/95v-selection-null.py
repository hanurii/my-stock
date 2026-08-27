# -*- coding: utf-8 -*-
r"""95v — **고르기 창의 `+34.54%p` 가 「5칸 중 최선」이 만든 값인가.** (서술 · 예산 0)

검증 세션(`aa99e4b0`) 지적:
> 「고르기에서 MDE 를 넘었다」가 근거가 «안» 된다 — **MDE 는 «단일 비교» 자**인데
> 그 칸은 **«5분위 중 최선»**으로 뽑혔다. 귀무에서도 「5칸 중 최대」는 단일 비교 MDE 를 자주 넘는다.
> **92 ㉤ · 89 ⑤ 와 같은 자리다.**

가르는 검사
```
고르기 창에서 «5칸 중 최선»의 귀무 분포를 만든다 (분위 딱지를 «연도 안»에서 섞는다)
관측이 그 분포 «밖»  →  그 창에선 진짜였다  =  **시간 변동(국면)**
관측이 그 분포 «안»  →  고르기가 뽑은 값     =  **과적합**
```
🚨 **고르기 창은 이미 쓴 창**이고 «선택 절차의 잡음»을 재는 것이라 **판정 창을 안 태운다. 예산 0.**
🚨 **관측을 «같은 판수»로 다시 잰다** — 100판 관측 vs 20판 귀무를 견주면 유형 25 다.
🚨 **88 의 「과적합이 아니라 국면 의존」을 여기 그대로 옮기지 않는다** —
   **88 에는 반례 구간(2026)이 있었고 95 에는 없다.** 통과 전까지는 「구분할 수 없다」다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("m95", HERE / "95-marketcap.py")
m = _u.module_from_spec(_s)
_s.loader.exec_module(m)

N_NULL = 200
N_SEED = 20          # 귀무와 관측이 «같은» 판수를 쓴다 (유형 25)
NQ = 5


def best_of_five(ev, ctl_eq, n_seed):
    """5칸 각각을 우선 담아 보고 «최선»의 짝차 중앙을 낸다 — 등록 절차와 같은 모양."""
    best = -1e18
    for q in range(NQ):
        trt = m.run(ev, m.prio_for(q), n_seed)
        dif = [t["equity_pct"] - c for t, c in zip(trt, ctl_eq)]
        v = st.median(dif)
        if v > best:
            best = v
    return best


def main() -> int:
    print("=" * 100, flush=True)
    print("95v — 고르기 창의 +34.54%p 가 «5칸 중 최선»이 만든 값인가 (서술 · 판정에 안 씀)",
          flush=True)
    print("=" * 100, flush=True)

    capdb = json.loads(m.CAP.read_text(encoding="utf-8"))
    funddb = json.loads(m.m92.FUND.read_text(encoding="utf-8"))["by"]
    rowsP, _a, _b = m.m92.build(tuple(range(1999, 2013)), *m.m92.PICK, funddb)
    _c, _n, fqroe = m.m92.cells_for(rowsP, "roe")
    ev, _ms = m.build(tuple(range(1999, 2013)), *m.PICK, capdb, funddb, m.make_roef(fqroe))
    cuts, fq = m.quintile_fn(ev)
    for t in ev:
        t["_q"] = fq(t["_logcap"])
        t["_q0"] = t["_q"]
        t["_yr"] = int(t["entry_date"][:4])
    print("고르기 거래 %s · seed %d · 귀무 %d판" % ("{:,}".format(len(ev)), N_SEED, N_NULL),
          flush=True)

    ctl = m.run(ev, None, N_SEED)
    ctl_eq = [x["equity_pct"] for x in ctl]

    obs = best_of_five(ev, ctl_eq, N_SEED)
    print("\n**관측(같은 %d판) 「5칸 중 최선」 = %+.2f%%p**" % (N_SEED, obs), flush=True)
    print("   (100판에서는 +34.54%p 였다 — 판수가 다르면 값도 달라진다)", flush=True)

    # ── 귀무: 분위 딱지를 «연도 안»에서 섞는다 ──────────────────────────
    byyear = defaultdict(list)
    for i, t in enumerate(ev):
        byyear[t["_yr"]].append(i)
    rnd = random.Random(0)
    nulls = []
    for b in range(N_NULL):
        for _y, idx in byyear.items():
            labs = [ev[i]["_q0"] for i in idx]
            rnd.shuffle(labs)
            for i, q in zip(idx, labs):
                ev[i]["_q"] = q
        nulls.append(best_of_five(ev, ctl_eq, N_SEED))
        if (b + 1) % 25 == 0:
            ns = sorted(nulls)
            print("   귀무 %3d/%d … 중앙 %+.2f · 95%% %+.2f · 최대 %+.2f"
                  % (b + 1, N_NULL, ns[len(ns) // 2], ns[int(len(ns) * .95)], ns[-1]),
                  flush=True)
    for i, t in enumerate(ev):
        t["_q"] = t["_q0"]

    ns = sorted(nulls)
    pct = 100.0 * sum(1 for x in nulls if x < obs) / N_NULL
    print("\n" + "=" * 100, flush=True)
    print("귀무 %d판 「5칸 중 최선」 — 중앙 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
          % (N_NULL, ns[len(ns) // 2], ns[int(N_NULL * .95)], ns[-1]), flush=True)
    print("관측 **%+.2f%%p** → **%.1f 백분위**" % (obs, pct), flush=True)
    print("\n판정(서술): %s" % (
        "**분포 «밖» — 고르기 창에서는 진짜였다. 판정 창에서 사라진 것은 «시간 변동»에 가깝다**"
        if pct >= 95 else
        ("**분포 «안» — 「5칸 중 최선」이 만든 값. «과적합»에 가깝다**" if pct < 80 else
         "**애매하다(80~95 백분위) — 이 자료로는 «구분할 수 없다»**")), flush=True)
    print("🚨 어느 쪽이든 **95 의 판정(미통과)은 안 바뀐다.** 이건 «왜»에 대한 서술이다.", flush=True)
    (m.r91.OUT / "95v-selection-null.json").write_text(json.dumps(
        {"obs": obs, "n_null": N_NULL, "n_seed": N_SEED, "pct": pct,
         "null_med": ns[len(ns) // 2], "null_p95": ns[int(N_NULL * .95)], "null_max": ns[-1]},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
