# -*- coding: utf-8 -*-
"""124 — **「2~4년 뒤에 빼야 한다」: 전세 만기 기간에서의 «세후» 비교** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「저는 지수 투자를 하더라도 **3~4년 사이에 돈을 쓸 일**이 분명 있을 것 같습니다.
>  **더 빠르면 2년 안으로도** 쓸 계획이 생길 수도 있어요. 그건 제가 **전세집에 살기** 때문이죠.」

★ 지금까지 «모든» 표가 이 조건과 안 맞았다.
```
121·121b   27.4년 한 번에 넣고 한 번에 뺌 · 지수는 «27년간 한 번도 안 판다»
122        3·5·10년 · **세전**
→ 사용자 상황은 **2·3·4년 · 세후**다. 그리고 그 기간에선
   **「27년 안 판다」는 지수의 세금 이점이 «거의 사라진다»** (지수도 그때 팔아 세금을 낸다)
```

# 재는 법
```
시작일을 **5거래일마다** 바꿔 가며 · 보유 **2년 · 3년 · 4년** (참고로 5년도)
넷   ① 우리 규칙(①+③) · ② SPY 그냥 보유 · ③ QQQ 그냥 보유 · ④ SPY+200일선

세금  창 «안»에서 해마다 실현이익에 22%(공제 250만) · **창 끝에 남은 미실현까지 판다**
     → 지수는 «끝에 한 번», 우리 규칙은 «해마다 + 끝에». 둘 다 «그 창 안»에서만 센다
수수료 왕복 0.2% × 자리 20% (121b 와 같은 자)
원금  1,000만원

★ 122 와 다른 점: 「여러 판의 «가운데 값»으로 만든 가짜 경로」가 아니라
  **성적이 «중앙»인 판 «하나»의 진짜 경로**를 쓴다 (합성 경로는 실제로 일어난 적이 없다)
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **Z**★ | 2·3·4년 «전부»에서 우리 규칙의 **최악**이 SPY·QQQ 의 최악보다 낫다 |
| **AA**★ | 2·3·4년 «전부»에서 우리 규칙의 **중앙**이 SPY 를 이긴다 |
| **AB** | 「원금을 잃고 끝난」 시작일 비율을 넷 다 적는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **Z★ 는 넘을 것으로 본다** — 122 에서 3년 최악이 −3.72% vs QQQ −40.16% 였다
㉯ 🚨 **AA★ 는 «못» 넘을 것으로 본다** — 121b 에서 세후 우리 −48.9% vs 지수 −19~20%.
   창이 짧아 지수의 «이연» 이점이 줄지만 **우리는 여전히 해마다 낸다**
㉰ 🚨 **2년은 셋 다 나쁠 것이다** — 2년은 아무 규칙도 못 구하는 길이다
→ **이 판의 값어치는 「누가 이기나」가 아니라 「최악에 얼마를 잃나」다**
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
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
HOR = (2, 3, 4, 5)
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
STEP = 5                      # 시작일을 5거래일마다


def taxed_window(ds, cv, real, i0, i1):
    """창 [i0,i1] 을 1,000만원으로 굴렸을 때의 **세후** 잔액.

    창 «안»에서 해마다 실현이익에 과세하고, **창 끝에 남은 미실현까지 판다**.
    지수 그냥 보유는 real 이 비어 있으므로 «끝에 한 번»만 과세된다(맞는 처리).
    """
    gross, net = START, START
    taxed_pre, ybuf = 0.0, 0.0
    for k in range(i0 + 1, i1 + 1):
        ratio = cv[k] / cv[k - 1]
        gross *= ratio
        net *= ratio
        if real:
            ybuf += real.get(ds[k], 0.0) / cv[k] * gross
        last = (k == i1)
        if last or ds[k + 1][:4] != ds[k][:4]:
            if last:
                ybuf += (gross - START) - taxed_pre - ybuf   # 남은 미실현까지 실현
            g_net = ybuf * (net / gross) if gross > 0 else 0.0
            if g_net > 0:
                net -= r111.tax_on(g_net)
            taxed_pre += ybuf
            ybuf = 0.0
    return net


def stats(vals):
    v = sorted(vals)
    q = lambda f: v[min(len(v) - 1, int(len(v) * f))]         # noqa: E731
    return {"min": v[0], "p10": q(0.10), "med": q(0.50), "p90": q(0.90), "max": v[-1],
            "loss": 100.0 * sum(1 for x in v if x < START) / len(v), "n": len(v)}


def main() -> int:
    n_seed = 8 if "--quick" in sys.argv else 40
    print("=" * 100, flush=True)
    print("124 — **2~4년 뒤에 빼야 한다: 전세 만기 기간 «세후» 비교** · 사전등록", flush=True)
    print("=" * 100, flush=True)
    print("★ 이 기간에선 **「27년 안 판다」는 지수의 세금 이점이 «거의 사라진다»**", flush=True)
    print("🚨 방향 먼저: Z★(최악) 넘을 것 · **AA★(중앙) 못 넘을 것** · 2년은 셋 다 나쁠 것\n",
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

    # ── 우리 규칙 — **성적이 «중앙»인 판 하나**의 진짜 경로 ──────────
    _n, ev = r118.fills_of(by_f)
    rs = r91.sim(ev, n_seed)
    rs.sort(key=lambda x: x["equity_pct"])
    x = rs[len(rs) // 2]
    print("① 우리 규칙 — 운의 번호 %d판 중 **중앙 판** 하나를 쓴다 (총수익 %+.1f%%)"
          % (n_seed, x["equity_pct"]), flush=True)

    vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                               1.0 + x["equity_pct"] / 100.0)]
    from collections import Counter
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    if sum(fd.values()) != int(x["n_filled"]):
        print("🚨 관문 미통과 — 수수료 횟수 %d ≠ 매수 %d"
              % (sum(fd.values()), int(x["n_filled"])), flush=True)
        return 3
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE
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
    # 청산 장부 → 날짜별 실현손익(시뮬 단위)
    our_real = {}
    for d, pl in x["exit_log"]:
        our_real[d] = our_real.get(d, 0.0) + pl

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")

    def ma_arm(ds_, c_, cash_rate=2.0):
        """200일선 판 — 곡선 + **판 날의 실현손익**(시뮬 단위)."""
        n = len(c_)
        mm, run_ = [None] * n, []
        for i in range(n):
            run_.append(c_[i])
            if len(run_) > 200:
                run_.pop(0)
            mm[i] = (sum(run_) / 200.0) if i >= 199 else None
        v, out, inm, basis = 1.0, [1.0], True, 1.0
        real, cd = {}, cash_rate / 100.0 / 252.0
        for i in range(1, n):
            v *= (c_[i] / c_[i - 1]) if inm else (1.0 + cd)
            out.append(v)
            if inm and mm[i] is not None and c_[i] < mm[i]:
                inm = False
                real[ds_[i]] = real.get(ds_[i], 0.0) + (v - basis)
            elif (not inm) and mm[i] is not None and c_[i] > mm[i]:
                inm = True
                basis = v
        return out, real

    ma_cv, ma_real = ma_arm(dsS, cS)
    ARMS = (("① 우리 규칙 (①+③)", our_ds, our_cv, our_real),
            ("② SPY 그냥 보유", dsS, cS, {}),
            ("③ QQQ 그냥 보유", dsQ, cQ, {}),
            ("④ SPY + 200일선", dsS, ma_cv, ma_real))

    out = {}
    for yrs in HOR:
        step = int(round(yrs * 252))
        print("\n### 보유 **%d년** — 1,000만원을 넣고 %d년 뒤 빼면 (**세후**)" % (yrs, yrs),
              flush=True)
        print("  %-20s %10s %10s %10s %10s %9s"
              % ("", "**최악**", "하위10%", "중앙", "최선", "원금손실"), flush=True)
        print("  " + "-" * 76, flush=True)
        for nm, d_, v_, rl_ in ARMS:
            res = []
            for i0 in range(0, len(d_) - step, STEP):
                if v_[i0] <= 0:
                    continue
                res.append(taxed_window(d_, v_, rl_, i0, i0 + step))
            if not res:
                continue
            s = stats(res)
            out.setdefault(nm, {})[yrs] = s
            print("  %-20s %8.0f만 %9.0f만 %9.0f만 %9.0f만 %8.1f%%"
                  % (nm, s["min"], s["p10"], s["med"], s["max"], s["loss"]), flush=True)

    print("\n" + "=" * 100, flush=True)
    A = [nm for nm, _d, _v, _r in ARMS]
    Z = all(out[A[0]][y]["min"] > max(out[A[1]][y]["min"], out[A[2]][y]["min"])
            for y in (2, 3, 4))
    AA = all(out[A[0]][y]["med"] > out[A[1]][y]["med"] for y in (2, 3, 4))
    print("  **Z★**  2·3·4년 «전부» 우리 최악 > SPY·QQQ 최악 → **%s**"
          % ("통과" if Z else "미통과"), flush=True)
    print("  **AA★** 2·3·4년 «전부» 우리 중앙 > SPY 중앙 → **%s**"
          % ("통과" if AA else "미통과"), flush=True)
    print("\n  ★ 읽는 법 — 「누가 이기나」가 아니라 **「최악에 얼마를 잃나」**를 본다", flush=True)
    (r91.OUT / "124-jeonse-horizon.json").write_text(
        json.dumps({"res": out, "Z": Z, "AA": AA, "step": STEP, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 124-jeonse-horizon.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
