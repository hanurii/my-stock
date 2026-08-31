# -*- coding: utf-8 -*-
"""137 — **「잘 고르면 얼마나 좋아지나」 천장부터 잰다** (사전등록 · 값 보기 «전»)

사용자(2026-08-31): 「돌파 주문 나간 게 200개가 되는데 실제 매수는 20개밖에 못 하니 아쉬운데요.
**200개에서도 가장 좋은 것만 선별해서 20개 안에 담도록 개선이 가능할까요?** … 이를 검증해 줄 수
있습니까?」

# ★ 왜 「천장」부터인가 — **우리는 이 길에서 «이미 실패한 적»이 있다**
```
86번   「규칙으로 고르기」는 «잴 수 없었다» —
       가짜약 200판이 **72%p 를 훑었고** 등록한 규칙은 **78.0 백분위**에 그쳤다 (유형 26)
89번   진입시점 12축 → 최선(base_depth) +8.29%p 였으나 귀무 **94.0 백분위** = 95% 문턱 미달
```
**고르는 규칙을 «찾아 나서면» 반드시 뭔가 찾아진다. 없어도 찾아진다.**
그래서 **규칙을 만들기 «전»에, 「완벽하게 골랐다면 얼마였나」(천장)를 먼저 잰다.**
```
천장이 «작으면»  → **이 길은 닫힌다.** 규칙을 아무리 잘 만들어도 얻을 게 없다
천장이 «크면»    → **추구할 값어치가 확인된다.** 그때 «사전등록한» 소수 축으로 2단계를 간다
```

# 재는 법
```
같은 날 여러 개가 돌파하면 지금은 **«무작위»로 고른다**(운의 번호가 정하는 것이 바로 이것이다).
`slot_sim_lots` 의 **`order_fn(seed, t)`** 훅으로 그 «순서»만 바꿔 세 팔을 만든다:

① **무작위** (현행)        운의 번호 30판
② **천장** (사후 최선)     🚨 **결과를 «미리 알고» 좋은 것부터 담는다 — 룩어헤드다.
                           달성 «불가능»한 상한이지 전략이 아니다**
③ **바닥** (사후 최악)     나쁜 것부터 담는다 — 「운이 최악이면」의 하한

목표 +20/−10 과 +30/−10 둘 다 · 세후 · 지수 숏 얹음
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **BL**★ | 🚨 관문 — 세 팔의 «매수 수»가 서로 크게 다르지 않아야 한다(순서만 바꾼 것이므로) |
| **BM** | 천장 ÷ 무작위 중앙 = **「잘 고르면 몇 배」** |
| **BN** | 무작위가 «천장과 바닥 사이 어디»에 있는가 (0% = 바닥, 100% = 천장) |

# ★ 방향을 «먼저» 적는다
```
㉮ **천장은 «아주» 높을 것이다** — 132 에서 «무작위 순서»만으로 5~95% 폭이 9,914만이었다.
   그건 「고르는 순서」가 만드는 폭이고, 완벽히 고르면 그보다 훨씬 위다
㉯ 🚨 **그래서 이 판은 「가능성이 있다」를 «거의 확실히» 보여줄 것이다 —
   그리고 그게 «함정»이다.** 천장이 높다는 건 「잘 고르면 좋다」일 뿐,
   **「고를 수 있다」가 아니다.** 2단계에서 진짜 시험이 온다
㉰ 바닥도 «아주» 낮을 것이다. 무작위는 대략 «가운데»에 있을 것으로 본다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
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
TARGETS = (20.0, 30.0)
STOP = 10.0


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 30
    print("=" * 100, flush=True)
    print("137 — **「잘 고르면 얼마나 좋아지나」 천장부터** · 사전등록", flush=True)
    print("=" * 100, flush=True)
    print("★ 규칙을 만들기 «전»에 「완벽히 골랐다면 얼마였나」를 먼저 잰다", flush=True)
    print("🚨 천장은 **룩어헤드**다 — 달성 «불가능»한 상한이지 전략이 아니다\n", flush=True)

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
        """세후 계좌 잔액 (지수 숏 + 수수료 포함)."""
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
        return (r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1),
                r129.shape(cds, ccv)[0], len(fdates))

    out = {}
    for tg in TARGETS:
        r91.TARGET, r91.STOP, r91.HALF = tg, STOP, 0.5
        ev, _b1, _b2 = r91.replay(by_f)
        # 🚨 사후 수익률 — **이것을 «순서»에 쓰는 것이 룩어헤드다**
        fut = {}
        for t in ev:
            m = t["masks"][next(iter(t["masks"]))]
            r_ = 0.0
            for _d, sh, px in m["exits"]:
                r_ += sh * (px / t["entry_px"] * 100.0 - 100.0)
            fut[(t["code"], t["scan_date"], t["entry_date"])] = r_

        def key_of(t):
            return fut.get((t["code"], t["scan_date"], t["entry_date"]), 0.0)

        arms = {}
        with r91.r41.Cost(*r91.COST):
            rr = [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                              reserve=False, fill_rule="truncate", cash_rule="per_slot")
                  for s in range(n_seed)]
            arms["① 무작위 (현행)"] = [account(x) for x in rr]
            for nm, sgn in (("② **천장** (사후 최선)", -1.0), ("③ 바닥 (사후 최악)", +1.0)):
                x = sl.sim_lots(ev, seed=0, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                reserve=False, fill_rule="truncate", cash_rule="per_slot",
                                order_fn=lambda _s, t: sgn * key_of(t))
                arms[nm] = [account(x)]

        ns = [st.median(a[2] for a in v) for v in arms.values()]
        ok = (max(ns) - min(ns)) / max(1, st.median(ns)) < 0.15
        print("**BL★ 관문** [목표 +%.0f] 세 팔 매수 수 %s · 어긋남 %.1f%% · **%s**"
              % (tg, " / ".join("%.0f" % n for n in ns),
                 100.0 * (max(ns) - min(ns)) / max(1, st.median(ns)),
                 "통과" if ok else "🚨 미통과 — 순서 말고 다른 게 바뀌었다"), flush=True)

        print("\n### 목표 +%.0f / 손절 −10 — 세후 계좌" % tg, flush=True)
        print("  %-24s %12s %10s %9s" % ("", "세후 총액", "낙폭", "매수"), flush=True)
        print("  " + "-" * 60, flush=True)
        vals = {}
        for nm, v in arms.items():
            a = st.median(x[0] for x in v)
            m_ = st.median(x[1] for x in v)
            n_ = st.median(x[2] for x in v)
            vals[nm] = a
            print("  %-24s %9.0f만 %+9.1f%% %8.0f" % (nm, a, m_, n_), flush=True)
        lo = vals["③ 바닥 (사후 최악)"]
        mid = vals["① 무작위 (현행)"]
        hi_ = vals["② **천장** (사후 최선)"]
        print("", flush=True)
        print("  **BM** 천장 / 무작위 = **%.1f배**  (%.0f만 -> %.0f만)"
              % (hi_ / mid, mid, hi_), flush=True)
        print("  **BN** 무작위는 바닥~천장의 **%.1f%%** 지점  (바닥 %.0f만 · 천장 %.0f만)"
              % (100.0 * (mid - lo) / max(1e-9, hi_ - lo), lo, hi_), flush=True)
        out["%.0f" % tg] = {k: st.median(x[0] for x in v) for k, v in arms.items()}
        print("", flush=True)

    print("=" * 100, flush=True)
    print("  🚨 **천장은 «룩어헤드»다.** 「잘 고르면 좋다」를 보여줄 뿐", flush=True)
    print("     **「고를 수 있다」는 전혀 보여주지 않는다.** 그건 2단계의 일이다", flush=True)
    (r91.OUT / "137-ceiling.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 137-ceiling.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
