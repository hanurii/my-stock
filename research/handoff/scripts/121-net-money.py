# -*- coding: utf-8 -*-
"""121 — **「돈이 되나」: 세금·수수료를 넣고도 지수를 이기는가** (사전등록 · 값 보기 «전»)

사용자(2026-08-30): 「지수를 이기거나 «돈이 된다»를 검증하진 못했군요. 이게 좀 많이 아쉽네요.」
★ **「지수를 이기나」는 전체 27.4년에서 확인됐다**(119: +11.18% vs SPY +8.60%).
   **「돈이 되나」는 «못 잰» 게 아니라 «안 잰» 것이다.** 111 이 방법을 만들어 뒀다.

# 무엇을 넣는가
```
세금    한국 «해외주식 양도소득세» **22%** · 해마다 **250만원 공제** · 이월결손금 «없음»
수수료   왕복 **0.2%** (미국 주식 온라인 기준 · 🚨 우리가 정한 값)
슬리피지  🚨 **안 넣는다** — 이미 91 규약이 「목표·손절 «가격»이 아니라 그날 종가로 결착」이라
        보수적인 쪽이다. 중복으로 물리면 이중 부과다
시작금    1,000만원
```

# 견주는 다섯
```
① 우리 규칙 (①+③)          — 119 의 그 판
② 바탕 (91 정본)
③ SPY 그냥 보유
④ QQQ 그냥 보유
⑤ SPY + 200일선
```
🚨 **다섯 «모두»에 같은 자로 세금·수수료를 물린다.**

# 근사 (111 과 같음 · 그대로 적는다)
```
우리 규칙·바탕   보유 중앙 34일이라 **「그 해 계좌 증가분 = 그 해 실현이익」**으로 본다
                → 연말 열린 자리만큼 «조금 더» 매기는 = **우리에게 «불리한» 근사**
지수 판          «정확»하다 — 판 시점의 실현손익을 그대로 센다
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **P**★ | 세금·수수료 «후» 우리 규칙이 **SPY 그냥 보유**를 이긴다 (전체 27.4년) |
| **Q**★ | 세금·수수료 «후» 우리 규칙이 **QQQ 그냥 보유**도 이긴다 |
| **R** | 다섯 전부의 «전·후»와 깎인 비율을 적는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **우리 규칙이 «가장 많이» 깎일 것이다** — 111 에서 미너비니가 −27.5% 로 지수 판(−18~20%)보다
   훨씬 아팠다. 우리 규칙은 매수 6,260 이라 바탕(9,172)보다는 덜 팔지만 여전히 많다
㉯ **P★ 는 «간당간당»할 것으로 본다** — 세전 +11.18 vs +8.60 은 여유 +2.58%p 인데
   깎이는 차이가 그만큼 될 수 있다
㉰ 🚨 **Q★ 는 못 넘을 것으로 본다** — QQQ 는 세전 +10.63%(27.4년)이고 «거의 안 판다»
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_t)
_t.loader.exec_module(r102)
_v = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_v)
_v.loader.exec_module(r103)
_w = _u.spec_from_file_location("r108", HERE / "108-short-index.py")
r108 = _u.module_from_spec(_w)
_w.loader.exec_module(r108)
_y = _u.spec_from_file_location("r109", HERE / "109-index-stop.py")
r109 = _u.module_from_spec(_y)
_y.loader.exec_module(r109)
_z = _u.spec_from_file_location("r111", HERE / "111-tax.py")
r111 = _u.module_from_spec(_z)
_z.loader.exec_module(r111)
_q = _u.spec_from_file_location("r118", HERE / "118-matched-placebo.py")
r118 = _u.module_from_spec(_q)
_q.loader.exec_module(r118)
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
YRS = 27.4
START = 1000.0
FEE = 0.002          # 🚨 왕복 0.2% — 우리가 정한 값
SHORT_SIZE, BORROW = 0.20, 2.0


def overlay_curve(curve, settle_pct, spy_ret, omap, size, borrow, n_fill):
    """★ 숏을 얹고 수수료를 뺀 **날마다의 곡선**을 낸다.

    🚨 앞 판은 숏 수익을 «세금 밖»에 두는 지저분한 셈이었다. 여기서 곡선을 먼저 만들고
       그 «위»에 해마다 세금을 물린다 → **숏 수익도 같이 과세된다**(그게 맞다).
    수수료: 매수 1회당 왕복 FEE × 포지션 비중(20%) 를 «날마다 고르게» 뺀다.
    """
    vals = [(d, v) for d, v in curve] + [(curve[-1][0], 1.0 + settle_pct / 100.0)]
    n = len(vals)
    fee_daily = (FEE * 0.20 * n_fill) / max(1, n - 1)     # 전체 수수료를 날짜로 나눔
    bo = borrow / 100.0 / 252.0 * size
    out, v = [], 1.0
    out.append((vals[0][0], v))
    for i in range(1, n):
        if vals[i - 1][1] <= 0:
            break
        rl = vals[i][1] / vals[i - 1][1] - 1.0
        d = vals[i][0]
        rs = 0.0
        if omap and omap.get(d) and d in spy_ret:
            rs = -size * spy_ret[d] - bo
        v *= (1.0 + rl + rs - fee_daily)
        if v <= 0:
            v = 1e-9
            break
        out.append((d, v))
    return out


def tax_yearly(cv):
    """해마다 «계좌 증가분 = 실현이익»으로 보고 세금을 뗀다 (111 과 같은 근사)."""
    byy = {}
    for d, v in cv:
        byy[d[:4]] = v
    acct, prev = START, 1.0
    peak, mdd = START, 0.0
    for y in sorted(byy):
        r = byy[y] / prev
        prev = byy[y]
        before = acct
        acct *= r
        peak = max(peak, acct)
        mdd = min(mdd, acct / peak - 1.0)
        g = acct - before
        if g > 0:
            acct -= r111.tax_on(g)
    return acct, mdd * 100



def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 60
    print("=" * 100, flush=True)
    print("121 — **「돈이 되나」: 세금 22%%·공제 250만원 + 수수료 왕복 0.2%%**", flush=True)
    print("=" * 100, flush=True)
    print("🚨 방향 먼저: **우리 규칙이 가장 많이 깎일 것** · P★ 간당간당 · **Q★ 못 넘을 것**\n",
          flush=True)

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

    rows = []
    for nm, by, omap, sz in (("① 우리 규칙 (①+③)", by_f, on, SHORT_SIZE),
                             ("② 바탕 (91 정본)", by2, {}, 0.0)):
        n_fill, ev = r118.fills_of(by)
        rs = r91.sim(ev, n_seed)
        pre, post = [], []
        for x in rs:
            cv0 = overlay_curve(x["curve"], x["equity_pct"], spy_ret, omap, sz,
                                BORROW if sz else 0.0, 0)          # 수수료 «없이» = 세전
            cv1 = overlay_curve(x["curve"], x["equity_pct"], spy_ret, omap, sz,
                                BORROW if sz else 0.0, n_fill)     # 수수료 «있이»
            pre.append(cv0[-1][1] * START)
            post.append(tax_yearly(cv1)[0])
        rows.append((nm, st.median(pre), st.median(post), n_fill))

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")
    for nm, ds_, c_, mode in (("③ SPY 그냥 보유", dsS, cS, "hold"),
                              ("④ QQQ 그냥 보유", dsQ, cQ, "hold"),
                              ("⑤ SPY + 200일선", dsS, cS, "ma")):
        r0 = r109.run(ds_, c_, mode, cash_rate=2.0)
        a, _md = r111.index_after_tax(ds_, c_, mode)
        n_sell = r0["n_sell"] + 1
        rows.append((nm, r0["final"] * START, a * ((1.0 - FEE) ** n_sell), n_sell))

    print("  %-22s %12s %13s %10s %10s %8s"
          % ("", "세금·수수료 전", "**후**", "깎인 비율", "연평균(후)", "매도수"), flush=True)
    print("  " + "-" * 84, flush=True)
    for nm, a0, a1, nf in rows:
        cg = ((a1 / START) ** (1 / YRS) - 1) * 100
        print("  %-22s %9.0f만 %12.0f만 %9.1f%% %+9.2f%% %8s"
              % (nm, a0, a1, 100.0 * (a1 - a0) / a0, cg, "{:,}".format(nf)), flush=True)

    ours, spy, qqq = rows[0][2], rows[2][2], rows[3][2]
    print("\n" + "=" * 100, flush=True)
    print("  **P★** 세금·수수료 후 우리 규칙 > SPY 그냥 보유 → **%s**  (%.0f만 vs %.0f만)"
          % ("통과" if ours > spy else "미통과", ours, spy), flush=True)
    print("  **Q★** 세금·수수료 후 우리 규칙 > QQQ 그냥 보유 → **%s**  (%.0f만 vs %.0f만)"
          % ("통과" if ours > qqq else "미통과", ours, qqq), flush=True)
    print("\n  → **「돈이 되는가」: %s**"
          % ("SPY 기준 예" if ours > spy else "**아니오**"), flush=True)
    print("\n🚨 근사: 우리 규칙은 「그 해 계좌 증가분 = 실현이익」(보유 34일) — **우리에게 불리한 근사**",
          flush=True)
    print("🚨 수수료 왕복 0.2%%는 «우리가 정한» 값이다. 슬리피지는 «안» 넣었다(91 규약이 이미 보수적)",
          flush=True)
    (r91.OUT / "121-net-money.json").write_text(
        json.dumps([{"name": n, "pre": a0, "post": a1, "n": nf} for n, a0, a1, nf in rows],
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 121-net-money.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
