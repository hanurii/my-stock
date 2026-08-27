# -*- coding: utf-8 -*-
"""93 — **연도별 표**. 1999~2026 을 «끊지 않고» 한 번에 굴린다.

사용자 지시(2026-08-28):
  ① 닷컴 구간을 «빼지» 말 것 — 미너비니 방식은 중소형 성장주라 성장주 각광기에 크게 번다
  ② 기간 덩어리 말고 **연도별로 잘라 비교표**로 볼 것

🚨 **이것은 «판정»이 아니라 «서술»이다.**
   91 의 규칙을 **한 글자도 안 바꾸고** 가진 자료 전체에 굴려 «해마다 어땠나»를 찍는다.
   새로 고르는 것이 없으므로 창을 태우지 «않는다». 문턱도 «없다».
   🚨 **여기서 나온 숫자로 규칙을 고치면 그때 창이 사라진다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/93-by-year.py [--quick]
"""
from __future__ import annotations

import datetime as _dt
import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402

_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)

OUT = ROOT / ".cache" / "bt5y" / "out"

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
# 91 이 쓴 창 라벨 — 표에 «어느 구간이었는지»를 함께 찍는다
WIN = {}
for y in YEARS:
    WIN[y] = ("닷컴" if y <= 2001 else
              ("표본밖" if y <= 2016 else
               ("표본밖" if y == 2017 else "이미봄")))


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def year_returns(curve, settle_pct):
    """곡선에서 **해마다의 수익률**을 뽑는다.

    🚨 곡선은 «일이 있었던 날»만 담는다 → 각 해 «마지막으로 알려진» 값을 쓴다(앞으로 채움).
    🚨 곡선은 «마지막 보유 정산 «전»»에서 끝난다(slot_sim_lots.py:256 vs 260)
       → 마지막 점을 정산값으로 갈아 끼운다. 82번에서 쓴 것과 같은 규약.
    """
    cv = list(curve)
    cv[-1] = (cv[-1][0], 1.0 + settle_pct / 100.0)
    end = {}
    last = cv[0][1]
    for d, v in cv:
        last = v
        end[d[:4]] = v
    # 거래가 아예 없던 해는 직전 해 값을 잇는다
    out, prev = {}, 1.0
    for y in YEARS:
        v = end.get("%d" % y, prev)
        out[y] = (v / prev - 1.0) * 100.0 if prev else float("nan")
        prev = v
    return out


def bench_year(tk):
    b = json.loads((OUT / "91-benchmarks.json").read_text(encoding="utf-8"))
    ser = b[tk]["series"]
    ds = sorted(d for d in ser if D0 <= d <= D1)
    end, prev_first = {}, None
    for d in ds:
        end[d[:4]] = ser[d][0]
        if prev_first is None:
            prev_first = ser[d][0]
    out, prev = {}, prev_first
    for y in YEARS:
        v = end.get("%d" % y)
        if v is None:
            out[y] = float("nan")
            continue
        out[y] = (v / prev - 1.0) * 100.0
        prev = v
    return out


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED

    print("=" * 108, flush=True)
    print("93 — 연도별 표 · 1999-04 ~ 2026-08 을 «끊지 않고» 한 번에 (판정 아님 · 서술)", flush=True)
    print("=" * 108, flush=True)
    print("규칙은 91 그대로 · seed %d · ext 미사용 · 월말패널 91-monthly-us-full.json\n" % n_seed,
          flush=True)

    (by0, by1, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2

    res = {}
    for name, by in (("0 선별없이", by0), ("1 주도업종", by1), ("2 조합", by2)):
        ev, blk, _t = r91.replay(by)
        rs = r91.sim(ev, n_seed)
        yrs_all = [year_returns(x["curve"], x["equity_pct"]) for x in rs]
        med = {y: st.median(d[y] for d in yrs_all) for y in YEARS}
        tot = sorted(x["equity_pct"] for x in rs)
        res[name] = {"year": med, "total": st.median(tot),
                     "p5": tot[int(n_seed * .05)],
                     "mdd": st.median(x["mdd_pct"] for x in rs),
                     "n_entry": len(ev)}
        print("  %-10s 진입 %6d · 27.4년 누적 중앙 %+.2f%%"
              % (name, len(ev), res[name]["total"]), flush=True)

    spy, qqq = bench_year("SPY"), bench_year("QQQ")

    print("\n" + "=" * 108, flush=True)
    print("  %-6s %-8s %10s %10s %10s %10s %10s"
          % ("연도", "구간", "0 선별없이", "1 주도업종", "**2 조합**", "S&P500", "나스닥100"),
          flush=True)
    print("  " + "-" * 104, flush=True)
    w = {"0 선별없이": res["0 선별없이"]["year"], "1 주도업종": res["1 주도업종"]["year"],
         "2 조합": res["2 조합"]["year"]}
    win2 = 0
    n_cmp = 0
    for y in YEARS:
        s, q = spy.get(y, float("nan")), qqq.get(y, float("nan"))
        mark = ""
        if s == s:
            n_cmp += 1
            if w["2 조합"][y] > s:
                win2 += 1
                mark = " ✅"
            else:
                mark = " ❌"
        print("  %-6d %-8s %+9.1f%% %+9.1f%% %+9.1f%% %+9.1f%% %+9.1f%%%s"
              % (y, WIN[y], w["0 선별없이"][y], w["1 주도업종"][y], w["2 조합"][y], s, q, mark),
              flush=True)
    print("  " + "-" * 104, flush=True)
    print("  조합이 S&P500 을 이긴 해 **%d / %d**" % (win2, n_cmp), flush=True)

    # 누적 — 1,000만원 기준
    print("\n  1,000만원을 넣었다면 (27.4년 · 중앙값 판)", flush=True)
    for name in ("0 선별없이", "1 주도업종", "2 조합"):
        r = res[name]
        print("     %-10s %12s원   (최악일 때 %.1f%% · 운 나쁜 판 %+.1f%%)"
              % (name, "{:,.0f}".format(1000e4 * (1 + r["total"] / 100)),
                 r["mdd"], r["p5"]), flush=True)
    for tk, d in (("S&P500", spy), ("나스닥100", qqq)):
        v = 1.0
        for y in YEARS:
            if d.get(y) == d.get(y):
                v *= (1 + d[y] / 100)
        print("     %-10s %12s원" % (tk, "{:,.0f}".format(1000e4 * v)), flush=True)

    (OUT / "93-by-year.json").write_text(
        json.dumps({"years": {str(y): {k: w[k][y] for k in w} for y in YEARS},
                    "spy": {str(y): spy.get(y) for y in YEARS},
                    "qqq": {str(y): qqq.get(y) for y in YEARS},
                    "totals": {k: {kk: vv for kk, vv in v.items() if kk != "year"}
                               for k, v in res.items()}},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 93-by-year.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
