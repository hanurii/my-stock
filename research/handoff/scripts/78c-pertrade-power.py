# -*- coding: utf-8 -*-
"""78c — **자를 바꾸면 「150년」이 줄어드는가**. 사용자 질문(2026-08-26).

## 왜 묻나
「몇 년 필요한가」는 **계좌 잔고 곡선 한 줄**을 놓고 잰다. 그런데
```
9년간 신호 3,040건  →  5칸이라 실제로 산 것 231건  →  **92.4% 를 버린다**
```
**3,040 개의 정보를 «25~110 개짜리 블록»으로 재고 있다.** 그래서 150년이 나온다.
→ **거래당 축**에서는 표본이 3,040 이다. 자를 바꾸면 필요 연수가 줄어드는가?

## 🚨 답하기 «전»에 못 박는 것 — 거래당이 «무엇을 못 답하는가»
[[verification-failure-modes]] 유형 21: **거래당으로 «자금 배분»을 판정할 수 없다.**
- 거래당은 **칸 경쟁**을 못 본다(오래 들면 다른 거래를 못 산다)
- **복리**도, **노출**도 안 들어간다
> **그러므로 거래당이 0 을 배제해도 「계좌가 더 번다」가 아니다.**
> **답하는 것은 「이 거래 하나만 놓고 보면 나눠 사는 게 나은가」뿐이다.**

## 두 가지 자를 «둘 다» 낸다
```
단순 거래당    r₁ − r₀                 ← M1 이 «자본을 덜 쓴다»는 걸 무시한다
자본 가중      c₁·r₁ − 1·r₀            ← c₁ = 증액했으면 1.0, 안 했으면 0.5
```
**둘이 갈리면 그 자체가 답이다** — 「덜 쓰고 비슷하게 번다」인지 「같은 돈으로 더 번다」인지.

## 표집: **진입일 블록** 부트스트랩
같은 날 산 거래는 상관돼 있다. 거래를 «진입일» 블록으로 묶어 재표집한다
(24번이 쓰는 축이고 `dataaxis`(일별 자산)와는 다른 코드다).

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/78c-pertrade-power.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import slot_sim                                              # noqa: E402

_s = _u.spec_from_file_location("r78", HERE / "78-source-quotes.py")
r78 = _u.module_from_spec(_s)
_s.loader.exec_module(r78)
r77, r74, r41 = r78.r77, r78.r74, r78.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
BLOCKS = (20, 40, 80)
N_BOOT = 2000
YEARS = 9.0


def trade_ret(t):
    """거래 하나의 «순수익 %»와 «쓴 자본»(평소 한 칸 = 1.0 기준).

    트랜치별 취득가로 각각 계산해 몫으로 가중한다 — `slot_sim_lots.close_out` 과 같은 산술.
    """
    m = t["masks"][(True,) * (len(t["shares"]) - 1)]
    lots = m["lots"]
    cap = sum(w for _d, _px, w, _k in lots)          # 실제로 쓴 자본
    r = 0.0
    for epx_i, w_i in ((px, w) for _d, px, w, _k in lots):
        for _d2, fr, px in m["exits"]:
            r += (w_i / max(1e-12, cap)) * fr * slot_sim.net(round(px / epx_i * 100 - 100, 2))
    return r, cap


def boot(pairs, block, rnd):
    """진입일 블록 재표집 — `pairs` = [(진입일, 값)]. 평균의 밴드를 낸다."""
    byday = defaultdict(list)
    for d, v in pairs:
        byday[d].append(v)
    days = sorted(byday)
    n = len(days)
    out = []
    for _ in range(N_BOOT):
        vals, got = [], 0
        while got < n:
            a = rnd.randint(0, max(0, n - block))
            for d in days[a:a + block]:
                vals.extend(byday[d])
            got += block
        out.append(st.mean(vals) if vals else 0.0)
    out.sort()
    m = len(out)
    return {"mean": st.mean(out), "lo": out[int(m * .025)], "hi": out[int(m * .975)],
            "excl0": (out[int(m * .025)] > 0) or (out[int(m * .975)] < 0)}


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 100, flush=True)
    print("78c — 자를 «거래당»으로 바꾸면 「150년」이 줄어드는가", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    ev0, _b0 = r77.replay(by2, (1.0,), "avg", r78.B)
    ev1, _b1 = r77.replay(by2, (0.5, 0.5), "avg", r78.TR(3))
    k0 = {(t["scan_date"], t["code"], t["pattern"]): t for t in ev0}
    print("경로 %d → 조합 %d · P0 진입 %d · M1 진입 %d\n"
          % (n_all, n_sel, len(ev0), len(ev1)), flush=True)

    simple, weighted, n_add, n_miss = [], [], 0, 0
    with r41.Cost(*r78.COST):
        for t in ev1:
            f = k0.get((t["scan_date"], t["code"], t["pattern"]))
            if f is None:
                n_miss += 1
                continue
            r1, c1 = trade_ret(t)
            r0, _c0 = trade_ret(f)
            n_add += (c1 > 0.75)
            simple.append((t["entry_date"], r1 - r0))
            weighted.append((t["entry_date"], c1 * r1 - r0))
    n = len(simple)
    print("짝지은 거래 **%d건** (짝 못 찾음 %d) · 그중 증액이 난 것 %d건 (%.1f%%)"
          % (n, n_miss, n_add, 100.0 * n_add / max(1, n)), flush=True)
    print("★ 자산 축은 이 자료를 «블록 25~110개»로 줄여 쟀다. 여기서는 «%d건»이 그대로 산다.\n"
          % n, flush=True)

    rnd = random.Random(780826)
    RES = {}
    for lbl, data in (("단순 거래당  r₁ − r₀", simple),
                      ("자본 가중   c₁·r₁ − r₀", weighted)):
        vals = [v for _d, v in data]
        win = 100.0 * sum(1 for v in vals if v > 0) / len(vals)
        print("─" * 100, flush=True)
        print("%s   평균 **%+.4f%%p** · 중앙 %+.4f%%p · 이긴 거래 %.1f%%"
              % (lbl, st.mean(vals), st.median(vals), win), flush=True)
        RES[lbl] = {"mean": st.mean(vals), "median": st.median(vals), "win": win,
                    "blocks": {}}
        for b in BLOCKS:
            r = boot(data, b, rnd)
            # 필요 배수 — 자산 축과 «같은 산수»(T > (hw/|L|)²)
            L, hw = r["mean"], (r["hi"] - r["mean"]) if r["mean"] < 0 else (r["mean"] - r["lo"])
            T = (hw / abs(L)) ** 2 if L else float("inf")
            RES[lbl]["blocks"][b] = {**r, "T": T, "years": T * YEARS}
            print("  블록 %2d  95%% [%+.4f, %+.4f]  %s  ·  **필요 %.2f배 = %.0f년**"
                  % (b, r["lo"], r["hi"], "**0 제외**" if r["excl0"] else "0 포함",
                     T, T * YEARS), flush=True)

    print("\n" + "=" * 100, flush=True)
    print("🚨 이 표가 «답하지 않는» 것 — 값을 보기 전에 적어 둔 것", flush=True)
    print("  거래당은 **칸 경쟁·복리·노출**을 못 본다(유형 21).", flush=True)
    print("  **0 을 배제해도 「계좌가 더 번다」가 아니다.**", flush=True)
    print("  답하는 것은 「이 거래 하나만 놓고 보면 나눠 사는 게 나은가」뿐이다.", flush=True)
    (OUT / "78c-pertrade-power.json").write_text(
        json.dumps({"n": n, "n_add": n_add, "res": RES}, ensure_ascii=False,
                   indent=1, default=str), encoding="utf-8")
    print("\n저장: 78c-pertrade-power.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
