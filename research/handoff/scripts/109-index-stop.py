# -*- coding: utf-8 -*-
"""109 — **지수에 «손절선»을 걸면 어떻게 되는가** (사용자 물음 2026-08-30)

> 「그럼 지수 투자할 때 손절선을 정해놓고 투자하면 되지 않나요?」

# 🚨 방향을 «먼저» 적는다 (값 보기 전)
```
82번  「손해는 «파는 것»이 아니라 «안 사는 것»에서 온다」
108번  200일선 «아래» 기간의 «반등»이 숏을 거의 다 먹었다
→ **손절선은 낙폭을 줄이지만, 「팔고 나서 오는 반등」을 놓쳐 수익이 더 깎일 것**
→ 그리고 **재진입 규칙이 결과를 지배할 것**이다. 손절 자체보다 그게 클 것으로 본다
```

# 규칙 — **파는 법보다 «다시 사는 법»을 갈라서 본다**
```
① 그냥 보유                                        (바탕)
② 200일선   종가가 아래면 현금 · 위면 보유
③ 고점 대비 −10 / −15 / −20% 면 판다
   재진입 ㉮ **200일선 위**로 오면     ㉯ **저점 대비 +10%** 오르면
현금 이자   연 0% / 2%   (둘 다 찍는다 — 실제 값은 시기마다 다르다)
🚨 종가를 보고 **다음 날** 움직인다. 당일 체결 안 한다(미래 안 봄)
🚨 세금·수수료 «안» 넣었다 — **자주 파는 쪽이 «유리해진» 자**다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)

BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))
D0, D1 = "1999-04-01", "2026-08-21"


def load(tk):
    d = json.loads((r91.OUT / "101-fund-ohlc.json").read_text(encoding="utf-8"))
    s = d[tk]["series"]
    ds = [x for x in sorted(s) if D0 <= x <= D1]
    return ds, [s[x][3] for x in ds]


def run(ds, c, mode, stop=None, reenter="ma", cash_rate=0.0):
    """mode: 'hold' | 'ma' | 'stop'.  🚨 종가를 보고 «다음 날» 움직인다."""
    n = len(c)
    ma = [None] * n
    run_ = []
    for i in range(n):
        run_.append(c[i])
        if len(run_) > 200:
            run_.pop(0)
        ma[i] = (sum(run_) / 200.0) if i >= 199 else None

    v, peak_v, mdd = 1.0, 1.0, 0.0
    inmkt = True
    peak_p = c[0]                       # 보유 중 고점 (손절 기준)
    low_p = c[0]                        # 현금 중 저점 (재진입 기준)
    cd = cash_rate / 100.0 / 252.0
    n_sell = n_cash = 0
    for i in range(1, n):
        # ── 오늘 «수익» 정산 (어제 정한 상태로)
        if inmkt:
            v *= c[i] / c[i - 1]
        else:
            v *= (1.0 + cd)
            n_cash += 1
        peak_v = max(peak_v, v)
        mdd = min(mdd, v / peak_v - 1.0)
        # ── 오늘 종가를 보고 «내일» 상태를 정한다
        if inmkt:
            peak_p = max(peak_p, c[i])
            out = False
            if mode == "ma":
                out = (ma[i] is not None and c[i] < ma[i])
            elif mode == "stop":
                out = (c[i] <= peak_p * (1.0 - stop / 100.0))
            if out:
                inmkt = False
                low_p = c[i]
                n_sell += 1
        else:
            low_p = min(low_p, c[i])
            back = False
            if mode == "ma":
                back = (ma[i] is not None and c[i] > ma[i])
            elif reenter == "ma":
                back = (ma[i] is not None and c[i] > ma[i])
            else:
                back = (c[i] >= low_p * 1.10)
            if back:
                inmkt = True
                peak_p = c[i]
    yrs = n / 252.0
    return {"cagr": (v ** (1 / yrs) - 1) * 100, "mdd": mdd * 100, "final": v,
            "n_sell": n_sell, "cash_pct": 100.0 * n_cash / n}


def main() -> int:
    print("=" * 100, flush=True)
    print("109 — 지수에 «손절선»을 걸면 어떻게 되는가 · 1999-04 ~ 2026-08 (27.4년)", flush=True)
    print("=" * 100, flush=True)
    print("🚨 값 보기 «전»에 적은 예상: 낙폭은 줄지만 «반등을 놓쳐» 수익이 더 깎인다.", flush=True)
    print("   그리고 **재진입 규칙이 손절폭보다 결과를 더 지배할 것**이다.", flush=True)
    print("🚨 세금·수수료 «안» 넣었다 — 자주 파는 쪽이 «유리해진» 자다.\n", flush=True)

    for tk in ("SPY", "QQQ"):
        ds, c = load(tk)
        print("### %s  (%s ~ %s · %s일)"
              % (tk, ds[0], ds[-1], "{:,}".format(len(ds))), flush=True)
        print("  %-34s %12s %10s %9s %8s %8s"
              % ("규칙", "1,000만원→", "연평균", "최대낙폭", "판 횟수", "현금비율"), flush=True)
        print("  " + "-" * 88, flush=True)
        rows = []
        base = run(ds, c, "hold")
        rows.append(("① 그냥 보유", base))
        for cr in (0.0, 2.0):
            rows.append(("② 200일선 (현금이자 %d%%)" % int(cr),
                         run(ds, c, "ma", cash_rate=cr)))
        for sp in (10, 15, 20):
            for re_, rl in (("ma", "200일선 위로"), ("low", "저점+10%")):
                rows.append(("③ 고점 −%d%% 손절 · 재진입 %s" % (sp, rl),
                             run(ds, c, "stop", stop=sp, reenter=re_, cash_rate=0.0)))
        for nm, r in rows:
            mark = ""
            if r["cagr"] > base["cagr"]:
                mark = " ✅"
            print("  %-34s %11.0f만 %+9.2f%%%s %8.1f%% %8s %7.1f%%"
                  % (nm, r["final"] * 1000, r["cagr"], mark, r["mdd"],
                     "{:,}".format(r["n_sell"]), r["cash_pct"]), flush=True)
        print("", flush=True)

    # ── 구간별 — 어디서 벌고 어디서 잃나 ─────────────────────────────
    print("=" * 100, flush=True)
    print("★ 구간별 — **손절선이 «어디서» 도와주고 «어디서» 깎는가** (SPY)", flush=True)
    print("  %-34s %14s %14s %14s"
          % ("규칙", "닷컴 99~01", "2002~2017", "2018~2026"), flush=True)
    print("  " + "-" * 82, flush=True)
    ds, c = load("SPY")
    for nm, mode, sp, re_ in (("① 그냥 보유", "hold", None, "ma"),
                              ("② 200일선", "ma", None, "ma"),
                              ("③ −15% 손절 · 200일선 재진입", "stop", 15, "ma"),
                              ("③ −15% 손절 · 저점+10% 재진입", "stop", 15, "low")):
        cells = []
        for lab, a, b in BLOCKS:
            idx = [i for i, d in enumerate(ds) if a <= d <= b]
            r = run(ds[idx[0]:idx[-1] + 1], c[idx[0]:idx[-1] + 1], mode, sp, re_)
            cells.append("%+7.2f%% (%5.1f%%)" % (r["cagr"], r["mdd"]))
        print("  %-34s %14s %14s %14s" % (nm, cells[0], cells[1], cells[2]), flush=True)
    print("\n  괄호 = 그 구간의 최대 낙폭", flush=True)
    print("\n🚨 세금이 빠져 있다. 실제로는 팔 때마다 세금을 내므로 **자주 파는 쪽이 더 나빠진다.**",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
