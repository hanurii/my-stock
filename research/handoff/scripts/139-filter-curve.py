# -*- coding: utf-8 -*-
"""139 — **「좋은 것만 남기면 연 몇 개가 되고 얼마가 되나」 곡선** (사전등록 · 값 보기 «전»)

사용자(2026-08-31):
> 「이 돌파하는 종목 중 **훌륭한 종목들의 공통점만 뽑아 두고, 매수 추천엔 이 공통점에 해당하는
>  종목만 추천**하게 한다면 **1년에 200종목이 아니라 몇 종목이나 추천 대상에 올라올 수 있겠습니까?**
>  이렇게 셋업해 둔 매수 추천 종목으로 슬롯을 가득 채워 두면 수익이 크게 상승할 거라고 전 봅니다.」

# ★ 이 물음은 «두 조각»이다 — 갈라서 답한다
```
㉠ **「몇 개가 남나」**        — 산수다. 필터 강도만 정하면 «바로» 나온다
㉡ **「그러면 얼마가 되나」**   — 이건 **필터의 «정확도»에 달려 있다**
```
그래서 **같은 «수»를 남기되 두 가지 방식**으로 남겨 나란히 놓는다:
```
① **완벽한 필터** (사후 상위 X%)   🚨 룩어헤드 — **천장**이다
② **예측력 «0» 필터** (무작위 X%)  — 「그럴듯해 보이지만 아무것도 못 맞히는」 필터
```
> **①과 ②의 «차이»가 곧 「고르기로 얻을 수 있는 전부」다.**
> **그리고 ②가 현행보다 «나쁘면», 「덜 사는 것」 자체가 손해라는 뜻이다.**

# 격자
```
남기는 비율  100%(현행) · 50% · 25% · 10% · 5%
             → 연 추천 수가 207 → 104 → 52 → 21 → 10 건이 된다
목표 +30 / 손절 −10 · 칸 5 · 세후 · 지수 숏 · 운의 번호 20판
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **BS**★ | 🚨 관문 — 각 칸의 «남은 후보 수»가 목표 비율과 «맞아야» 한다 (±3%) |
| **BT** | 비율마다 **연 추천 수 · 매수 수 · 세후 총액 · 낙폭 · 투입률** |
| **BU**★ | ② 무작위 X% 가 현행(100%)보다 «나쁜가» — 나쁘면 **「덜 사는 것 자체가 손해」** |
| **BV** | 🚨 **①과 ②의 차이** = 「필터가 완벽할 때만 얻는 몫」 |

# ★ 방향을 «먼저» 적는다
```
㉮ **① 은 조일수록 «크게» 좋아질 것이다** — 133 에서 「상위 5% 빼면 전부 마이너스」였다
㉯ 🚨 **② 는 조일수록 «나빠질» 것이다** — 후보가 줄면 슬롯을 못 채우고, 대박도 같이 걸러진다
㉰ 🚨 **그래서 이 판의 답은 「필터를 만들면 좋아진다」가 «아니라»**
   **「필터가 «거의 완벽»해야 본전이고, 어설프면 오히려 손해다」**가 될 것으로 본다
㉱ 🚨 **그리고 그게 사용자님 제안의 «진짜 문턱»이다** — 「몇 개 남나」가 아니라
   **「그 몇 개 안에 대박이 몇 개나 들어 있나」**가 전부다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r124 = _load("r124", "124-jeonse-horizon.py")
r129 = _load("r129", "129-frontier.py")
import slot_sim_lots as sl                                       # noqa: E402
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
START, FEE = 1000.0, 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
TARGET, STOP = 30.0, 10.0
KEEP = (1.00, 0.50, 0.25, 0.10, 0.05)
YRS = 26.0


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 20
    print("=" * 106, flush=True)
    print("139 — **좋은 것만 남기면 연 몇 개가 되고 얼마가 되나** · 사전등록", flush=True)
    print("=" * 106, flush=True)
    print("★ 같은 «수»를 남기되 **① 완벽한 필터(룩어헤드) · ② 예측력 0 필터(무작위)**를 나란히",
          flush=True)
    print("🚨 방향 먼저: ①은 크게 좋아지고 **②는 나빠질 것** → 답은 «필터가 거의 완벽해야 본전»\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, "1999-04-01", "2026-08-21", "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    def account(x):
        fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
        fd = Counter(fdates)
        vv = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                 1.0 + x["equity_pct"] / 100.0)]
        cds, ccv, V = [vv[0][0]], [1.0], 1.0
        for i in range(1, len(vv)):
            if vv[i - 1][1] <= 0:
                break
            d = vv[i][0]
            rl = vv[i][1] / vv[i - 1][1] - 1.0
            sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
            V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
            cds.append(d)
            ccv.append(max(V, 1e-9))
        real = {}
        for d, pl in x["exit_log"]:
            real[d] = real.get(d, 0.0) + pl
        m_, _rc = r129.shape(cds, ccv)
        return r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1), m_, len(fdates)

    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, 0.5
    ev, _b1, _b2 = r91.replay(by_f)
    score = []
    for t in ev:
        m = t["masks"][next(iter(t["masks"]))]
        r_ = 0.0
        for _d, sh, px in m["exits"]:
            r_ += sh * (px / t["entry_px"] * 100.0 - 100.0)
        score.append((r_, t))
    print("바탕 후보 **%s건** (연 %.0f건)\n"
          % ("{:,}".format(len(ev)), len(ev) / YRS), flush=True)

    res = {}
    with r91.r41.Cost(*r91.COST):
        for kp in KEEP:
            k = max(1, int(round(len(ev) * kp)))
            top = [t for _r, t in sorted(score, key=lambda x: -x[0])[:k]]
            rnd = random.Random(9090)
            rd = rnd.sample([t for _r, t in score], k)
            row = {}
            for lab, sub in (("① 완벽 (사후 상위)", top), ("② 예측력 0 (무작위)", rd)):
                gap = abs(len(sub) - k) / max(1, k)
                if gap > 0.03:
                    print("🚨 BS★ 미통과 — 남은 수 %d vs 목표 %d" % (len(sub), k), flush=True)
                    return 3
                rr = [sl.sim_lots(sub, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                  reserve=False, fill_rule="truncate", cash_rule="per_slot")
                      for s in range(n_seed)]
                ac = [account(x) for x in rr]
                row[lab] = {"post": st.median(a[0] for a in ac),
                            "mdd": st.median(a[1] for a in ac),
                            "n": st.median(a[2] for a in ac),
                            "expo": st.median(x["expo_mean"] for x in rr),
                            "cand": len(sub)}
            res["%.0f%%" % (kp * 100)] = row
            a, b = row["① 완벽 (사후 상위)"], row["② 예측력 0 (무작위)"]
            print("  남기는 비율 %-5s 연 추천 **%5.0f건**  |  ① 완벽 %8.0f만 (매수 %4.0f · 투입 %.0f%%)"
                  "  |  ② 무작위 %8.0f만 (매수 %4.0f · 투입 %.0f%%)"
                  % ("%.0f%%" % (kp * 100), len(top) / YRS, a["post"], a["n"], a["expo"],
                     b["post"], b["n"], b["expo"]), flush=True)

    base = res["100%"]["② 예측력 0 (무작위)"]["post"]
    print("\n" + "=" * 106, flush=True)
    print("### BT — 표", flush=True)
    print("  %-8s %10s %12s %12s %12s %10s"
          % ("남김", "연 추천", "**① 완벽**", "**② 무작위**", "차이(①−②)", "② 낙폭"), flush=True)
    print("  " + "-" * 70, flush=True)
    for kp in KEEP:
        k2 = "%.0f%%" % (kp * 100)
        a, b = res[k2]["① 완벽 (사후 상위)"], res[k2]["② 예측력 0 (무작위)"]
        print("  %-8s %9.0f건 %9.0f만 %11.0f만 %11.0f만 %+9.1f%%"
              % (k2, a["cand"] / YRS, a["post"], b["post"], a["post"] - b["post"], b["mdd"]),
              flush=True)

    print("\n  **BU★** 예측력 0 필터가 현행(100%)보다 «나쁜가»", flush=True)
    for kp in KEEP[1:]:
        k2 = "%.0f%%" % (kp * 100)
        b = res[k2]["② 예측력 0 (무작위)"]["post"]
        print("     %-5s → %8.0f만  (현행 %.0f만 대비 **%+.1f%%**)  %s"
              % (k2, b, base, 100.0 * (b - base) / base,
                 "**나쁨**" if b < base else "좋음"), flush=True)

    print("\n  **BV** 「필터가 완벽할 때만 얻는 몫」 = ① − ②", flush=True)
    for kp in KEEP[1:]:
        k2 = "%.0f%%" % (kp * 100)
        a = res[k2]["① 완벽 (사후 상위)"]["post"]
        b = res[k2]["② 예측력 0 (무작위)"]["post"]
        print("     %-5s  ① %8.0f만  −  ② %8.0f만  =  **%8.0f만** (%.1f배)"
              % (k2, a, b, a - b, a / max(1e-9, b)), flush=True)

    (r91.OUT / "139-filter-curve.json").write_text(
        json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 139-filter-curve.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
