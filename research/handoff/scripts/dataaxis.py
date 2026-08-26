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
ALIGN_STATS = []       # 정렬 통계 — 「같은 날짜인가」의 증거


def rets(curve):
    """[(날짜, 자산)] → 일별 수익률. 첫날은 1.0 에서 시작한 것으로 본다."""
    out, prev = [], 1.0
    for _d, eq in curve:
        out.append(eq / prev - 1.0 if prev != 0 else 0.0)
        prev = eq
    return out


CYCLIC = [False]       # 🚨 True 면 «순환» 블록 재표집. 기본은 옛 동작 그대로.


def _resample(r, block, rnd):
    """블록 재표집 — 원 길이만큼 채운다.

    🚨 **기본(이동 블록)은 계열의 «양 끝»을 덜 뽑는다** (2026-08-25, 검증 세션 `fd2f8bc2`).
       시작점이 `[0, n−block]` 로 제한되므로 가운데 날은 `block` 개의 시작점이 덮지만
       첫날·마지막날은 **1 개**뿐이다. 블록 80 이면 양 끝 79일씩 ≈ 2,250일의 7% 가
       덜 들어간다. 이동 블록 부트스트랩의 알려진 성질이다.
    `CYCLIC[0] = True` 로 두면 **순환 블록**(끝에서 처음으로 감아 시작점을 `[0, n−1]`
       전체로 여는 것)이 되어 모든 날이 «정확히 block 번» 덮인다.
    🚨 기본값을 바꾸지 않는다 — 24·73·74 의 옛 값이 조용히 달라지면 안 된다.
       대신 «둘을 대조해» 영향을 재고, 그 결과를 판정 문서에 적는다.
    """
    n = len(r)
    if n == 0:
        return []
    out = []
    if CYCLIC[0]:
        while len(out) < n:
            a = rnd.randint(0, n - 1)
            out.extend(r[a:a + block] if a + block <= n
                       else r[a:] + r[:a + block - n])
        return out[:n]
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


def align(cv, c0):
    """🚨 **두 곡선을 «같은 날짜 축»에 올린다.**

    변형마다 청산일이 달라 곡선 길이가 다르다. 그대로 짝지으면
    **다른 날의 수익률을 마주 세우게 된다** — 짝비교의 뜻이 사라진다.
    두 날짜의 «합집합»을 만들고 값이 없는 날은 **직전 값을 끌어온다**(그날 손익이 없다는 뜻).
    """
    dv, d0 = dict(cv), dict(c0)
    days = sorted(set(dv) | set(d0))
    # 🚨 «버려진 날은 없다»(합집합) — 대신 «한쪽에만 있어 끌어온 날»을 센다.
    #    많이 끌어왔으면 두 곡선이 다른 달력 위에 있다는 뜻이고 그 자체가 한계다.
    ALIGN_STATS.append({"days": len(days), "only_v": len(set(dv) - set(d0)),
                        "only_0": len(set(d0) - set(dv)),
                        "both": len(set(dv) & set(d0))})
    out_v, out_0 = [], []
    lv = l0 = 1.0
    for d in days:
        lv = dv.get(d, lv)
        l0 = d0.get(d, l0)
        out_v.append((d, lv))
        out_0.append((d, l0))
    return out_v, out_0


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
        av, a0 = align(curves_v[s], curves_0[s])   # 🚨 같은 날짜 축에 올린다
        rv, r0 = rets(av), rets(a0)
        n = min(len(rv), len(r0))
        assert len(rv) == len(r0), "정렬 뒤에도 길이가 다르다"
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


def sweep(curves_v, curves_0=None, blocks=BLOCKS, n_stream=None, n_rep=None):
    """블록 20/40/80 세 판. **헤드라인은 가장 넓은 구간**을 쓴다.

    🚨 `n_stream`/`n_rep` 은 **기본값 None = 옛 동작 그대로**(스트림 10 × 재표집 100).
       2026-08-26 검증 세션 지적 — **자산 표는 200판인데 자료 축은 앞 10 seed 만 쓴다.**
       그래서 `band_paired` 중앙이 관측 짝 성과와 크게 어긋날 수 있다
       (77번: 짝200 +21.49% vs band_paired(10) +3.2%).
       **`T > (hw/|L|)²` 에 쓰려면 `L` 과 `hw` 가 «같은 구성»에서 나와야 하므로**
       그때는 `n_stream=200, n_rep=5` 처럼 «같은 몬테카를로 예산»으로 다시 돌린다."""
    kw = {}
    if n_stream is not None:
        kw["n_stream"] = n_stream
    if n_rep is not None:
        kw["n_rep"] = n_rep
    out = {}
    for b in blocks:
        out[b] = (band_paired(curves_v, curves_0, b, **kw) if curves_0 is not None
                  else band_total(curves_v, b, **kw))
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
