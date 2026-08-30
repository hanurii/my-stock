# -*- coding: utf-8 -*-
"""128 — **「나쁠 때 얼마나 잃나」를 «여러 판»으로 다시 잰다** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「손절선 범위를 넓힌 만큼 손실률이 올라가는 건 어쩔 수 없다고 생각합니다.
>  **bad case 일 때 손실을 최대한 막으면서 수익률은 최대한 끌어올리는 그런 모델을 만드는 게**
>  **우리의 추구 방향입니다.** 여러 판으로 다시 재서 근거를 찾아주시면 그때 또 이야기하죠.」

# 127 이 남긴 문제 — **「최악」이 «한 경로»의 값이었다**
```
127 은 성적이 «중앙»인 판 하나를 골라 그 경로에서 최악을 읽었다.
운의 번호가 하나 바뀌면 «최악»은 흔들린다. → 「−201만」을 근거로 못 쓴다
```

# 이 판이 하는 것 — **판 × 시작일을 «모두 모아» 아래꼬리를 낸다**
```
손절 세 자   −8 · −10 · −12.5      (목표는 +20 고정)
판          운의 번호 20판
시작일       10거래일마다
보유         2 · 3 · 4 · 5년
→ 창 개수 = 20판 × 약 600 시작일 = **판마다 «한 경로»가 아니라 «만 이천 창»**

내는 값     **최악 · 하위1% · 하위5% · 하위10% · 중앙 · 원금손실률**
           + **창 «안»의 최대 낙폭** (지나온 최고점 대비)
🚨 세후다 (창 안 해마다 + 창 끝에 남은 미실현까지 판다 · 124 와 같은 자)
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AL**★ | 🚨 관문 — 수수료 횟수 = 매수 수 · Σ(자리 손익) = 총수익 (0.5% 안) |
| **AN**★ | 3년·4년의 **하위 5%** 에서 −8 이 −10 보다 «낫다» (127 의 한 경로 관찰이 여러 판에서도 사는가) |
| **AO** | 창 «안» 최대 낙폭을 세 자 나란히 |
| **AP** | 「나쁠 때」와 「보통」을 **같은 줄**에 적는다 — 사용자님이 세운 목표가 그 둘의 «동시» 최적화이므로 |

# ★ 방향을 «먼저» 적는다
```
㉮ 🚨 **−8 의 아래꼬리가 나을 것이다** — 기전이 명확하다(넓은 손절 = 한 번에 더 잃음)
㉯ **중앙은 −10 이 나을 것이다** — 126·127 에서 그랬다
㉰ 🚨 **한 경로에서 본 「−201만」 같은 «크기»는 «줄어들» 것이다** —
   한 경로의 극단은 과장되기 쉽다. **여러 판을 모으면 아래꼬리가 «메워진다»**
→ 이 판이 답하는 것은 「어느 손절이 옳나」가 아니라
  **「나쁠 때의 손실과 보통 때의 수익을 «어떻게 맞바꾸나»」**다
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
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
STOPS = (8.0, 10.0, 12.5)
HOR = (2, 3, 4, 5)
STEP = 10
N_SEED = 20


def window(ds, cv, real, i0, i1):
    """창 [i0,i1] 의 **세후 잔액**과 **창 «안» 최대 낙폭**을 같이 낸다."""
    gross, net = START, START
    taxed_pre, ybuf = 0.0, 0.0
    peak, worst = 1.0, 0.0
    base = cv[i0]
    for k in range(i0 + 1, i1 + 1):
        ratio = cv[k] / cv[k - 1]
        gross *= ratio
        net *= ratio
        rel = cv[k] / base
        peak = max(peak, rel)
        worst = min(worst, rel / peak - 1.0)
        if real:
            ybuf += real.get(ds[k], 0.0) / cv[k] * gross
        last = (k == i1)
        if last or ds[k + 1][:4] != ds[k][:4]:
            if last:
                ybuf += (gross - START) - taxed_pre - ybuf
            g_net = ybuf * (net / gross) if gross > 0 else 0.0
            if g_net > 0:
                net -= r111.tax_on(g_net)
            taxed_pre += ybuf
            ybuf = 0.0
    return net, worst * 100


def q(v, f):
    return v[min(len(v) - 1, int(len(v) * f))]


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed, step = (4, 40) if quick else (N_SEED, STEP)
    print("=" * 104, flush=True)
    print("128 — **「나쁠 때 얼마나 잃나」를 «여러 판»으로** · 사전등록 · 판 %d · %d거래일마다"
          % (n_seed, step), flush=True)
    print("=" * 104, flush=True)
    print("사용자 목표: **「bad case 일 때 손실을 최대한 막으면서 수익률은 최대한 끌어올린다」**",
          flush=True)
    print("🚨 127 의 「최악」은 «한 경로» 값이었다. 여기서는 **판 × 시작일을 모두 모은다**", flush=True)
    print("🚨 방향 먼저: −8 의 아래꼬리가 나을 것 · 중앙은 −10 · **한 경로의 극단은 «줄어들» 것**\n",
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
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    res = {}
    for stop in STOPS:
        r91.STOP, r91.TARGET = stop, 20.0
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        pooled = {h: [] for h in HOR}
        dds = {h: [] for h in HOR}
        cags = []
        for x in rs:
            fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
            if len(fdates) != int(x["n_filled"]):
                print("🚨 AL★ 미통과 — 수수료 횟수 %d ≠ 매수 %d"
                      % (len(fdates), int(x["n_filled"])), flush=True)
                return 3
            g = abs(sum(r_ * t / 100.0 for _d, r_, t in x["ret_log"])
                    - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
            if g >= 0.005:
                print("🚨 AL★ 미통과 — 손익 합 어긋남 %.3f%%" % (g * 100), flush=True)
                return 4
            fd = Counter(fdates)
            vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                       1.0 + x["equity_pct"] / 100.0)]
            cds, ccv, V = [vals[0][0]], [1.0], 1.0
            for i in range(1, len(vals)):
                if vals[i - 1][1] <= 0:
                    break
                d = vals[i][0]
                rl = vals[i][1] / vals[i - 1][1] - 1.0
                sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
                V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
                cds.append(d)
                ccv.append(max(V, 1e-9))
            real = {}
            for d, pl in x["exit_log"]:
                real[d] = real.get(d, 0.0) + pl
            cags.append(ccv[-1])
            for h in HOR:
                sp = int(round(h * 252))
                for i0 in range(0, len(cds) - sp, step):
                    if ccv[i0] <= 0:
                        continue
                    a, m = window(cds, ccv, real, i0, i0 + sp)
                    pooled[h].append(a)
                    dds[h].append(m)
        res[stop] = {"pool": {h: sorted(pooled[h]) for h in HOR},
                     "dd": {h: sorted(dds[h]) for h in HOR},
                     "pre": st.median(cags) * START}
        print("**AL★ 관문** [손절 −%.1f%%] 통과 · 창 %s 개 (판 %d × 시작일)"
              % (stop, "{:,}".format(len(pooled[HOR[0]])), n_seed), flush=True)

    print("\n" + "=" * 104, flush=True)
    print("### 1,000만원 · **세후** · 판 %d × 시작일 «모두 모음»" % n_seed, flush=True)
    for h in HOR:
        print("\n  보유 **%d년**   %9s %9s %9s %9s %9s %9s"
              % (h, "**최악**", "하위1%", "**하위5%**", "하위10%", "**중앙**", "원금손실"),
              flush=True)
        for stop in STOPS:
            v = res[stop]["pool"][h]
            print("    손절 −%-5.1f%%  %7.0f만 %8.0f만 %8.0f만 %8.0f만 %8.0f만 %8.1f%%"
                  % (stop, v[0], q(v, 0.01), q(v, 0.05), q(v, 0.10), q(v, 0.50),
                     100.0 * sum(1 for a in v if a < START) / len(v)), flush=True)
        print("      창 «안» 최대 낙폭 —  %s"
              % ("  ".join("−%.1f: 중앙 %.1f%% / 하위5%% %.1f%%"
                           % (s, res[s]["dd"][h][len(res[s]["dd"][h]) // 2],
                              q(res[s]["dd"][h], 0.05)) for s in STOPS)), flush=True)

    print("\n" + "=" * 104, flush=True)
    ok3 = res[8.0]["pool"][3][int(len(res[8.0]["pool"][3]) * 0.05)] > \
        res[10.0]["pool"][3][int(len(res[10.0]["pool"][3]) * 0.05)]
    ok4 = res[8.0]["pool"][4][int(len(res[8.0]["pool"][4]) * 0.05)] > \
        res[10.0]["pool"][4][int(len(res[10.0]["pool"][4]) * 0.05)]
    print("  **AN★** 3년·4년 «하위 5%%» 에서 −8 이 −10 보다 나은가 → **%s** (3년 %s · 4년 %s)"
          % ("통과" if (ok3 and ok4) else "미통과",
             "✅" if ok3 else "❌", "✅" if ok4 else "❌"), flush=True)
    print("\n  **AP** 「나쁠 때」와 「보통」을 같은 줄에 — 27.4년 세전 자산도 함께", flush=True)
    print("    %-12s %12s %12s %14s" % ("", "3년 하위5%", "3년 중앙", "27.4년 세전"), flush=True)
    for stop in STOPS:
        v = res[stop]["pool"][3]
        print("    손절 −%-6.1f%% %9.0f만 %11.0f만 %12.0f만"
              % (stop, q(v, 0.05), q(v, 0.50), res[stop]["pre"]), flush=True)
    (r91.OUT / "128-badcase.json").write_text(
        json.dumps({str(s): {"h%d" % h: {"min": res[s]["pool"][h][0],
                                         "p1": q(res[s]["pool"][h], 0.01),
                                         "p5": q(res[s]["pool"][h], 0.05),
                                         "p10": q(res[s]["pool"][h], 0.10),
                                         "med": q(res[s]["pool"][h], 0.50),
                                         "loss": 100.0 * sum(1 for a in res[s]["pool"][h]
                                                             if a < START)
                                         / len(res[s]["pool"][h]),
                                         "dd_med": res[s]["dd"][h][len(res[s]["dd"][h]) // 2],
                                         "dd_p5": q(res[s]["dd"][h], 0.05),
                                         "n": len(res[s]["pool"][h])}
                             for h in HOR} | {"pre": res[s]["pre"]} for s in STOPS},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 128-badcase.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
