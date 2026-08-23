# -*- coding: utf-8 -*-
"""12 (1~4단계) — 청산 격자 24칸 · (i) 고정 진입 유니버스.

지시서: research/handoff/tasks/12-exit-grid.md (v2) · 개정 v2 M1·M2·M4·M9-5
        + 두뇌 세션 추가(2-1 unresolved 사유 분리 · 2-2 피벗 ±0.005 취약성)
슬롯5 정본: research/handoff/scripts/slot_sim.py
  · **reuse='nextday' (④)** — 슬롯도 손익도 다음 거래일부터. ⑤는 민감도로만.
  · **rng_mode='orderkey'** — 후보 순서를 거래별 정렬키로 정한다. 날짜 전체를 섞으면
    후보가 1건만 빠져도 남은 거래의 상대 순서가 달라져 짝비교가 깨진다.
  · 자산곡선 **수준**은 인용 금지 — 모든 칸에 **상위 5건 제거 시 값**을 함께 낸다.

유니버스는 현행 +20/-10 의 진입 **3,776키를 전 칸이 공유**한다(고정 진입 판).
칸마다 바뀌는 것은 청산뿐이다.

매수 당일 손절 터치 세 판 (M1)
------------------------------
  갭업 진입(gap_up_pct > 0)은 시가에 샀으니 그날 저가가 확실히 진입 후다.
    · 손절만 터치 → **손절 확정 손실** (ambiguous 아님 — 오류 수정)
    · 목표·손절 둘 다 터치 → 둘 다 진입 후지만 순서를 모른다 → ambiguous (그대로)
  장중 진입(gap_up_pct == 0)은 저가가 진입 전인지 모른다.
    · (가) 손절 확정 손실로 **포함**
    · (나) 표본에서 **제외** (옛 방식)
    · (다) **교집합** — 24칸 중 어느 한 칸에서라도 (나)에서 제외되는 키를
           **전 칸에서** 뺀 표본. (다)에서는 (가)와 (나)가 같아진다.

미결(unresolved) 처리 — 두뇌 세션 추가 2-1
------------------------------------------
  ① **종목 소멸** : 그 종목 시계열이 구간 끝보다 먼저 끝났다(상장폐지·합병·거래정지).
  ② **구간 끝**   : 자료 마지막 날까지 목표·손절 어디도 안 닿았다.
  주 판정 = 둘 다 **마지막 종가 청산**. 부가 민감도 두 판(①에만 적용):
    (ㄱ) 손절가 청산  (ㄴ) 표본 제외

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12-exit-grid.py
난수 seed: 수준 추정 0~199 · 짝비교 0~399 (고정)
"""
from __future__ import annotations

import bisect
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"

TARGETS = [15, 20, 25, 30, 40, 50]
STOPS = [5, 7, 10, 12]
BASE_CELL = (20, 10)
N_LEVEL = 200
N_PAIR = 400
SLOTS = 5
REUSE = "nextday"                 # 정본 ④
SLIPS = [0.0, 0.5, 1.0, "cond"]   # 손절 쪽에만. 'cond' = 거래대금 하위20%에만 1.0%p
PIVOT_EPS = 0.005                 # 이벤트 pivot 이 소수 둘째 자리 반올림이라 그 절반


# ── 1) 경로 적재 ──────────────────────────────────────────────────────────

def load_paths():
    P = {}
    year_last = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        last = ""
        for p in d["paths"]:
            h, l = p["h"], p["l"]
            rmax, rmin = [], []
            mh, ml = -1e30, 1e30
            for i in range(len(h)):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rmin.append(-ml)          # 부호를 뒤집어 두 배열 모두 비감소 → bisect
            last = max(last, p["dates"][-1])
            P[(p["scan_date"], p["code"], p["pattern"])] = {
                "code": p["code"], "pattern": p["pattern"], "scan_date": p["scan_date"],
                "entry_date": p["entry_date"], "entry_price": p["entry_price"],
                "gap_up": p["gap_up_pct"] > 0, "year": y,
                "end_date": p["dates"][-1], "dates": p["dates"], "c": p["c"],
                "rmax": rmax, "rmin_neg": rmin, "n": len(h),
            }
        year_last[y] = last
        print("  경로 %d년 적재 · 누적 %d · 시계열 끝 %s" % (y, len(P), last), flush=True)
    # 종목 소멸 = 그 해 시계열 끝보다 먼저 끊긴 경로
    n_van = 0
    for p in P.values():
        p["vanished"] = p["end_date"] < year_last[p["year"]]
        n_van += p["vanished"]
    print("  종목 소멸(시계열 조기 종료) %d건" % n_van, flush=True)
    return P, year_last


def load_turnover():
    tv = {}
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            tv[(e["scan_date"], e["code"], e["pattern"])] = e.get("turnover_eok") or 0.0
    return tv


# ── 2) 칸별 결과 ─────────────────────────────────────────────────────────

def outcome(p, tgt, stp, plan, unres="last_close", eps=0.0):
    """한 거래 · 한 칸의 결과. 반환 None = 그 칸 표본에서 빠짐.

    plan  : 'ga' | 'na'   (매수 당일 장중진입 손절 터치 처리)
    unres : 'last_close' (주 판정) | 'stop' (ㄱ) | 'drop' (ㄴ) — ①종목 소멸에만 적용
    eps   : 매수가 흔들기(피벗 반올림 취약성 점검). 갭업 진입은 시가라 흔들지 않는다.
    """
    e = p["entry_price"] + (0.0 if p["gap_up"] else eps)
    T = e * (1 + tgt / 100)
    S = e * (1 - stp / 100)
    n = p["n"]
    ti = bisect.bisect_left(p["rmax"], T)
    si = bisect.bisect_left(p["rmin_neg"], -S)
    ti = ti if ti < n else None
    si = si if si < n else None

    def mk(kind, reason, i):
        return {"result": kind, "exit_reason": reason, "days_held": i,
                "gain": (p["c"][i] / e - 1) * 100, "resolve_date": p["dates"][i]}

    if ti is None and si is None:
        i = n - 1
        if p["vanished"] and unres != "last_close":
            if unres == "drop":
                return None
            g = -stp                                   # (ㄱ) 손절가 청산
            return {"result": "loss", "exit_reason": "stop", "days_held": i,
                    "gain": g, "resolve_date": p["dates"][i]}
        g = (p["c"][i] / e - 1) * 100
        return {"result": "win" if g > 0 else "loss",
                "exit_reason": "last_close_vanished" if p["vanished"] else "last_close",
                "days_held": i, "gain": g, "resolve_date": p["dates"][i]}
    if ti is not None and (si is None or ti < si):
        return mk("win", "target", ti)
    if si is not None and (ti is None or si < ti):
        if si == 0 and not p["gap_up"] and plan == "na":
            return None                                # (나) 표본에서 제외
        return mk("loss", "stop", si)                  # 갭업이면 M1-1 오류 수정 포함
    return None                                        # 같은 날 둘 다 터치


def cell_trades(P, tgt, stp, plan, keys=None, slip=0.0, low_tv=None,
                unres="last_close"):
    out = []
    s = {"n": 0, "n_ambiguous": 0, "n_stop": 0, "n_day0_stop": 0,
         "n_target": 0, "n_last_close": 0, "n_unres_vanished": 0,
         "n_unres_windowend": 0, "n_dropped_vanished": 0}
    for k, p in P.items():
        if keys is not None and k not in keys:
            continue
        r = outcome(p, tgt, stp, plan, unres)
        if r is None:
            if (unres == "drop" and p["vanished"]
                    and outcome(p, tgt, stp, plan, "last_close") is not None):
                s["n_dropped_vanished"] += 1
            else:
                s["n_ambiguous"] += 1
            continue
        g = r["gain"]
        rea = r["exit_reason"]
        if rea == "stop":
            s["n_stop"] += 1
            if r["days_held"] == 0:
                s["n_day0_stop"] += 1
            g -= slip if (low_tv is None or k in low_tv) else 0.0
        elif rea == "target":
            s["n_target"] += 1
        else:
            s["n_last_close"] += 1
            if rea == "last_close_vanished":
                s["n_unres_vanished"] += 1
            else:
                s["n_unres_windowend"] += 1
        out.append({"code": p["code"], "pattern": p["pattern"],
                    "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                    "resolve_date": r["resolve_date"], "gain": g,
                    "result": r["result"], "days_held": r["days_held"]})
    s["n"] = len(out)
    return out, s


def pivot_fragility(P, tgt, stp, plan, keys=None):
    """매수가를 ±0.005 흔들었을 때 판정(result·days_held)이 바뀌는 건수."""
    n = 0
    for k, p in P.items():
        if keys is not None and k not in keys:
            continue
        if p["gap_up"]:
            continue                       # 시가 체결이라 반올림 취약성 없음
        base = outcome(p, tgt, stp, plan)
        for eps in (PIVOT_EPS, -PIVOT_EPS):
            r = outcome(p, tgt, stp, plan, eps=eps)
            if (r is None) != (base is None) or (
                    r is not None and base is not None
                    and (r["result"], r["days_held"]) != (base["result"], base["days_held"])):
                n += 1
                break
    return n


# ── 3) 빠른 슬롯5 (고정 유니버스라 날짜별 후보 순서를 seed마다 한 번만 만든다) ──

def build_byday(P):
    """진입일별 후보 키. 기준 순서는 정본 slot_sim._byday 와 같은 (code, pattern, scan_date)."""
    byday = defaultdict(list)
    for k, p in P.items():
        byday[p["entry_date"]].append(k)
    for d in byday:
        byday[d].sort(key=lambda k: (k[1], k[2], k[0]))
    return dict(byday)


def build_order_cache(byday, n_seeds):
    """seed × 날짜 → 그날 후보 순서 (거래별 정렬키).

    ★ 거래마다 자기 난수를 가지므로 **후보가 빠져도 남은 거래의 상대 순서가 유지**된다.
      그래서 전체 유니버스로 한 번 정렬해 두고 칸마다 거르기만 하면 되고,
      그 결과가 정본 slot_sim(rng_mode='orderkey')과 정확히 같다.
    """
    return [{d: sorted(ks, key=lambda k: slot_sim.order_key(
        s, {"code": k[1], "scan_date": k[0], "pattern": k[2]}))
        for d, ks in byday.items()} for s in range(n_seeds)]


def fast_sim(tmap, seed, cache, byday, all_dates, slots=SLOTS,
             cash_today=False):
    """정본 ④ — 결착분은 그날 슬롯을 계속 차지하고 손익도 다음 거래일에 반영.
    cash_today=True 면 ⑤(손익만 결착일 반영) 민감도."""
    order_day = cache[seed]
    eq = 1.0
    held = []                       # [resolve_date, key, weight, credited]
    n = w = 0
    peak, mdd = 1.0, 0.0
    streak = best = 0
    net = slot_sim.net
    for d in all_dates:
        if held:
            for h in held:
                if h[3] or (h[0] > d if cash_today else h[0] >= d):
                    continue
                t = tmap[h[1]]
                eq += h[2] * net(t["gain"]) / 100
                n += 1
                iw = t["result"] == "win"
                w += iw
                streak = 0 if iw else streak + 1
                if streak > best:
                    best = streak
                h[3] = True
            held = [h for h in held if h[0] >= d]
        free = slots - len(held)
        if free > 0:
            ks = order_day.get(d)
            if ks:
                wgt = eq / slots
                for k in ks:
                    t = tmap.get(k)
                    if t is not None:
                        held.append([t["resolve_date"], k, wgt, False])
                        free -= 1
                        if free == 0:
                            break
        if eq > peak:
            peak = eq
        v = eq / peak - 1
        if v < mdd:
            mdd = v
    for h in held:
        if not h[3]:
            t = tmap[h[1]]
            eq += h[2] * net(t["gain"]) / 100
            n += 1
            iw = t["result"] == "win"
            w += iw
            streak = 0 if iw else streak + 1
            if streak > best:
                best = streak
    if eq > peak:
        peak = eq
    mdd = min(mdd, eq / peak - 1)
    return (eq - 1) * 100, n, (w / n * 100 if n else 0.0), mdd * 100, best


def drop_top(trades, k=5):
    """순수익 상위 k건 제거 (집중도 — 개정 3-1)."""
    idx = set(sorted(range(len(trades)),
                     key=lambda i: -slot_sim.net(trades[i]["gain"]))[:k])
    return [t for i, t in enumerate(trades) if i not in idx]


def run_cell(trades, cache, byday, all_dates, cash_today=False, drop5=True):
    """짝비교용 400 seed. 수준 추정(중앙·5~95%)은 사전등록대로 앞 200 seed 만.
    drop5=True 면 순수익 상위 5건을 뺀 표본의 중앙값도 함께 낸다."""
    tmap = {(t["scan_date"], t["code"], t["pattern"]): t for t in trades}
    rs = [fast_sim(tmap, s, cache, byday, all_dates, cash_today=cash_today)
          for s in range(N_PAIR)]
    lv = rs[:N_LEVEL]
    eqs = sorted(r[0] for r in lv)
    return {"equities": [r[0] for r in rs],
            "median": st.median(eqs), "p5": eqs[N_LEVEL // 20 - 1],
            "p95": eqs[N_LEVEL - N_LEVEL // 20],
            "n_filled": st.median(r[1] for r in lv),
            "slot5_win": st.median(r[2] for r in lv),
            "mdd": st.median(r[3] for r in lv),
            "loss_streak": st.median(r[4] for r in lv),
            **_drop5(trades, cache, byday, all_dates, cash_today, st.median(
                sorted(r[0] for r in lv)) if drop5 else None, drop5)}


def _drop5(trades, cache, byday, all_dates, cash_today, med, on):
    if not on:
        return {}
    t5 = drop_top(trades, 5)
    tm = {(t["scan_date"], t["code"], t["pattern"]): t for t in t5}
    eqs = sorted(fast_sim(tm, s, cache, byday, all_dates, cash_today=cash_today)[0]
                 for s in range(N_LEVEL))
    m5 = st.median(eqs)
    return {"median_drop5": m5,
            "sign_flips_on_drop5": (med is not None) and ((med > 0) != (m5 > 0))}


def yearly_net(trades):
    """칸의 연도별 거래당 순수익 — 우위가 한 해에 몰려 있는지 보기 위한 것."""
    by = defaultdict(list)
    for t in trades:
        by[t["scan_date"][:4]].append(slot_sim.net(t["gain"]))
    return {y: {"n": len(v), "mean_net": st.mean(v)} for y, v in sorted(by.items())}


def drop_year_scan(trades, base_trades, cache, byday, all_dates, n=N_LEVEL):
    """연도 하나씩 빼 보고 **자산곡선 중앙이 가장 크게 떨어지는 해**를 찾는다.

    14번에서 ①vs②의 +0.84%p가 통째로 2021 한 해였던 것과 같은 검사다.
    반환: 최악 연도 · 그때의 중앙값 · 기준선 대비 우세율 · 부호가 뒤집혔는지.
    """
    years = sorted({t["scan_date"][:4] for t in trades})
    full = st.median(sorted(
        fast_sim({(t["scan_date"], t["code"], t["pattern"]): t for t in trades},
                 s, cache, byday, all_dates)[0] for s in range(n)))
    worst = None
    for y in years:
        sub = [t for t in trades if t["scan_date"][:4] != y]
        bsub = [t for t in base_trades if t["scan_date"][:4] != y]
        tm = {(t["scan_date"], t["code"], t["pattern"]): t for t in sub}
        bm = {(t["scan_date"], t["code"], t["pattern"]): t for t in bsub}
        eq = [fast_sim(tm, s, cache, byday, all_dates)[0] for s in range(n)]
        be = [fast_sim(bm, s, cache, byday, all_dates)[0] for s in range(n)]
        med = st.median(sorted(eq))
        win = sum(1 for i in range(n) if eq[i] > be[i]) / n * 100
        if worst is None or med < worst["median_without"]:
            worst = {"year_dropped": y, "median_without": med,
                     "vs_base_win_pct_without": win}
    worst["median_full"] = full
    worst["sign_flips_on_drop_year"] = (full > 0) != (worst["median_without"] > 0)
    return worst


def per_trade_stats(trades):
    nets = [slot_sim.net(t["gain"]) for t in trades]
    wins = [x for x in nets if x > 0]
    loss = [x for x in nets if x <= 0]
    wr = len(wins) / len(nets) * 100 if nets else 0.0
    be = (abs(st.mean(loss)) / (st.mean(wins) + abs(st.mean(loss))) * 100
          if wins and loss else None)
    return {"trade_win_rate": wr, "breakeven": be,
            "edge": (wr - be) if be is not None else None,
            "mean_net": st.mean(nets) if nets else 0.0}


def compare(r, base):
    d = [r["equities"][i] - base["equities"][i] for i in range(N_PAIR)]
    ds = sorted(d)
    return {"vs_base_win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
            "vs_base_diff_median": st.median(d),
            "vs_base_diff_p5": ds[N_PAIR // 20 - 1],
            "vs_base_diff_p95": ds[N_PAIR - N_PAIR // 20]}


def main():
    print("경로 적재 …", flush=True)
    P, year_last = load_paths()
    tv = load_turnover()
    vals = sorted((tv.get(k, 0.0), k) for k in P)
    cut = int(len(vals) * 0.2)
    low_tv = {k for _, k in vals[:cut]}
    print("거래 %d건 · 거래대금 하위20%% %d건 (경계 %.2f억)"
          % (len(P), len(low_tv), vals[cut - 1][0]), flush=True)

    all_dates = sorted({d for p in P.values() for d in p["dates"]})
    print("달력 %d일 (%s ~ %s)" % (len(all_dates), all_dates[0], all_dates[-1]), flush=True)

    drop = {k for k, p in P.items()
            for tg in TARGETS for sp in STOPS
            if outcome(p, tg, sp, "na") is None}
    inter_keys = set(P) - drop
    print("(다) 교집합 표본 %d건 (제외 %d)" % (len(inter_keys), len(drop)), flush=True)

    print("후보 순서 캐시 %d seed …" % N_PAIR, flush=True)
    byday = build_byday(P)
    cache = build_order_cache(byday, N_PAIR)

    tr0, _ = cell_trades(P, 20, 10, "na")
    tm0 = {(t["scan_date"], t["code"], t["pattern"]): t for t in tr0}
    a = fast_sim(tm0, 0, cache, byday, all_dates)[0]
    b = slot_sim.sim(tr0, seed=0, rng_mode="orderkey", reuse=REUSE)["equity_pct"]
    print("정합성 fast_sim vs slot_sim 정본: %.10f vs %.10f (차 %.2e)"
          % (a, b, abs(a - b)), flush=True)

    PLANS = [("가", "ga", None), ("나", "na", None), ("다", "na", inter_keys)]
    res = {"n_universe": len(P), "n_intersection": len(inter_keys),
           "n_vanished": sum(1 for p in P.values() if p["vanished"]),
           "series_end_by_year": year_last, "reuse": REUSE,
           "consistency": {"fast": a, "canon": b, "diff": abs(a - b)},
           "n_level_runs": N_LEVEL, "n_pair_runs": N_PAIR,
           "low_turnover_cut_eok": vals[cut - 1][0], "plans": {}}

    for pname, plan, keys in PLANS:
        res["plans"][pname] = {}
        for slip in SLIPS:
            sl = 1.0 if slip == "cond" else slip
            lt = low_tv if slip == "cond" else None
            btr, bst = cell_trades(P, *BASE_CELL, plan, keys, sl, lt)
            bres = run_cell(btr, cache, byday, all_dates)
            tab = {"_base": {k: v for k, v in bres.items() if k != "equities"} |
                   bst | per_trade_stats(btr)}
            for tg in TARGETS:
                for sp in STOPS:
                    tr, stt = cell_trades(P, tg, sp, plan, keys, sl, lt)
                    r = run_cell(tr, cache, byday, all_dates)
                    row = {"target": tg, "stop": sp}
                    row |= stt
                    row |= per_trade_stats(tr)
                    row |= {k: v for k, v in r.items() if k != "equities"}
                    row |= compare(r, bres)
                    row["stop_share"] = (stt["n_stop"] / stt["n"] * 100) if stt["n"] else 0.0
                    if slip == 0.0:
                        row["pivot_fragile"] = pivot_fragility(P, tg, sp, plan, keys)
                        row["yearly"] = yearly_net(tr)
                        row["drop_year"] = drop_year_scan(tr, btr, cache, byday,
                                                          all_dates)
                    tab["t%ds%d" % (tg, sp)] = row
            res["plans"][pname][str(slip)] = tab
            print("[판 %s · 슬립 %s] 기준선 중앙 %+.1f%% · 확정 %d"
                  % (pname, slip, bres["median"], bst["n"]), flush=True)
            (OUT / "12-exit-grid.json").write_text(
                json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 미결 민감도 (ㄱ)(ㄴ) — 상위 3칸 + 기준선, 슬립 0, 세 판 ──
    top = sorted(((v["median"], k) for k, v in res["plans"]["가"]["0.0"].items()
                  if k != "_base"), reverse=True)[:3]
    res["top3_by_plan_ga"] = [k for _, k in top]
    sens = {}
    for pname, plan, keys in PLANS:
        for unres in ("stop", "drop"):
            btr, bst = cell_trades(P, *BASE_CELL, plan, keys, 0.0, None, unres)
            bres = run_cell(btr, cache, byday, all_dates)
            row = {"_base": {"median": bres["median"], "p5": bres["p5"],
                             "p95": bres["p95"], "n": bst["n"],
                             "n_dropped_vanished": bst["n_dropped_vanished"]}}
            for _, key in top:
                tg, sp = int(key[1:key.index("s")]), int(key[key.index("s") + 1:])
                tr, stt = cell_trades(P, tg, sp, plan, keys, 0.0, None, unres)
                r = run_cell(tr, cache, byday, all_dates)
                row[key] = {"median": r["median"], "p5": r["p5"], "p95": r["p95"],
                            "n": stt["n"],
                            "n_dropped_vanished": stt["n_dropped_vanished"],
                            **compare(r, bres)}
            sens["%s/%s" % (pname, unres)] = row
            print("[민감도 판 %s · 미결 %s] 기준선 중앙 %+.1f%%"
                  % (pname, unres, bres["median"]), flush=True)
    res["unresolved_sensitivity"] = sens

    # ── ⑤ 민감도 (손익만 결착일 반영) — 상위 3칸 + 기준선, 슬립 0, 세 판 ──
    five = {}
    for pname, plan, keys in PLANS:
        btr, _ = cell_trades(P, *BASE_CELL, plan, keys)
        bres = run_cell(btr, cache, byday, all_dates, cash_today=True)
        row = {"_base": {k: v for k, v in bres.items() if k != "equities"}}
        for _, key in top:
            tg, sp = int(key[1:key.index("s")]), int(key[key.index("s") + 1:])
            tr, _st2 = cell_trades(P, tg, sp, plan, keys)
            r = run_cell(tr, cache, byday, all_dates, cash_today=True)
            row[key] = {**{k: v for k, v in r.items() if k != "equities"},
                        **compare(r, bres)}
        five["%s/⑤" % pname] = row
        print("[⑤민감도 판 %s] 기준선 중앙 %+.1f%%" % (pname, bres["median"]), flush=True)
    res["cash_today_sensitivity"] = five
    (OUT / "12-exit-grid.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12-exit-grid.json")


if __name__ == "__main__":
    main()
