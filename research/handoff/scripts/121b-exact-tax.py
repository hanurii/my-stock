# -*- coding: utf-8 -*-
"""121b — **세금을 «근사»가 아니라 «실제 매도 시점»으로 다시 센다** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「세금 비용에서 우리 규칙이 정말 많이 깎였는데요 (**−49.1%**).
>  **어떤 식으로 계산한지 세부 로직 한번 보여줄래요?**」

★ 설명하다가 **근사의 결함**을 찾았다.

```
121 이 쓴 근사   「그 해 계좌 «증가분» = 그 해 실현이익」
🚨 결함          연말에 **«아직 안 판»** 자리의 평가이익에도 세금을 매긴다
                → 세금을 «먼저» 내는 셈이고, 그 자리가 나중에 «손실»로 끝나면 **진짜 과잉**이다
                투입율 72% 라 연말에 보통 3~4 자리가 열려 있다
```

# 이 판이 고치는 것 — **세금 계산만 고친다. 나머지는 121 과 «완전히» 같다**
```
시뮬레이터에 **exit_log** 를 새로 달았다 — (청산일, 계좌 기준 실현손익)
관문 이미 통과: 실현손익 «합» = equity_pct 소수점까지 일치 (3.0304 = 3.0304)

이제 그 해 실현손익 = Σ(그 해 «판» 자리의 손익) + 그 해 숏 손익 − 그 해 수수료
세금은 그 «실현»분에만 매긴다. 안 판 자리의 평가이익은 건드리지 않는다
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **S**★ | 🚨 관문 — 정확판의 「해마다 실현손익 합」이 무세 총수익과 일치 (1% 안) |
| **T**★ | 정확판 세금이 근사판보다 **적다** (방향이 맞는지) |
| **U** | P★(SPY 이김)·Q★(QQQ 이김)이 «바뀌는가» |

# ★ 방향을 «먼저» 적는다
```
㉮ **정확판이 덜 깎일 것이다** — 근사가 «우리에게 불리한» 쪽이었으니 당연하다
㉯ 🚨 **크기는 «작을» 것으로 본다** — 보유 중앙 34일이라 연말에 걸리는 자리가
   전체의 일부이고, 게다가 그 자리는 «이듬해»에 과세되니 «미루기»일 뿐 «면제»가 아니다
   → **되돌아오는 건 «세금 자체»가 아니라 «먼저 낸 만큼의 복리»다**
㉰ 그래서 **P★·Q★ 판정은 안 바뀔 것으로 본다**(Q★ 는 격차가 4,000만원대라 크다)
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
r109 = _load("r109", "109-index-stop.py")
r111 = _load("r111", "111-tax.py")
r118 = _load("r118", "118-matched-placebo.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
YRS = 27.4
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0


def build(curve, settle, spy_ret, omap, size, borrow, fill_dates):
    """세전 «날마다» 곡선 + 그 해 «롱 밖» 손익(숏·수수료) + 롱곡선 대비 배율."""
    vals = [(d, v) for d, v in curve] + [(curve[-1][0], 1.0 + settle / 100.0)]
    bo = borrow / 100.0 / 252.0 * size
    fd = Counter(fill_dates)
    V, lv = 1.0, 1.0
    out = [(vals[0][0], 1.0)]
    other, lsc = {}, {}
    for i in range(1, len(vals)):
        if vals[i - 1][1] <= 0:
            break
        rl = vals[i][1] / vals[i - 1][1] - 1.0
        d = vals[i][0]
        rs = (-size * spy_ret[d] - bo) if (omap and omap.get(d) and d in spy_ret) else 0.0
        fe = FEE * 0.20 * fd.get(d, 0)
        other[d[:4]] = other.get(d[:4], 0.0) + (rs - fe) * V     # 계좌 단위 손익
        V *= (1.0 + rl + rs - fe)
        lv *= (1.0 + rl)
        if V <= 0:
            V = 1e-9
            break
        out.append((d, V))
        lsc[d] = (V / lv) if lv > 0 else 1.0
    return out, other, lsc


def tax_approx(cv):
    """121 이 쓴 근사 — 「그 해 계좌 증가분 = 실현이익」."""
    byy = {}
    for d, v in cv:
        byy[d[:4]] = v
    acct, prev = START, 1.0
    for y in sorted(byy):
        r = byy[y] / prev
        prev = byy[y]
        before = acct
        acct *= r
        g = acct - before
        if g > 0:
            acct -= r111.tax_on(g)
    return acct


def tax_exact(cv, other, lsc, exit_log):
    """★ «실제로 판» 자리의 손익만 그 해 과세한다."""
    ly = {}
    for d, pl in exit_log:
        ly[d[:4]] = ly.get(d[:4], 0.0) + pl * lsc.get(d, 1.0)
    byy = {}
    for d, v in cv:
        byy[d[:4]] = v
    acct, prev, scale = START, 1.0, 1.0
    tot_tax, real_sum = 0.0, 0.0
    for y in sorted(byy):
        r = byy[y] / prev
        prev = byy[y]
        acct *= r
        g = (ly.get(y, 0.0) + other.get(y, 0.0)) * START * scale
        real_sum += (ly.get(y, 0.0) + other.get(y, 0.0))
        if g > 0:
            t = r111.tax_on(g)
            acct -= t
            tot_tax += t
        scale = acct / (START * byy[y]) if byy[y] > 0 else scale
    return acct, tot_tax, real_sum


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 60
    print("=" * 104, flush=True)
    print("121b — **세금을 «실제 매도 시점»으로 다시 센다** · 사전등록", flush=True)
    print("=" * 104, flush=True)
    print("🚨 근사의 결함: **연말에 «안 판» 자리의 평가이익에도 세금을 매겼다**", flush=True)
    print("🚨 방향 먼저: 덜 깎이나 **크기는 «작을» 것** — 미루기지 면제가 아니다\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
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

    rows, gate = [], []
    for nm, by, omap, sz in (("① 우리 규칙 (①+③)", by_f, on, SHORT_SIZE),
                             ("② 바탕 (91 정본)", by2, {}, 0.0)):
        _n, ev = r118.fills_of(by)
        rs = r91.sim(ev, n_seed)
        pre, ap, ex, tx = [], [], [], []
        for x in rs:
            fdates = [f[0] for f in x.get("fill_log", [])]
            cv0, _o0, _l0 = build(x["curve"], x["equity_pct"], spy_ret, omap, sz,
                                  BORROW if sz else 0.0, [])
            cv1, oth, lsc = build(x["curve"], x["equity_pct"], spy_ret, omap, sz,
                                  BORROW if sz else 0.0, fdates)
            pre.append(cv0[-1][1] * START)
            ap.append(tax_approx(cv1))
            a2, t2, rsum = tax_exact(cv1, oth, lsc, x["exit_log"])
            ex.append(a2)
            tx.append(t2)
            gate.append(abs(rsum - (cv1[-1][1] - 1.0)) / max(1e-9, abs(cv1[-1][1] - 1.0)))
        rows.append((nm, st.median(pre), st.median(ap), st.median(ex), st.median(tx)))

    g = max(gate)
    print("**S★ 관문** — 「해마다 실현손익 합」 vs 무세 총수익 · 최대 어긋남 **%.3f%%** · **%s**\n"
          % (g * 100, "통과" if g < 0.01 else "🚨 미통과"), flush=True)

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")
    for nm, ds_, c_, mode in (("③ SPY 그냥 보유", dsS, cS, "hold"),
                              ("④ QQQ 그냥 보유", dsQ, cQ, "hold"),
                              ("⑤ SPY + 200일선", dsS, cS, "ma")):
        r0 = r109.run(ds_, c_, mode, cash_rate=2.0)
        a, _md = r111.index_after_tax(ds_, c_, mode)
        ns = r0["n_sell"] + 1
        v = a * ((1.0 - FEE) ** ns)
        rows.append((nm, r0["final"] * START, v, v, 0.0))

    print("  %-22s %11s %12s %12s %9s %10s"
          % ("", "세전", "근사(121)", "**정확**", "차이", "연평균(정확)"), flush=True)
    print("  " + "-" * 84, flush=True)
    for nm, a0, a1, a2, _t in rows:
        cg = ((a2 / START) ** (1 / YRS) - 1) * 100
        print("  %-22s %8.0f만 %9.0f만 %9.0f만 %+7.0f만 %+9.2f%%"
              % (nm, a0, a1, a2, a2 - a1, cg), flush=True)

    ours, spy, qqq = rows[0][3], rows[2][3], rows[3][3]
    ap0 = rows[0][2]
    T = ours > ap0
    print("\n" + "=" * 104, flush=True)
    print("  **T★** 정확판이 근사판보다 «덜 깎였는가» → **%s** (%.0f만 → %.0f만, %+.1f%%p)"
          % ("통과" if T else "미통과", ap0, ours, 100.0 * (ours - ap0) / rows[0][1]), flush=True)
    print("  **P★** 정확 세후 우리 규칙 > SPY → **%s** (%.0f만 vs %.0f만)"
          % ("통과" if ours > spy else "미통과", ours, spy), flush=True)
    print("  **Q★** 정확 세후 우리 규칙 > QQQ → **%s** (%.0f만 vs %.0f만)"
          % ("통과" if ours > qqq else "미통과", ours, qqq), flush=True)
    print("\n  깎인 비율 — 근사 %.1f%%  →  **정확 %.1f%%**"
          % (100.0 * (ap0 - rows[0][1]) / rows[0][1],
             100.0 * (ours - rows[0][1]) / rows[0][1]), flush=True)
    (r91.OUT / "121b-exact-tax.json").write_text(
        json.dumps([{"name": n, "pre": a0, "approx": a1, "exact": a2, "tax": t}
                    for n, a0, a1, a2, t in rows],
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 121b-exact-tax.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
