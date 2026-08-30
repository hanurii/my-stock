# -*- coding: utf-8 -*-
"""116 — **원전 사다리를 «낙폭»의 자로 다시 잰다** (사전등록 · 값 보기 «전»)

# 🚨 사용자가 원전 예시를 다시 주었고, 그걸로 «규칙이 확정»됐다 (2026-08-30)
```
1거래 ¼   → 성공 → 확대
2거래 ½   → 성공 → 확대
3거래 전체 → **실패** → 축소
4거래 ½   → **실패** → 또 축소
```
> ### **「한 번 이기면 한 칸 위 · «한 번만 져도» 한 칸 아래」**
> ### **99 에서 「우리 구성」이라 라벨 달았던 「한 칸 내림」이 «원전 것»으로 확정됐다.**
> ### **그리고 114 의 「3연패→½」는 «내가 만든 것»이고, 원전은 «훨씬 더 빨리» 줄인다.**

## 손절 방식도 확정됐다 (Momentum Masters · 사용자 전사)
> 「주가가 스톱 가격을 만나면 **전체 포지션을 즉시 매도**한다. 때때로 **평균 손실률이 스톱 한 개만
>  설정할 때와 «일치»하도록** 스톱을 여러 단계로 쌓아 놓기도 한다.」
→ **기본은 전량 손절이고 우리 하네스가 그것이다** ✅ · 스톱 쌓기는 «기대값이 같다»(분산만 준다)

# 왜 다시 재나
99 는 이 사다리를 **«수익»의 자**로 재고 미통과라 했다. **«낙폭»은 안 쟀다.**
114 에서 낙폭이 −45.2% → **−22.0%** 로 «절반 이하»가 되는 걸 봤지만
**115 처럼 «짝비교 이긴 판»과 «동전 격자»로는 안 쟀다.**

# 팔 — 원전 한 칸 + 흔들기 둘
```
㉠ 원전    ¼·½·전체 · 이기면 +1칸 · **지면 −1칸**    ← 사용자 예시 «그대로»
㉡ 흔들기   지면 −1칸이되 **두 번 져야** 내린다
㉢ 흔들기   지면 −1칸이되 **최저 칸이 ½**(¼ 까지 안 내림)
동전       팔마다 «그 팔의» 크기 분포를 무작위 배정
```

# 합격선 — 값 보기 «전» (115 와 «같은» 자)
| | 문턱 |
|---|---|
| **X**★ | 네 구간 «모두» 낙폭이 «그 칸의» 동전보다 작은 판 > 55% |
| **Y**★ | 네 구간 «모두» 수익도 동전보다 큰 판 > 55% |
| **Z**★ | ㉠ 의 낙폭 이득이 **동전 격자 3칸의 «최대»**를 넘는가  🚨 **주지표** |
| **W** | 세 칸을 «전부» 적고 투입율·수익을 같이 찍는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ 낙폭은 «크게» 줄 것이다 — 114 에서 −22.0% 를 봤다. 거의 확실하다
㉯ 수익도 «크게» 줄 것이다 — 114 에서 +4.82%(바탕 +9.37%). 반토막이다
㉰ 🚨 **그래서 Y★ 는 못 넘을 것으로 본다.** 115 의 ㉰ 도 상승장에서 졌다
㉱ 🚨 **투입율이 32% 안팎이라 「그냥 덜 든 것」의 몫이 클 것이다** — 동전 짝이 그걸 가른다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim_lots as sl                                        # noqa: E402
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
r41 = r91.r41

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
A_PASS = 55.0
MULT = (0.25, 0.50, 1.00)


def f_source(recent, seed, t):
    """★ 원전 — 이기면 +1칸 · **지면 −1칸**. 사용자 예시 그대로."""
    k = 0
    for w in recent:
        k = min(2, k + 1) if w else max(0, k - 1)
    return MULT[k]


def f_slow(recent, seed, t):
    """흔들기 — 이기면 +1칸 · **두 번 져야** −1칸."""
    k, l = 0, 0
    for w in recent:
        if w:
            k, l = min(2, k + 1), 0
        else:
            l += 1
            if l >= 2:
                k, l = max(0, k - 1), 0
    return MULT[k]


def f_floor(recent, seed, t):
    """흔들기 — 원전과 같되 **최저 칸이 ½**."""
    k = 0
    for w in recent:
        k = min(2, k + 1) if w else max(1, k - 1)
    return MULT[k]


def make_fake(props, tag):
    def fn(recent, seed, t):
        r = random.Random((tag * 1000003) ^ (seed * 7919) ^ (id(t) & 0xFFFF))
        u, acc = r.random(), 0.0
        for m, p in props:
            acc += p
            if u <= acc:
                return m
        return props[-1][0]
    return fn


def run(ev, fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            size_fn=fn, recent_n=20) for s in range(n_seed)]


def props_of(ev, fn, n_seed):
    cnt = {}

    def spy(recent, seed, t):
        m = fn(recent, seed, t)
        cnt[m] = cnt.get(m, 0) + 1
        return m
    run(ev, spy, min(8, n_seed))
    tot = sum(cnt.values()) or 1
    return sorted(((m, c / tot) for m, c in cnt.items()), key=lambda x: x[0])


ARMS = (("★ 원전 (지면 −1칸)", f_source),
        ("  두 번 져야 −1칸", f_slow),
        ("  최저 칸이 ½", f_floor))


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 100
    print("=" * 112, flush=True)
    print("116 — **원전 사다리를 «낙폭»의 자로** · 사전등록 · 100판", flush=True)
    print("=" * 112, flush=True)
    print("🚨 사용자 원전 예시로 규칙 확정: **「한 번 이기면 +1칸 · «한 번만 져도» −1칸」**",
          flush=True)
    print("   114 의 「3연패→½」는 «내가 만든 것»이고 원전은 «훨씬 더 빨리» 줄인다\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    ev_all, _x, _y = r91.replay(by2)

    base = {}
    for lab, a0, b0, yrs in WIN:
        ev = [t for t in ev_all if a0 <= t["entry_date"] <= b0]
        rs = run(ev, None, n_seed)
        base[lab] = {"cagr": ((1 + st.median(x["equity_pct"] for x in rs) / 100.0)
                              ** (1 / yrs) - 1) * 100,
                     "mdd": st.median(x["mdd_pct"] for x in rs)}
    print("  바탕 — %s\n"
          % (" · ".join("%s %+.2f%% (낙폭 %.1f%%)" % (l, base[l]["cagr"], base[l]["mdd"])
                        for l, _a, _b, _y in WIN)), flush=True)

    res = {}
    print("  %-20s %s" % ("칸", "구간별 [연평균 · 낙폭 · 낙폭이긴판 · 수익이긴판 · 투입율]"),
          flush=True)
    print("  " + "-" * 104, flush=True)
    for gi, (nm, fn) in enumerate(ARMS):
        cells, rec = [], {}
        for lab, a0, b0, yrs in WIN:
            ev = [t for t in ev_all if a0 <= t["entry_date"] <= b0]
            rt = run(ev, fn, n_seed)
            fk = run(ev, make_fake(props_of(ev, fn, n_seed), gi + 1), n_seed)
            dm = [x["mdd_pct"] - y["mdd_pct"] for x, y in zip(rt, fk)]
            de = [x["equity_pct"] - y["equity_pct"] for x, y in zip(rt, fk)]
            wm = 100.0 * sum(1 for v in dm if v > 0) / n_seed
            we = 100.0 * sum(1 for v in de if v > 0) / n_seed
            cg = ((1 + st.median(x["equity_pct"] for x in rt) / 100.0) ** (1 / yrs) - 1) * 100
            md = st.median(x["mdd_pct"] for x in rt)
            ex = st.median(x["expo_mean"] for x in rt)
            rec[lab] = {"cagr": cg, "mdd": md, "win_mdd": wm, "win_eq": we,
                        "expo": ex, "gain": st.median(dm)}
            cells.append("%s %+6.2f%% %5.1f%% %5.1f%%%s %5.1f%%%s %3.0f%%"
                         % (lab, cg, md, wm, "✅" if wm > A_PASS else "❌",
                            we, "✅" if we > A_PASS else "❌", ex))
        res[nm] = rec
        print("  %-20s %s" % (nm, "  ".join(cells)), flush=True)

    print("\n" + "=" * 112, flush=True)
    X = [k for k, v in res.items() if all(v[l]["win_mdd"] > A_PASS for l in v)]
    Y = [k for k, v in res.items() if all(v[l]["win_eq"] > A_PASS for l in v)]
    print("  **X★** 네 구간 «모두» 낙폭이 동전보다 나은가  →  %s"
          % (", ".join(X) if X else "**없음 — 미통과**"), flush=True)
    print("  **Y★** 네 구간 «모두» 수익도 동전보다 나은가  →  %s"
          % (", ".join(Y) if Y else "**없음 — 미통과**"), flush=True)

    ev = [t for t in ev_all if WIN[0][1] <= t["entry_date"] <= WIN[0][2]]
    fmax = -99.0
    for gi, (nm, fn) in enumerate(ARMS):
        pr = props_of(ev, fn, n_seed)
        a = run(ev, make_fake(pr, 900 + gi), n_seed)
        b = run(ev, make_fake(pr, 500 + gi), n_seed)
        fmax = max(fmax, st.median(x["mdd_pct"] - y["mdd_pct"] for x, y in zip(a, b)))
    g0 = res[ARMS[0][0]]["전체"]["gain"]
    print("\n  **Z★** 동전 «끼리» 3칸의 최대 = **%+.2f%%p**  ·  원전 = **%+.2f%%p**  →  **%s**"
          % (fmax, g0, "넘는다 — 통과" if g0 > fmax else "못 넘는다 — 미통과"), flush=True)

    ok = (ARMS[0][0] in X) and (ARMS[0][0] in Y) and g0 > fmax
    print("\n  → **원전 사다리가 «낙폭의 자»로 확인됐는가: %s**"
          % ("예" if ok else "**아니오**"), flush=True)
    (r91.OUT / "116-source-ladder.json").write_text(
        json.dumps({"res": res, "base": base, "fmax": fmax, "X": X, "Y": Y},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 116-source-ladder.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
