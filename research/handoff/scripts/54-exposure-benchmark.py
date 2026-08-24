# -*- coding: utf-8 -*-
"""54번 — **노출을 맞춘 벤치마크**. 사전등록: `tasks/54-exposure-benchmark.md`

S&P +102.48% 는 5.6년 내내 100% 투자된 값이고 우리는 손절이 나면 현금이다.
**같은 돈·같은 날·같은 비중을 우리 종목 대신 지수에 넣으면 얼마인가**를 잰다.
노출과 시점을 붙들어 두고 **선별만** 남긴다.

🚨 시뮬 산술은 `slot_sim_frac.sim_frac` 과 «같아야» 한다 — 달력을 늘린 것뿐이다.
   §5 관문이 비트 단위로 확인한다. 다르면 계산이 아니라 구현이 틀린 것이다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                               # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
from slot_sim import net, order_key                           # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
SLOTS = slot_sim.SLOTS


# ─────────────────────────────────────────────────────────────────────────
def sim_calendar(trades, cal, slots=SLOTS, seed=0, sizing="cash"):
    """`sf.sim_frac` 과 «같은» 산술을 **전 거래일 달력** 위에서 돈다.

    반환에 `expo`(날짜별 노출 비율)와 `daily`(날짜별 자산)가 추가된다.
    """
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda t: (t["code"], t.get("pattern", ""),
                                     t.get("scan_date", "")))

    ev_dates = set(list(byday) + [t["resolve_date"] for t in trades]
                   + [d for t in trades for d, _f, _g in t["legs"]])
    dates = sorted(set(cal) | ev_dates)
    calset = set(cal)

    eq, held, n = 1.0, [], 0
    nomw, arith = {}, [0.0]
    expo, daily = [], []

    def credit(items):
        nonlocal eq
        for _d, _c, wg, fr, g, _t in sorted(items, key=lambda x: (x[0], x[1])):
            eq += wg * fr * net(g) / 100
            arith[0] += nomw.get(id(_t), 0.0) * fr * net(g) / 100

    for d in dates:
        due = []
        for h in held:
            rest = []
            for leg in h[3]:
                if leg[0] < d:
                    due.append((leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1]))
                else:
                    rest.append(leg)
            h[3] = rest
        credit(due)
        done = [h for h in held if h[0] < d]
        held = [h for h in held if h[0] >= d]
        for _h in sorted(done, key=lambda x: (x[0], x[1]["code"])):
            assert not _h[3], "🚨 마지막 다리보다 늦은 다리가 남았다"
            n += 1

        free = slots - len(held)
        if d in byday and free > 0:
            open_w = sum(h[2] * sum(fr for _d2, fr, _g2 in h[3]) for h in held)
            per = (min(eq / slots, max(0.0, eq - open_w) / free) if sizing == "cash"
                   else eq / slots)
            if per > 0:
                c = sorted(byday[d], key=lambda t: order_key(seed, t))
                for t in c[:free]:
                    nomw[id(t)] = per / eq if eq > 0 else 0.0
                    held.append([t["resolve_date"], t, per, list(t["legs"])])

        if d in calset:                   # 달력 위에서만 노출·자산을 기록한다
            dep = sum(h[2] * sum(fr for _d2, fr, _g2 in h[3]) for h in held)
            expo.append((d, dep / eq if eq > 0 else 0.0))
            daily.append((d, eq))

    rest = [(leg[0], h[1]["code"], h[2], leg[1], leg[2], h[1])
            for h in held for leg in h[3]]
    credit(rest)
    n += len(held)
    return {"equity_pct": (eq - 1) * 100, "n_filled": n, "expo": expo, "daily": daily}


def mdd_of(series):
    peak, mdd = -1e18, 0.0
    for _d, v in series:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd * 100


def matched_bench(expo, spx):
    """같은 비중 일정으로 **지수를** 담는다. 현금 수익률 0."""
    beq, curve = 1.0, []
    for i in range(len(expo) - 1):
        d, w = expo[i]
        r = spx[expo[i + 1][0]] / spx[d] - 1
        beq *= 1 + w * r
        curve.append((expo[i + 1][0], beq))
    return (beq - 1) * 100, curve


def vol_sharpe(daily):
    rs = [daily[i + 1][1] / daily[i][1] - 1 for i in range(len(daily) - 1)
          if daily[i][1] > 0]
    if len(rs) < 2:
        return 0.0, 0.0
    m, s = st.mean(rs), st.pstdev(rs)
    return s * math.sqrt(252) * 100, (m / s * math.sqrt(252) if s else 0.0)


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    idx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))
    spx = idx["US500"]

    print("=" * 74, flush=True)
    print("54번 — **노출을 맞춘 벤치마크** (사전등록 tasks/54)", flush=True)
    print("=" * 74, flush=True)

    RES = {}
    for cname, ft, fs in (("종가판", "close", "close"),
                          ("실집행", "limit", "market")):
        r41.TARGET_FILL, r41.STOP_FILL = ft, fs
        for vname, fn, vlabel, _ht in r41.VARIANTS:
            if vname not in ("0회차", "1a"):
                continue
            ev, _blocked = r41.replay(by, fn)
            lo = min(e["entry_date"] for e in ev)
            hi = max((e["resolve_date"] or e["entry_date"]) for e in ev)
            cal = [d for d in sorted(spx) if lo <= d <= hi]
            if cname == "종가판" and vname == "0회차":
                print("\n창 %s ~ %s · 거래일 **%d일** · 진입 %d건"
                      % (lo, hi, len(cal), len(ev)), flush=True)
                print("S&P500 같은 창 **%+.2f%%** · 달력 MDD **%.2f%%**"
                      % ((spx[cal[-1]] / spx[cal[0]] - 1) * 100,
                         mdd_of([(d, spx[d]) for d in cal])), flush=True)

            for rname, fb, fsell in r41.REGIMES:
                with r41.Cost(fb, fsell):
                    if rname == r41.REGIMES[0][0]:
                        bad = []
                        for s in range(5):
                            a = sim_calendar(ev, cal, seed=s)["equity_pct"]
                            b = sf.sim_frac(ev, seed=s, sizing="cash")["equity_pct"]
                            if abs(a - b) > 1e-9:
                                bad.append((s, a, b))
                        if bad:
                            print("🚨 §5 관문 **미통과** %s" % bad[:3], flush=True)
                            return 3

                    rows = []
                    for s in range(N_SEED):
                        r = sim_calendar(ev, cal, seed=s)
                        bm, _bc = matched_bench(r["expo"], spx)
                        vol, shp = vol_sharpe(r["daily"])
                        rows.append({"eq": r["equity_pct"], "bm": bm,
                                     "gap": r["equity_pct"] - bm,
                                     "w": st.mean(w for _d, w in r["expo"]),
                                     "mdd": mdd_of(r["daily"]),
                                     "vol": vol, "sharpe": shp,
                                     "n": r["n_filled"]})
                    g = sorted(x["gap"] for x in rows)
                    key = "%s|%s|%s" % (cname, vname, rname)
                    RES[key] = {
                        "label": vlabel,
                        "equity_median": st.median(x["eq"] for x in rows),
                        "equity_p5": sorted(x["eq"] for x in rows)[int(N_SEED * .05)],
                        "bench_median": st.median(x["bm"] for x in rows),
                        "gap_median": st.median(g),
                        "gap_p5": g[int(N_SEED * .05)],
                        "gap_p95": g[int(N_SEED * .95)],
                        "gap_pos_pct": 100.0 * sum(1 for x in g if x > 0) / N_SEED,
                        "expo_mean": st.median(x["w"] for x in rows),
                        "mdd": st.median(x["mdd"] for x in rows),
                        "vol": st.median(x["vol"] for x in rows),
                        "sharpe": st.median(x["sharpe"] for x in rows),
                        "n_filled": st.median(x["n"] for x in rows),
                        "spx": (spx[cal[-1]] / spx[cal[0]] - 1) * 100,
                        "spx_mdd": mdd_of([(d, spx[d]) for d in cal])}
                    a = RES[key]
                    print("\n[%s · %s · %s] %s" % (cname, vname, rname, vlabel),
                          flush=True)
                    print("  평균 노출 **%.1f%%** · 체결 %d건 · 달력 MDD **%.2f%%** "
                          "(S&P %.2f%%)" % (a["expo_mean"] * 100, a["n_filled"],
                                            a["mdd"], a["spx_mdd"]), flush=True)
                    print("  자산 중앙 %+.2f%% (하단 %+.2f%%)  vs  "
                          "**노출맞춤 S&P %+.2f%%**"
                          % (a["equity_median"], a["equity_p5"], a["bench_median"]),
                          flush=True)
                    print("  → 짝비교 격차 중앙 **%+.2f%%p** "
                          "[5%% %+.2f · 95%% %+.2f] · 양수 seed **%.1f%%**"
                          % (a["gap_median"], a["gap_p5"], a["gap_p95"],
                             a["gap_pos_pct"]), flush=True)
                    print("  변동성 %.1f%% · Sharpe %.2f" % (a["vol"], a["sharpe"]),
                          flush=True)

    (OUT / "54-exposure-benchmark.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 54-exposure-benchmark.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
