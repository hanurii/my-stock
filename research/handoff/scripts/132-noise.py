# -*- coding: utf-8 -*-
"""132 — **+25 골짜기가 «진짜»인가: 잡음부터 잰다** (사전등록 · 값 보기 «전»)

사용자(2026-08-31): 「**+30 으로 결정하기 전에 잡음 문제 먼저 확인해줘.**」

★ 옳은 순서다. 131·129 는 칸마다 «중앙값 하나»만 보고 줄을 세웠다.
   **그 중앙값이 얼마나 흔들리는지 안 재고 순위를 믿으면 안 된다.**

# 이상한 점 — 손절 −10 에서
```
+20  9,280만   →   +25  **7,351만**  ←  뚝 떨어짐   →   +30  12,908만
「목표를 올릴수록 좋아진다」면 +25 도 +20 보다 좋아야 하는데 «나쁘다».
→ 잡음인가, 진짜 골짜기인가?
```

# 세 갈래로 «동시에» 캔다
```
① **촘촘한 격자**   +20 · +22.5 · +25 · +27.5 · +30 · +32.5 · +35   (한 칸이 튄 건지 보려면)
② **판을 늘린다**   20판 → **60판**   (127 에서 40판 vs 60판이 7.5% 어긋났다)
③ ★★ **짝비교**   **같은 운의 번호**에서 +30 vs +20 을 직접 견준다
   → 공통 잡음이 상쇄된다. **「60판 중 몇 판에서 +30 이 이겼나」**가 진짜 답이다
```
손절 −10 고정 · 청산 절반+추격 · 세후 · 지수 숏 얹음

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AY**★ | 🚨 관문 — 수수료 횟수 = 매수 수 · Σ(자리 손익) = 총수익 |
| **AZ**★ | **짝비교**에서 +30 이 +20 을 이긴 판이 **60판 중 70% 초과** |
| **BA** | +25 골짜기가 «촘촘한 격자 + 60판»에서도 남는가 |
| **BB** | 🚨 **한 칸 «안»의 폭(5~95%)** 과 **칸 «사이» 차이**를 «같은 줄»에 적는다 |

**AZ★ 를 넘으면 「+30 으로 옮길 근거가 있다」, 못 넘으면 「순위는 잡음이다」.**

# ★ 방향을 «먼저» 적는다
```
㉮ 🚨 **한 칸 «안»의 폭이 칸 «사이» 차이보다 «클» 것이다** — 27년 복리라 판마다 크게 갈린다
   (74번 실측: 한 칸 안 406%p vs 변형 사이 16.7%p = **24배**)
   → 그러면 **「순위표」는 못 믿고 «짝비교»만 남는다**
㉯ **짝비교에서는 +30 이 이길 것이다** — 네 손절 «전부»에서 이겼으므로
㉰ 🚨 **+25 골짜기는 «사라질» 것으로 본다** — 20판의 잡음일 가능성이 높다
   만약 60판에서도 «남으면» 그건 훨씬 흥미로운 일이고, 이유를 따로 캐야 한다
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
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
START, FEE = 1000.0, 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
TARGETS = (20.0, 22.5, 25.0, 27.5, 30.0, 32.5, 35.0)
STOP = 10.0
BASE, CAND = 20.0, 30.0
PASS = 70.0
FRONT, BACK = ("1999-04-01", "2011-12-31"), ("2012-01-01", "2026-08-21")


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 60
    print("=" * 106, flush=True)
    print("132 — **+25 골짜기가 «진짜»인가: 잡음부터 잰다** · 사전등록 · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 106, flush=True)
    print("★ 중앙값이 «얼마나 흔들리는지» 안 재고 순위를 믿으면 안 된다", flush=True)
    print("🚨 방향 먼저: **한 칸 «안»의 폭이 칸 «사이» 차이보다 클 것** → 짝비교만 남는다\n",
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

    r91.STOP, r91.HALF = STOP, 0.5
    per = {}                                     # 목표 -> [판마다 세후 총액]
    mdd = {}
    for tg in TARGETS:
        r91.TARGET = tg
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        vals, ms = [], []
        for x in rs:
            fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
            if len(fdates) != int(x["n_filled"]):
                print("🚨 AY★ 미통과 — 수수료 횟수", flush=True)
                return 3
            g = abs(sum(r_ * t2 / 100.0 for _d, r_, t2 in x["ret_log"])
                    - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
            if g >= 0.005:
                print("🚨 AY★ 미통과 — 손익 합 %.3f%%" % (g * 100), flush=True)
                return 4
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
            vals.append(r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1))
            ms.append(r129.shape(cds, ccv)[0])
        per[tg] = vals
        mdd[tg] = ms
        s = sorted(vals)
        print("  목표 +%-5.1f  중앙 %7.0f만 · **5~95%% %6.0f ~ %6.0f만** · 낙폭 중앙 %+.1f%%"
              % (tg, st.median(s), s[int(len(s) * 0.05)], s[int(len(s) * 0.95)],
                 st.median(ms)), flush=True)

    print("\n" + "=" * 106, flush=True)
    print("### BB — 🚨 **한 칸 «안»의 폭 vs 칸 «사이» 차이**", flush=True)
    widths = []
    for tg in TARGETS:
        s = sorted(per[tg])
        w = s[int(len(s) * 0.95)] - s[int(len(s) * 0.05)]
        widths.append(w)
        print("   목표 +%-5.1f  한 칸 «안» 폭 (5~95%%) = **%6.0f만**" % (tg, w), flush=True)
    meds = [st.median(per[t]) for t in TARGETS]
    gap = max(meds) - min(meds)
    print("\n   칸 «사이» 차이 (중앙값 최대−최소) = **%.0f만**" % gap, flush=True)
    print("   한 칸 «안» 폭의 중앙          = **%.0f만**" % st.median(widths), flush=True)
    print("   → **한 칸 «안»이 칸 «사이»의 %.1f배**  %s"
          % (st.median(widths) / gap if gap else 0,
             "→ 🚨 **순위표는 못 믿는다. 짝비교만 남는다**"
             if st.median(widths) > gap else "→ 순위표를 읽을 수 있다"), flush=True)

    print("\n### AZ★ — **짝비교** (같은 운의 번호끼리 · %d판)" % n_seed, flush=True)
    print("   %-22s %10s %12s" % ("", "이긴 판", "중앙 차이"), flush=True)
    print("   " + "-" * 48, flush=True)
    res = {}
    for a, b in ((CAND, BASE), (25.0, BASE), (25.0, CAND), (27.5, BASE), (35.0, BASE)):
        w = sum(1 for i in range(n_seed) if per[a][i] > per[b][i])
        d = st.median(per[a][i] - per[b][i] for i in range(n_seed))
        res["%.1f>%.1f" % (a, b)] = {"win": 100.0 * w / n_seed, "med": d}
        print("   +%-5.1f 가 +%-5.1f 를 이김   %5.1f%% (%2d/%d) %10.0f만%s"
              % (a, b, 100.0 * w / n_seed, w, n_seed, d,
                 "  ← **AZ★**" if (a, b) == (CAND, BASE) else ""), flush=True)

    AZ = res["%.1f>%.1f" % (CAND, BASE)]["win"] > PASS
    print("\n   **AZ★** +30 이 +20 을 이긴 판 > %.0f%% → **%s**"
          % (PASS, "통과" if AZ else "**미통과**"), flush=True)

    print("\n### BA — **+25 골짜기가 남는가** (촘촘한 격자 · %d판 중앙)" % n_seed, flush=True)
    line = "   "
    for tg in TARGETS:
        line += "+%.1f %7.0f만   " % (tg, st.median(per[tg]))
    print(line, flush=True)
    v25 = st.median(per[25.0])
    dip = v25 < st.median(per[22.5]) and v25 < st.median(per[27.5])
    print("   → +25 가 «양 옆(+22.5·+27.5)보다 낮은가»: **%s**"
          % ("**그렇다 — 골짜기가 남는다**" if dip else "**아니다 — 20판의 잡음이었다**"), flush=True)

    (r91.OUT / "132-noise.json").write_text(
        json.dumps({"med": {str(t): st.median(per[t]) for t in TARGETS},
                    "p5": {str(t): sorted(per[t])[int(n_seed * 0.05)] for t in TARGETS},
                    "p95": {str(t): sorted(per[t])[int(n_seed * 0.95)] for t in TARGETS},
                    "mdd": {str(t): st.median(mdd[t]) for t in TARGETS},
                    "paired": res, "AZ": AZ, "dip25": dip,
                    "width_med": st.median(widths), "gap": gap},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 132-noise.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
