# -*- coding: utf-8 -*-
"""자료 축 밴드 — **자산에도 「자료가 달랐으면」을 묻는다.**

왜 필요한가
-----------
🚨 `slot_sim*.band()` 의 5~95%는 **seed 축**이다 — 거래 집합을 고정한 채
**슬롯 선택 난수만** 바꾼다. **M10: seed 축은 판정에 못 쓴다.**
그런데 1회차까지 「본전 통과 = 자산 5% 하단 > 0」을 **seed 축으로 걸었다**(2026-08-24 자책).

왜 이렇게 재는가
----------------
거래를 날짜 블록으로 재표집해 시뮬에 먹이면 **결착일이 블록 밖으로 나가** 시뮬이 깨진다.
그래서 **재는 대상을 바꾼다**:
  ① 시드마다 시뮬을 한 번 돌려 **일별 자산 계열**을 얻고
  ② 그 계열의 **일별 수익률**을 블록으로 재표집해 **곱한다**
**M32-2 규약**: 스트림(seed)을 **먼저** 고르고 그 안에서 블록을 뽑는다.
단일 스트림 구간은 버릴 값이다.

🚨 **블록 길이 민감도** — 보유 기간 중앙 15일 · P90 71일인데 블록이 20~40일이면
**포지션이 블록 경계에서 잘려 자기상관을 덜 잡고 구간이 «좁게»** 나온다(우리에게 유리한 방향).
그래서 **20 / 40 / 80** 세 판을 낸다. **80이 P90(71일)을 덮는다.**
**헤드라인은 가장 넓은 구간**(문턱을 넘기 어렵게 잡는 쪽)으로 한다.

짝비교
------
같은 seed·같은 재표집에서
```
Δ = Σ [ log(1+r_변형) − log(1+r_0회차) ]      →   exp(Δ) − 1 = 누적 상대 성과
```
**슬롯 선택 밴드(±146%p)가 대부분 상쇄되는 게 이 지표다.**
"""
from __future__ import annotations

import math
import random
import statistics as st

BLOCKS = (20, 40, 80)
N_STREAM = 10          # M32-2
N_REP = 100            # 스트림당 → 총 1,000
BOOT_SEED = 420824


def rets(curve):
    """[(날짜, 자산)] → 일별 수익률. 첫날은 1.0 에서 시작한 것으로 본다."""
    out, prev = [], 1.0
    for _d, eq in curve:
        out.append(eq / prev - 1.0 if prev != 0 else 0.0)
        prev = eq
    return out


def _resample(r, block, rnd):
    """블록 재표집 — 원 길이만큼 채운다."""
    n = len(r)
    if n == 0:
        return []
    out = []
    while len(out) < n:
        a = rnd.randint(0, max(0, n - block))
        out.extend(r[a:a + block])
    return out[:n]


def _compound(r):
    x = 1.0
    for v in r:
        x *= (1.0 + v)
    return (x - 1.0) * 100


def band_total(curves, block, n_stream=N_STREAM, n_rep=N_REP, seed=BOOT_SEED):
    """자료 축 총수익 밴드. `curves` = 스트림(seed)별 일별 자산 계열 목록."""
    rnd = random.Random(seed)
    vals = []
    for s in range(min(n_stream, len(curves))):
        r = rets(curves[s])
        for _ in range(n_rep):
            vals.append(_compound(_resample(r, block, rnd)))
    vals.sort()
    m = len(vals)
    nb = len(rets(curves[0])) / block if curves else 0
    return {"block": block, "n": m, "n_blocks": nb, "median": st.median(vals),
            "lo": vals[int(m * .025)], "hi": vals[int(m * .975)],
            "excl0": (vals[int(m * .025)] > 0) or (vals[int(m * .975)] < 0)}


def band_paired(curves_v, curves_0, block, n_stream=N_STREAM, n_rep=N_REP, seed=BOOT_SEED):
    """🚨 **주판정** — 같은 seed·같은 재표집에서 «변형 − 0회차» 누적 상대 성과.

    `Δ = Σ[log(1+r_v) − log(1+r_0)]` → `exp(Δ)−1`.
    로그를 쓰므로 **곱셈이 덧셈이 되어 블록 재표집이 그대로 먹는다.**
    ⚠️ 수익률이 −100% 이하면 로그가 정의되지 않는다 — 그런 날은 −99.99%로 막는다
       (실제로는 안 나오지만, 나오면 **막았다는 사실을 세어 보고한다**).
    """
    rnd = random.Random(seed)
    vals, n_clamp = [], 0
    for s in range(min(n_stream, len(curves_v), len(curves_0))):
        rv, r0 = rets(curves_v[s]), rets(curves_0[s])
        n = min(len(rv), len(r0))
        d = []
        for i in range(n):
            a, b = rv[i], r0[i]
            if a <= -1.0:
                a = -0.9999
                n_clamp += 1
            if b <= -1.0:
                b = -0.9999
                n_clamp += 1
            d.append(math.log(1 + a) - math.log(1 + b))
        for _ in range(n_rep):
            vals.append((math.exp(sum(_resample(d, block, rnd))) - 1.0) * 100)
    vals.sort()
    m = len(vals)
    nb = (len(rets(curves_v[0])) / block) if curves_v else 0
    return {"block": block, "n": m, "n_blocks": nb, "n_clamp": n_clamp, "median": st.median(vals),
            "lo": vals[int(m * .025)], "hi": vals[int(m * .975)],
            "excl0": (vals[int(m * .025)] > 0) or (vals[int(m * .975)] < 0)}


def sweep(curves_v, curves_0=None, blocks=BLOCKS):
    """블록 20/40/80 세 판. **헤드라인은 가장 넓은 구간**을 쓴다."""
    out = {}
    for b in blocks:
        out[b] = (band_paired(curves_v, curves_0, b) if curves_0 is not None
                  else band_total(curves_v, b))
    widest = max(out, key=lambda b: out[b]["hi"] - out[b]["lo"])
    out["_widest"] = widest
    out["_verdict_block"] = widest
    return out


def fmt(sw, label=""):
    lines = []
    for b in BLOCKS:
        r = sw[b]
        # 🚨 블록 «수»도 찍는다 — 80에서 구간이 좁아지는 게 「자기상관이 없어서」인지
        #    「재표집 단위가 줄어 분산이 준 것」인지는 다른 얘기다.
        lines.append("    블록 %-3d (계열/블록 %5.1f개)  중앙 %+9.2f%%  "
                     "95%% %+9.2f ~ %+9.2f  폭 %8.2f  %s%s"
                     % (b, r.get("n_blocks", 0), r["median"], r["lo"], r["hi"],
                        r["hi"] - r["lo"], "**0 제외**" if r["excl0"] else "0 포함",
                        "   ← 가장 넓음(헤드라인)" if b == sw["_widest"] else ""))
    if label:
        lines.insert(0, "  %s" % label)
    return "\n".join(lines)
