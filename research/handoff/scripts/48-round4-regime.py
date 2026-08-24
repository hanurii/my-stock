# -*- coding: utf-8 -*-
"""48 — **4회차 · 시장 국면**. 헤드라인 `4a` 는 결과를 보기 «전»에 고정됐다. **3a 위에 누적.**

| 변형 | |
|---|---|
| **4a ★** | **같은 유니버스 등가중 지수 < 20MA 이면 «신규 진입 중단»**(보유 유지) |
| 4b | **S&P500 < 50MA** 이면 신규 진입 중단 |
| 4c | 노출 상한을 국면에 따라 **100 / 50 / 0%** 3단 |
| 4d | (대조) 4회차 없음 = **3a** |

🚨 룩어헤드 차단 — **국면은 «스캔일 종가»까지만 본다**
------------------------------------------------------
하네스는 **스캔일 자료로 판단하고 «이튿날» 진입**한다(실측: 5,542/5,542 건 전부
`entry_date > scan_date`). 그러므로 **스캔일 종가 기준 국면은 룩어헤드가 아니다.**
이동평균도 그날까지의 값만 쓴다.

🚨 등가중 지수의 «청소 규약»
----------------------------
등가중은 규약에 흔들린다(오늘 확인: filt_daily +52.76% ~ all_bh +523.83%, **130배**).
**하네스와 같은 규약** = `curve_harness_filt`(하네스 거래대금 문턱 + 시점 유니버스, 일별 재배분).
**열 이름에 규약을 박는다.**

4c 의 3단 정의 (지시서에 없어 «내가» 정한다 — 결과 보기 전에 고정)
--------------------------------------------------------------------
- **100%**: 지수 ≥ 20MA
- **50%** : 지수 < 20MA 이지만 ≥ 50MA
- **0%**  : 지수 < 50MA

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/48-round4-regime.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                    # noqa: E402
import slot_sim                                          # noqa: E402
import slot_sim_pyr as sp                                # noqa: E402

_s = _u.spec_from_file_location("r47", HERE / "47-round3-pyramid.py")
r47 = _u.module_from_spec(_s)
_s.loader.exec_module(r47)
r41 = r47.r41
OUT = ROOT / ".cache" / "bt5y" / "out"

N_SEED = 200
RISK, CAP, PILOT = 0.0125, 0.25, 0.5
ADDS = ((3.0, 0.5),)
REGIMES = (("무비용", 0.0, 0.0), ("한국-미래에셋", 0.0014, 0.0034))
FILLS = (("종가판", "close", "close"), ("실집행 근사판", "limit", "market"))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def ma_flags(curve, wins=(20, 50)):
    """[(날짜, 값)] → {날짜: {20: 값>=MA20, 50: ...}}. **그날까지만** 쓴다."""
    d = [x[0] for x in curve]
    v = [x[1] for x in curve]
    out = {}
    for i, day in enumerate(d):
        f = {}
        for w in wins:
            if i + 1 < w:
                f[w] = None                     # 자료 부족 — 판단 안 함
            else:
                f[w] = v[i] >= st.mean(v[i - w + 1:i + 1])
        out[day] = f
    return out


def spx_curve(idx):
    ks = sorted(idx["US500"])
    return [(k, idx["US500"][k]) for k in ks]


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))
    idx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))
    eqw_f = ma_flags(eqw["curve_harness_filt"])
    spx_f = ma_flags(spx_curve(idx))
    print("국면 지표 — 등가중 `curve_harness_filt`(**하네스 문턱 + 시점 유니버스 + 일별 재배분**) "
          "%d일 · S&P500 %d일" % (len(eqw_f), len(spx_f)), flush=True)
    on20 = sum(1 for f in eqw_f.values() if f[20]) / len(eqw_f) * 100
    on50s = sum(1 for f in spx_f.values() if f[50]) / len(spx_f) * 100
    print("  등가중 ≥ 20MA 인 날 **%.1f%%** · S&P500 ≥ 50MA 인 날 **%.1f%%**"
          % (on20, on50s), flush=True)

    def keep(flags, w):
        def f(p):
            g = flags.get(p["scan_date"])
            return True if (g is None or g[w] is None) else g[w]
        return f

    def scale3(p_scan):
        g = eqw_f.get(p_scan)
        if g is None or g[20] is None or g[50] is None:
            return 1.0
        if g[20]:
            return 1.0
        return 0.5 if g[50] else 0.0

    res = {}
    for fname, ft, fs in FILLS:
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# 4회차 · %s" % fname, flush=True)
        print("#" * 92, flush=True)
        ev3, _ = r47.replay(by, ft, fs, adds=ADDS)                    # 3a = 4d
        by_a = {y: [p for p in ps if keep(eqw_f, 20)(p)] for y, ps in by.items()}
        by_b = {y: [p for p in ps if keep(spx_f, 50)(p)] for y, ps in by.items()}
        ev4a, _ = r47.replay(by_a, ft, fs, adds=ADDS)
        ev4b, _ = r47.replay(by_b, ft, fs, adds=ADDS)
        n_all = sum(len(v) for v in by.values())
        print("  방아쇠 %d → 4a %d (%.1f%% 남음) · 4b %d (%.1f%%)"
              % (n_all, sum(len(v) for v in by_a.values()),
                 100 * sum(len(v) for v in by_a.values()) / n_all,
                 sum(len(v) for v in by_b.values()),
                 100 * sum(len(v) for v in by_b.values()) / n_all), flush=True)
        for rname, fb, fs_ in REGIMES:
            row, curves = {}, {}
            with Cost(fb, fs_):
                spec = (("3a(=4d)", ev3, None), ("4a", ev4a, None), ("4b", ev4b, None),
                        ("4c", ev3, scale3))
                for name, e, dsc in spec:
                    b = sp.band(e, n_runs=N_SEED, risk=RISK, cap=CAP, pilot=PILOT,
                                date_scale=dsc)
                    c = [sp.sim_pyr(e, seed=s, risk=RISK, cap=CAP, pilot=PILOT,
                                    date_scale=dsc)["curve"] for s in range(10)]
                    row[name] = {"n_filled": b["n_filled"], "equity": b["median"],
                                 "p5": b["p5"], "p95": b["p95"], "mdd": b["mdd"],
                                 "arith": b["arith"], "fpt": b["filled_per_trade"],
                                 "added": b["n_added"], "add_blocked": b["n_add_blocked"],
                                 "conc_median": b["conc_median"], "conc_p10": b["conc_p10"],
                                 "conc_p90": b["conc_p90"], "conc_max": b["conc_max"],
                                 "overrun": b["risk_overrun_mean"],
                                 "cash_floor": b["cash_floor"]}
                    curves[name] = c
            print("", flush=True)
            print("  [%s]" % rname, flush=True)
            print("    %-8s %8s %13s %12s %12s %12s %10s"
                  % ("판", "체결", "체결분거래당", "산술", "관측", "격차", "동시보유중앙"), flush=True)
            for k in ("3a(=4d)", "4a", "4b", "4c"):
                v = row[k]
                print("    %-8s %8.0f %12.4f%% %11.2f%% %11.2f%% %11.2f%%p %9.0f"
                      % (k, v["n_filled"], v["fpt"], v["arith"], v["equity"],
                         v["equity"] - v["arith"], v["conc_median"]), flush=True)
            print("    🚨 주판정 — 짝비교(자료 축 · 4a − 3a)", flush=True)
            print(da.fmt(da.sweep(curves["4a"], curves["3a(=4d)"])), flush=True)
            print("    항등 분해(4a): 산술 증분 %+.2f%%p · 격차 증분 %+.2f%%p = 관측 증분 %+.2f%%p"
                  % (row["4a"]["arith"] - row["3a(=4d)"]["arith"],
                     (row["4a"]["equity"] - row["4a"]["arith"])
                     - (row["3a(=4d)"]["equity"] - row["3a(=4d)"]["arith"]),
                     row["4a"]["equity"] - row["3a(=4d)"]["equity"]), flush=True)
            print("    위험초과 3a %+.4f%%p · 4a %+.4f%%p · 자유현금 최솟값 3a %+.6f · 4a %+.6f"
                  % (row["3a(=4d)"]["overrun"], row["4a"]["overrun"],
                     row["3a(=4d)"]["cash_floor"], row["4a"]["cash_floor"]), flush=True)
            res["%s|%s" % (fname, rname)] = row
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "48-round4.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/48-round4.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
