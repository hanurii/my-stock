# -*- coding: utf-8 -*-
"""127 — **기준을 +20/−10 으로 맞추고 핵심 표를 다시 낸다** (사전등록 · 값 보기 «전»)

사용자(2026-08-30): 「그럼 앞으로 우리는 **수익 20% / 손절 −10%** 를 기준으로 놓나요?」

# 어긋나 있던 것 — **버리는 게 아니라 «맞추는» 것이다**
```
사용자님 실전 규칙                 +20 / **−10**   (2026-08-13 부터)
프로젝트 정본 strategy_params.py   +20 / **−10**   (:10-11)
원전이 지목한 값                   +20 / **−10**
🚨 미국 백테스트 하네스만            +20 / **−8**    (91:54)
   ↑ 연구 계보(74→81→91)에서 «비교하려고» 얼려 둔 값이 매매 정본과 갈라져 있었다
```
🚨 **91 파일 자체는 안 고친다** — 74·81·91 의 재현을 깨지 않기 위해서다.
   대신 여기서 `r91.STOP = 10.0` 으로 «꽂아» 쓰고, 앞으로 새 판은 전부 이 자를 쓴다.

# 다시 내는 표 둘 — **바뀌는 건 손절 하나뿐, 나머지는 «완전히» 같다**
```
① 27.4년 «세후» 다섯 팔        (121b 재판)
② 2·3·4·5년 «세후» 시점 운     (124 재판 · 전세 만기)
③ ★ 덤 — **낙폭을 «제대로»** 잰다 (126 의 낙폭 열이 계산 오류였다)
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AI**★ | 🚨 관문 — 수수료 «물린 횟수» = 매수 수 (121b 에서 배운 것) |
| **AJ**★ | 🚨 관문 — Σ(자리 손익) = 총수익 (0.5% 안) |
| **AK** | −8 판과 −10 판을 «나란히» 적는다. 어느 결론이 바뀌는지 그 자리에서 본다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **−10 이 조금 나을 것이다** — 126 에서 전체 연평균 +11.28 → +11.75 (+0.47%p)
㉯ 🚨 **큰 결론은 «안» 바뀔 것이다** — SPY 는 계속 이기고 **QQQ 는 계속 못 이긴다**
   (세후 8,470만 → 9,300만 근처로 봐도 QQQ 12,602만에 한참 못 미친다)
㉰ **2~4년 표의 «최악»은 조금 나아지되 «순서»는 그대로일 것이다**
→ 그래서 이 판은 «새 발견»을 노리는 게 아니라 **「자를 맞추는」** 판이다.
   🚨 **만약 결론이 «바뀌면» 그건 이 판의 소득이 아니라 «경보»다** — 손절 2%p 로 뒤집히는
   결론이었다면 애초에 그 결론이 약했던 것이다
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
r121b = _load("r121b", "121b-exact-tax.py")
r124 = _load("r124", "124-jeonse-horizon.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
YRS = 27.4
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
HOR = (2, 3, 4, 5)
STEP = 5


def mdd(vals):
    """★ «제대로» 된 최대 낙폭 — 지나온 최고점 대비."""
    peak, worst = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100


def main() -> int:
    n_seed = 8 if "--quick" in sys.argv else 40
    print("=" * 104, flush=True)
    print("127 — **기준을 +20/−10 으로 맞추고 핵심 표를 다시 낸다** · 사전등록", flush=True)
    print("=" * 104, flush=True)
    print("🚨 버리는 게 아니라 «맞추는» 것 — 실전·정본·원전 모두 −10, **하네스만 −8** 이었다",
          flush=True)
    print("🚨 방향 먼저: −10 이 조금 나을 것 · **큰 결론은 «안» 바뀔 것** · 바뀌면 그건 «경보»\n",
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

    res = {}
    for stop in (8.0, 10.0):
        r91.STOP, r91.TARGET = stop, 20.0
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        pre, post, wr, md, nfl = [], [], [], [], []
        feeg, sumg = [], []
        for x in rs:
            fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
            feeg.append(abs(len(fdates) - int(x["n_filled"])))
            sumg.append(abs(sum(r_ * t / 100.0 for _d, r_, t in x["ret_log"])
                            - x["equity_pct"] / 100.0)
                        / max(1e-9, abs(x["equity_pct"] / 100.0)))
            cv0, _o, _l = r121b.build(x["curve"], x["equity_pct"], spy_ret, on,
                                      SHORT_SIZE, BORROW, [])
            cv1, oth, lsc = r121b.build(x["curve"], x["equity_pct"], spy_ret, on,
                                        SHORT_SIZE, BORROW, fdates)
            pre.append(cv0[-1][1] * START)
            post.append(r121b.tax_exact(cv1, oth, lsc, x["exit_log"])[0])
            md.append(mdd([v for _d, v in cv1]))
            r_ = [e[1] for e in x["ret_log"]]
            wr.append(100.0 * sum(1 for v in r_ if v > 0) / len(r_))
            nfl.append(len(r_))
        if max(feeg) != 0:
            print("🚨 AI★ 미통과 — 수수료 횟수 어긋남 %d" % max(feeg), flush=True)
            return 3
        if max(sumg) >= 0.005:
            print("🚨 AJ★ 미통과 — 손익 합 어긋남 %.3f%%" % (max(sumg) * 100), flush=True)
            return 4
        res[stop] = {"pre": st.median(pre), "post": st.median(post),
                     "wr": st.median(wr), "mdd": st.median(md), "n": st.median(nfl),
                     "curves": rs}
        print("**AI★·AJ★ 관문** [손절 −%.0f%%] 수수료 0건 · 손익합 %.4f%% · **통과**"
              % (stop, max(sumg) * 100), flush=True)

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")
    bench = {}
    for nm, ds_, c_, mode in (("③ SPY 그냥 보유", dsS, cS, "hold"),
                              ("④ QQQ 그냥 보유", dsQ, cQ, "hold"),
                              ("⑤ SPY + 200일선", dsS, cS, "ma")):
        r0 = r109.run(ds_, c_, mode, cash_rate=2.0)
        a, _m = r111.index_after_tax(ds_, c_, mode)
        ns = r0["n_sell"] + 1
        bench[nm] = (r0["final"] * START, a * ((1.0 - FEE) ** ns))

    print("\n" + "=" * 104, flush=True)
    print("### ① 27.4년 «세후» — 손절 −8 vs −10 나란히", flush=True)
    print("  %-22s %11s %12s %9s %9s %9s"
          % ("", "세전", "**세후**", "승률", "**낙폭**", "매수"), flush=True)
    print("  " + "-" * 78, flush=True)
    for stop in (8.0, 10.0):
        v = res[stop]
        cg = ((v["post"] / START) ** (1 / YRS) - 1) * 100
        print("  우리 규칙 손절 −%-4.0f%%      %8.0f만 %9.0f만 %8.1f%% %+8.1f%% %8.0f   (연 %+.2f%%)"
              % (stop, v["pre"], v["post"], v["wr"], v["mdd"], v["n"], cg), flush=True)
    for nm, (a0, a1) in bench.items():
        print("  %-22s %8.0f만 %9.0f만 %8s %9s %8s" % (nm, a0, a1, "-", "-", "-"), flush=True)

    o10, spy, qqq = res[10.0]["post"], bench["③ SPY 그냥 보유"][1], bench["④ QQQ 그냥 보유"][1]
    print("\n  **P★** 세후 우리(−10) > SPY → **%s** (%.0f만 vs %.0f만)"
          % ("통과" if o10 > spy else "미통과", o10, spy), flush=True)
    print("  **Q★** 세후 우리(−10) > QQQ → **%s** (%.0f만 vs %.0f만)"
          % ("통과" if o10 > qqq else "**미통과**", o10, qqq), flush=True)
    print("  → 손절 −8 → −10 으로 세후 자산 **%.0f만 → %.0f만** (%+.1f%%)"
          % (res[8.0]["post"], o10, 100.0 * (o10 - res[8.0]["post"]) / res[8.0]["post"]),
          flush=True)

    # ── ② 2·3·4·5년 세후 (−10 기준) ────────────────────────────────
    print("\n### ② 2~5년 «세후» 시점 운 — **손절 −10 기준** (1,000만원)", flush=True)
    rs = sorted(res[10.0]["curves"], key=lambda x: x["equity_pct"])
    x = rs[len(rs) // 2]
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE
    vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                               1.0 + x["equity_pct"] / 100.0)]
    our_ds, our_cv, V = [vals[0][0]], [1.0], 1.0
    for i in range(1, len(vals)):
        if vals[i - 1][1] <= 0:
            break
        d = vals[i][0]
        rl = vals[i][1] / vals[i - 1][1] - 1.0
        sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
        V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
        our_ds.append(d)
        our_cv.append(max(V, 1e-9))
    our_real = {}
    for d, pl in x["exit_log"]:
        our_real[d] = our_real.get(d, 0.0) + pl

    ARMS = [("① 우리 규칙 (−10)", our_ds, our_cv, our_real),
            ("② SPY 그냥 보유", dsS, cS, {}),
            ("③ QQQ 그냥 보유", dsQ, cQ, {})]
    hz = {}
    for yrs in HOR:
        step = int(round(yrs * 252))
        print("\n  보유 **%d년**  %10s %10s %10s %10s"
              % (yrs, "**최악**", "하위10%", "중앙", "원금손실"), flush=True)
        for nm, d_, v_, rl_ in ARMS:
            out = [r124.taxed_window(d_, v_, rl_, i0, i0 + step)
                   for i0 in range(0, len(d_) - step, STEP) if v_[i0] > 0]
            if not out:
                continue
            s = r124.stats(out)
            hz.setdefault(nm, {})[yrs] = s
            print("    %-20s %8.0f만 %9.0f만 %9.0f만 %9.1f%%"
                  % (nm, s["min"], s["p10"], s["med"], s["loss"]), flush=True)

    (r91.OUT / "127-restandardize.json").write_text(
        json.dumps({"tax": {str(k): {f: v[f] for f in ("pre", "post", "wr", "mdd", "n")}
                            for k, v in res.items()},
                    "bench": {k: list(v) for k, v in bench.items()},
                    "horizon": hz},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 127-restandardize.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
