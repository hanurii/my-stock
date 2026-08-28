# -*- coding: utf-8 -*-
"""101b — 미너비니 쪽을 **무한매수법과 «같은 창»**에서 굴린다. (표 A 용)

창: **2010-03-11 ~ 2026-08-21** — SOXL 상장일 이후. TQQQ·SOXL 이 같은 창에 든다.

🚨 이건 «판정»이 아니라 **비교표의 한 칸**이다.
   91 의 규칙을 **한 글자도 안 바꾸고** 창만 바꿔 굴린다. 고르는 것이 없으므로 창을 안 태운다.
🚨 **2010~2026 은 91 이 이미 본 구간을 포함한다**(2017-09~2026 이 개발 구간).
   → 표에 그렇게 적는다. 「표본 밖」이 아니다.

내는 것: `.cache/bt5y/out/101b-minervini-window.json`
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

NLS = chr(10)
D0, D1 = "2010-03-11", "2026-08-21"
YEARS = tuple(range(2010, 2027))



def lever(res, L, fin_rate):
    """일간 재조정 레버리지 — 실제 레버리지 ETF 가 하는 것과 같은 셈.

    🚨 검증 세션 ④: 「위험맞춤 칸은 **미너비니를 노출로 조정한 것** 하나만 정당하다」
       (무한매수법 쪽을 줄이면 그 방법의 «정의»를 깬다)
    fin_rate: 차입 연리(%). 0 = 미너비니에 «가장 유리한» 가정.
    """
    # 🚨 관문 ⑬ — `curve` 는 **마지막 «정산 전»에서 끝난다.**
    #    루프가 끝난 뒤 `close_out` 이 남은 보유를 청산하며 eq 를 바꾸는데 곡선엔 안 붙는다.
    #    (`slot_sim_lots.py:272` 가 마지막 append, 정산은 그 «뒤»)
    #    그래서 곡선만으로 재면 L=1.0 이 equity_pct 를 «재현 못 한다»(실측 +10.42 vs +10.96).
    #    → 마지막 점을 «정산 후» 값으로 붙인다. 그러면 L=1.0 이 소수점까지 맞는다.
    vals = [z[1] for z in res["curve"]] + [1.0 + res["equity_pct"] / 100.0]
    v, peak, mdd = 1.0, 1.0, 0.0
    d = fin_rate / 100.0 / 252.0 * (L - 1.0)
    for i in range(1, len(vals)):
        if vals[i - 1] <= 0:
            break
        r = vals[i] / vals[i - 1] - 1.0
        v *= (1.0 + L * r - d)
        if v <= 0:
            v = 1e-9
            break
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return (v - 1.0) * 100.0, mdd * 100.0


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    print("=" * 100, flush=True)
    print("101b — 미너비니(91 규칙 그대로)를 %s ~ %s 에서" % (D0, D1), flush=True)
    print("=" * 100, flush=True)
    print("🚨 판정 아님 · 비교표의 «한 칸» · seed %d\n" % n_seed, flush=True)

    (by0, by1, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2

    out = {}
    for name, by in (("0 선별없이", by0), ("1 주도업종", by1), ("2 조합(정본)", by2)):
        ev, _b, _t = r91.replay(by)
        rs = r91.sim(ev, n_seed)
        if name.startswith("2"):
            curves = rs
        tot = sorted(x["equity_pct"] for x in rs)
        med = st.median(tot)
        yrs = 16.45
        out[name] = {"n_entry": len(ev), "total_pct": med,
                     "cagr": ((1 + med / 100.0) ** (1 / yrs) - 1) * 100,
                     "p25": tot[int(n_seed * .25)], "p05": tot[int(n_seed * .05)],
                     "mdd_pct": st.median(x["mdd_pct"] for x in rs),
                     "expo_mean": st.median(x["expo_mean"] for x in rs),
                     "conc": st.median(x["conc_median"] for x in rs),
                     "n_filled": st.median(x["n_filled"] for x in rs)}
        o = out[name]
        print("  %-14s 진입 %6d · 자산중앙 %+9.2f%% · 연환산 %+6.2f%% · MDD %6.1f%%"
              " · 투입율 %5.1f%% · 동시 %4.1f · 체결 %5.0f"
              % (name, o["n_entry"], o["total_pct"], o["cagr"], o["mdd_pct"],
                 o["expo_mean"], o["conc"], o["n_filled"]), flush=True)

    # ── 위험맞춤 칸 (검증 세션 ④) ────────────────────────────────
    print(NLS + "  ★ 위험맞춤 — **미너비니를 «일간 재조정 레버리지»로 올리면**", flush=True)
    print("     (무한매수법 TQQQ 20분할의 낙폭이 -56.8%% 다. 거기까지 올려 본다)", flush=True)
    print("     %-6s %12s %10s %10s %10s" % ("배수", "1,000만원->", "연환산", "최대낙폭", "차입 3%%면"),
          flush=True)
    g1 = [lever(x, 1.0, 0.0)[0] for x in curves]
    gap = max(abs(a - x["equity_pct"]) for a, x in zip(g1, curves))
    print("     관문 ⑬ L=1.0 이 원래 값을 재현하는가 → **최대 어긋남 %.2e%%p** %s"
          % (gap, "통과" if gap < 1e-6 else "🚨 미통과 — 멈춘다"), flush=True)
    if gap >= 1e-6:
        return 3
    for L in (1.0, 1.5, 2.0, 2.5, 3.0):
        a0 = [lever(x, L, 0.0) for x in curves]
        a3 = [lever(x, L, 3.0) for x in curves]
        t0, m0 = st.median(z[0] for z in a0), st.median(z[1] for z in a0)
        t3 = st.median(z[0] for z in a3)
        yrs = 16.45
        c0 = ((1 + t0 / 100.0) ** (1 / yrs) - 1) * 100
        c3 = ((1 + t3 / 100.0) ** (1 / yrs) - 1) * 100
        out["레버 %.1f배" % L] = {"total_pct": t0, "cagr": c0, "mdd_pct": m0,
                                  "cagr_fin3": c3}
        print("     %-6.1f %11.0f만 %+9.2f%% %9.1f%% %+9.2f%%"
              % (L, (1 + t0 / 100.0) * 1000, c0, m0, c3), flush=True)

    (r91.OUT / "101b-minervini-window.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 101b-minervini-window.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
