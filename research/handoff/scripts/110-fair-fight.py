# -*- coding: utf-8 -*-
"""110 — **공정한 비교: 미너비니(손절 있음) vs 지수 + 손절선** (사용자 물음 2026-08-30)

> 「엄청난 낙폭을 그냥 견디는 개인투자자는 잘 없을 겁니다. … 지수 투자를 할 때도 손절선을 지켜
>  최대 낙폭을 줄여야 할 것 같습니다. 이런 경우를 고려하여 미너비니 방법과 우위를 비교해 주세요.」

★ **지적이 정확하다.** 지금까지 표는 「손절하는 미너비니」와 「끝까지 버티는 지수」를 견줬다.
   **둘 다 손절을 걸어야 공정하다.**

# 세우는 판
```
① 미너비니        5칸 · 손절 −8% · 익절 +20% (91 정본)
② SPY 그냥 보유    (참고 — 사용자가 «못 견딘다»고 한 쪽)
③ SPY + 200일선   아래면 현금 · 위면 보유 (현금이자 2%)
④ QQQ 그냥 보유    (참고)
⑤ QQQ + 200일선
★ ⑥ 낙폭 맞춤     ③ 을 «미너비니와 같은 낙폭»이 되게 레버리지로 올린 판
                   ← **이게 결정적인 칸이다.** 같은 위험에서 누가 더 버는가
```
🚨 세금·수수료 **안 넣었다** — 200일선은 27년에 90번 판다. **자주 파는 쪽이 «유리해진» 자**다.
🚨 미너비니는 운의 번호 200판 «중앙값», 지수는 «경로 하나»다. 폭이 비대칭이다.
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
_t = _u.spec_from_file_location("r109", HERE / "109-index-stop.py")
r109 = _u.module_from_spec(_t)
_t.loader.exec_module(r109)

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체 1999~2026", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴 1999~2001", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))


def lever_series(ds, c, mode, L, cash_rate=2.0):
    """지수+손절 판을 «일간 재조정 레버리지»로 L 배 올린다. 차입 연 3% 가정."""
    r = r109.run(ds, c, mode, cash_rate=cash_rate)
    return r


def levered(ds, c, L, fin=3.0):
    """200일선 판을 L 배로. 현금일 땐 레버리지도 없다(현금이니까)."""
    n = len(c)
    ma, run_ = [None] * n, []
    for i in range(n):
        run_.append(c[i])
        if len(run_) > 200:
            run_.pop(0)
        ma[i] = (sum(run_) / 200.0) if i >= 199 else None
    v, peak, mdd = 1.0, 1.0, 0.0
    inmkt = True
    d_fin = fin / 100.0 / 252.0 * (L - 1.0)
    for i in range(1, n):
        if inmkt:
            v *= (1.0 + L * (c[i] / c[i - 1] - 1.0) - d_fin)
        else:
            v *= (1.0 + 2.0 / 100.0 / 252.0)
        if v <= 0:
            v = 1e-9
            break
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
        if inmkt:
            if ma[i] is not None and c[i] < ma[i]:
                inmkt = False
        else:
            if ma[i] is not None and c[i] > ma[i]:
                inmkt = True
    yrs = n / 252.0
    return {"cagr": (v ** (1 / yrs) - 1) * 100, "mdd": mdd * 100, "final": v}


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else r91.N_SEED
    print("=" * 104, flush=True)
    print("110 — **공정한 비교: 미너비니(손절 있음) vs 지수 + 손절선** · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 104, flush=True)
    print("★ 지금까지 표는 「손절하는 미너비니」와 「끝까지 버티는 지수」를 견줬다.", flush=True)
    print("  **둘 다 손절을 걸어야 공정하다.**\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    ev, _x, _y = r91.replay(by2)
    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")

    out = {}
    for lab, a, b, yrs in WIN:
        e = [t for t in ev if a <= t["entry_date"] <= b]
        rs = r91.sim(e, n_seed)
        med = st.median(x["equity_pct"] for x in rs)
        mv = {"cagr": ((1 + med / 100.0) ** (1 / yrs) - 1) * 100,
              "mdd": st.median(x["mdd_pct"] for x in rs)}
        iS = [i for i, d in enumerate(dsS) if a <= d <= b]
        iQ = [i for i, d in enumerate(dsQ) if a <= d <= b]
        sS, cSw = dsS[iS[0]:iS[-1] + 1], cS[iS[0]:iS[-1] + 1]
        sQ, cQw = dsQ[iQ[0]:iQ[-1] + 1], cQ[iQ[0]:iQ[-1] + 1]
        row = {
            "① 미너비니 (손절 −8%)": mv,
            "② SPY 그냥 보유": r109.run(sS, cSw, "hold"),
            "③ SPY + 200일선": r109.run(sS, cSw, "ma", cash_rate=2.0),
            "④ QQQ 그냥 보유": r109.run(sQ, cQw, "hold"),
            "⑤ QQQ + 200일선": r109.run(sQ, cQw, "ma", cash_rate=2.0),
        }
        out[lab] = row
        print("### %s" % lab, flush=True)
        print("  %-24s %10s %10s %12s" % ("", "연평균", "최대낙폭", "수익÷낙폭"), flush=True)
        print("  " + "-" * 60, flush=True)
        for k, r in row.items():
            rr = abs(r["cagr"] / r["mdd"]) if r["mdd"] else float("nan")
            print("  %-24s %+9.2f%% %9.1f%% %11.3f" % (k, r["cagr"], r["mdd"], rr), flush=True)
        print("", flush=True)

    # ── ★ 낙폭을 «맞춰» 놓고 견준다 ──────────────────────────────────
    print("=" * 104, flush=True)
    print("★★ **낙폭을 «맞춰» 놓고 견준다** — SPY+200일선을 미너비니와 «같은 낙폭»까지 올린다",
          flush=True)
    print("   (일간 재조정 레버리지 · 차입 연 3% 가정)\n", flush=True)
    for lab, a, b, yrs in WIN:
        m = out[lab]["① 미너비니 (손절 −8%)"]
        iS = [i for i, d in enumerate(dsS) if a <= d <= b]
        sS, cSw = dsS[iS[0]:iS[-1] + 1], cS[iS[0]:iS[-1] + 1]
        best, bl = None, None
        for L10 in range(10, 41):
            L = L10 / 10.0
            r = levered(sS, cSw, L)
            if best is None or abs(r["mdd"] - m["mdd"]) < abs(best["mdd"] - m["mdd"]):
                best, bl = r, L
        gap = best["cagr"] - m["cagr"]
        print("  %-16s 미너비니 %+7.2f%% (낙폭 %5.1f%%)   vs   "
              "SPY+200일선 **%.1f배** %+7.2f%% (낙폭 %5.1f%%)   →  **%+.2f%%p**"
              % (lab, m["cagr"], m["mdd"], bl, best["cagr"], best["mdd"], gap), flush=True)
        out[lab]["★ 낙폭맞춘 SPY+200일선"] = {"L": bl, **best, "gap": gap}

    print("\n" + "=" * 104, flush=True)
    print("🚨 세금·수수료 «안» 넣었다 — 200일선은 27년에 90번 판다. **자주 파는 쪽이 유리해진 자**",
          flush=True)
    print("🚨 미너비니는 운의 번호 200판 «중앙», 지수는 «경로 하나»다. **폭이 비대칭**", flush=True)
    print("🚨 레버리지 칸은 «산수»다 — 개인이 지수 ETF 에 2~3배를 실제로 걸 수 있는지는 다른 문제",
          flush=True)
    (r91.OUT / "110-fair-fight.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 110-fair-fight.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
