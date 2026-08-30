# -*- coding: utf-8 -*-
"""122 — **「아무 때나 시작해서 아무 때나 팔면 얼마인가」** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「27년간 한 번도 안 파는 건 «불가능»합니다. 살다 보면 집을 매매하거나 꼭 필요한 시기에 돈을
>  써야 할 때가 있습니다. **그리고 그 돈을 써야 할 시기가 많이 떨어졌을 시기일 수도 있고요.**」

★ **지적이 정확하다.** 지금까지 모든 표가 「1999-04 에 넣고 2026-08 에 뺀다」를 가정했다.
   **그건 «한 경로»이고, 실제로는 «언제 넣고 언제 빼는지»를 우리가 못 고른다.**

# 재는 법
```
시작일을 **날마다** 바꿔 가며 · 보유 기간 **3년 · 5년 · 10년**
   → 최악 · 하위10% · 중앙 · 최선 을 «전부» 적는다
견주는 넷   ① 우리 규칙(①+③) · ② SPY 그냥 보유 · ③ QQQ 그냥 보유 · ④ SPY+200일선
🚨 세금·수수료는 **안** 넣는다 — 121 이 따로 답했고, 여기 물음은 «시점 운»이다
```

# ★ 방향을 «먼저» 적는다
```
㉮ **최악의 경우가 «크게» 다를 것이다** — QQQ 는 2000년에 들어가면 10년 뒤에도 마이너스다
㉯ 우리 규칙은 낙폭이 얕으니 **최악이 덜 나쁠 것**이다
㉰ 🚨 **중앙값으로는 QQQ 가 이길 것이다** — 121 에서 세후에도 그랬다
→ 그래서 이 판의 값어치는 «중앙»이 아니라 **«꼬리»**에 있다
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
_q = _u.spec_from_file_location("r118", HERE / "118-matched-placebo.py")
r118 = _u.module_from_spec(_q)
_q.loader.exec_module(r118)
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
HOR = (3, 5, 10)
SHORT_SIZE, BORROW = 0.20, 2.0


def windows(ds, vals, yrs):
    """시작일을 날마다 바꿔 가며 yrs 년 뒤 «연평균»을 낸다."""
    n = len(ds)
    step = int(round(yrs * 252))
    out = []
    for i in range(0, n - step):
        a, b = vals[i], vals[i + step]
        if a > 0 and b > 0:
            out.append(((b / a) ** (1.0 / yrs) - 1) * 100)
    return sorted(out)


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 40
    print("=" * 100, flush=True)
    print("122 — **아무 때나 시작해서 아무 때나 팔면** · 사전등록", flush=True)
    print("=" * 100, flush=True)
    print("🚨 지금까지 모든 표가 「1999-04 에 넣고 2026-08 에 뺀다」였다. **그건 «한 경로»다**\n",
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

    # 우리 규칙 — 숏 얹은 «날마다» 곡선을 seed 마다 만들고 «중앙 경로»를 쓴다
    _n, ev = r118.fills_of(by_f)
    rs = r91.sim(ev, n_seed)
    curves = []
    for x in rs:
        vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                   1.0 + x["equity_pct"] / 100.0)]
        v, cur = 1.0, []
        bo = BORROW / 100.0 / 252.0 * SHORT_SIZE
        for i in range(1, len(vals)):
            if vals[i - 1][1] <= 0:
                break
            r_ = vals[i][1] / vals[i - 1][1] - 1.0
            d = vals[i][0]
            rs_ = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
            v *= (1.0 + r_ + rs_)
            cur.append((d, max(v, 1e-9)))
        curves.append(cur)
    L = min(len(x) for x in curves)
    our_ds = [x[0] for x in curves[0][:L]]
    our_v = [st.median(curves[j][i][1] for j in range(len(curves))) for i in range(L)]

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")

    def ma_series(ds_, c_, cash_rate=2.0):
        n = len(c_)
        mm, run_ = [None] * n, []
        for i in range(n):
            run_.append(c_[i])
            if len(run_) > 200:
                run_.pop(0)
            mm[i] = (sum(run_) / 200.0) if i >= 199 else None
        v, out, inm = 1.0, [1.0], True
        cd = cash_rate / 100.0 / 252.0
        for i in range(1, n):
            v *= (c_[i] / c_[i - 1]) if inm else (1.0 + cd)
            out.append(v)
            if inm and mm[i] is not None and c_[i] < mm[i]:
                inm = False
            elif (not inm) and mm[i] is not None and c_[i] > mm[i]:
                inm = True
        return out

    ARMS = (("① 우리 규칙 (①+③)", our_ds, our_v),
            ("② SPY 그냥 보유", dsS, cS),
            ("③ QQQ 그냥 보유", dsQ, cQ),
            ("④ SPY + 200일선", dsS, ma_series(dsS, cS)))

    out = {}
    for yrs in HOR:
        print("### 보유 **%d년** — 시작일을 날마다 바꿔 가며 (연평균)" % yrs, flush=True)
        print("  %-20s %9s %10s %10s %10s %9s"
              % ("", "**최악**", "하위10%", "중앙", "상위10%", "최선"), flush=True)
        print("  " + "-" * 74, flush=True)
        for nm, d_, v_ in ARMS:
            w = windows(d_, v_, yrs)
            if not w:
                continue
            q = lambda f: w[int(len(w) * f)]                       # noqa: E731
            out.setdefault(nm, {})[yrs] = {"min": w[0], "p10": q(0.10),
                                           "med": q(0.50), "p90": q(0.90), "max": w[-1],
                                           "n": len(w),
                                           "neg": 100.0 * sum(1 for x in w if x < 0) / len(w)}
            print("  %-20s %+8.2f%% %+9.2f%% %+9.2f%% %+9.2f%% %+8.2f%%"
                  % (nm, w[0], q(0.10), q(0.50), q(0.90), w[-1]), flush=True)
        print("     («마이너스로 끝난» 시작일 비율)  %s"
              % (" · ".join("%s %.0f%%" % (nm.split()[0], out[nm][yrs]["neg"])
                            for nm, _d, _v in ARMS if nm in out)), flush=True)
        print("", flush=True)

    print("=" * 100, flush=True)
    print("  ★ 읽는 법 — **중앙이 아니라 «최악»과 «마이너스 비율»을 본다.**", flush=True)
    print("     사용자 물음이 「돈이 필요한 시점이 하필 나쁠 때」이기 때문이다.", flush=True)
    (r91.OUT / "122-anytime.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 122-anytime.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
