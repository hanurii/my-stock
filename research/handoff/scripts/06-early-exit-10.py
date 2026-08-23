# -*- coding: utf-8 -*-
"""06 — 조기청산 대표 10변형 (페이지 주장 8).

지시서: research/handoff/tasks/06-early-exit-10.md (v2 개정 반영본)
슬롯5 정본: slot_sim.py — **④ reuse='nextday' · rng_mode='orderkey'**

사전등록된 10변형만 돌린다(추가 금지). 모두 원래 규칙(+20% / −10%)과 **병행**하고
먼저 닿는 쪽이 청산이다.

체결 모형이 셋 섞여 있다 (M9-17 — 바꾸지 않되 나란히 적는다):
  · 현행 +20/−10        → **닿은 날 종가**
  · 20일선 이탈·추적손절 → **다음날 시가** (장중 되돌림 룩어헤드 방지)
  · 시간컷              → **그날 종가**

부등호 고정 (2026-08-23 확정): 20일선 이탈은 **`종가 < ma20 − 1e-9`**.
OHLC 마지막 비트 오차(최대 2.2e-16)가 참·거짓을 뒤집지 못하게 한다.
차이가 1e-9 안에 든 날의 수를 결과에 싣는다.

유니버스: 12번 판(가)와 같은 **고정 진입 3,776키 · M1 적용**
(매수 당일 손절 터치·동시 접촉도 그날 종가 체결로 편입).
지시서 원문의 "확정 3,681건"만 쓴 판도 부가로 함께 낸다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/06-early-exit-10.py
난수 seed: 수준 0~199 · 짝비교 0~399 (고정)
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "grid", Path(__file__).resolve().parent / "12-exit-grid.py")
grid = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grid)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
N_LEVEL, N_PAIR = 200, 400
EPS = 1e-9
YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
SEGMENTS = [("2021", "2021-01-01", "2021-12-31"), ("2022", "2022-01-01", "2022-12-31"),
            ("2023", "2023-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
            ("2025~26", "2025-01-01", "2026-12-31")]

VARIANTS = [
    ("0", "현행 +20/−10", None, None),
    ("1", "20일선 이탈 → 익일 시가", "ma20", None),
    ("2", "5일차 −5% → 익일 시가", "day5", -5.0),
    ("3", "시간컷 10일 → 그날 종가", "timecut", 10),
    ("4", "시간컷 20일 → 그날 종가", "timecut", 20),
    ("5", "시간컷 30일 → 그날 종가", "timecut", 30),
    ("6", "추적손절 −8% → 익일 시가", "trail", 8.0),
    ("7", "추적손절 −10% → 익일 시가", "trail", 10.0),
    ("8", "추적손절 −12% → 익일 시가", "trail", 12.0),
    ("9", "추적손절 −15% → 익일 시가", "trail", 15.0),
    ("10", "추적손절 −20% → 익일 시가", "trail", 20.0),
]


def load_paths():
    P, year_last = {}, {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        last = ""
        for p in d["paths"]:
            last = max(last, p["dates"][-1])
            P[(p["scan_date"], p["code"], p["pattern"])] = {
                "code": p["code"], "pattern": p["pattern"], "scan_date": p["scan_date"],
                "entry_date": p["entry_date"], "entry_price": p["entry_price"],
                "year": y, "orig_result": p["orig_result"],
                "dates": p["dates"], "o": p["o"], "h": p["h"], "l": p["l"],
                "c": p["c"], "ma20": p["ma20"], "n": len(p["c"])}
        year_last[y] = last
    for p in P.values():
        p["vanished"] = p["dates"][-1] < year_last[p["year"]]
    print("경로 %d건 적재" % len(P), flush=True)
    return P


def label(reason, gain):
    """승/패 라벨 — 두뇌 세션 확정 규칙. 목표=승 · 손절/동시접촉=패 ·
    그 밖의 청산은 손익 부호(정확히 0.00%면 패)."""
    if reason == "target":
        return "win"
    if reason in ("stop", "both_same_day"):
        return "loss"
    return "win" if gain > 0 else "loss"


def simulate(p, kind, param, tie_counter=None):
    """원래 규칙 + 변형 하나를 함께 걸고 하루씩 걸어 결착시킨다."""
    e = p["entry_price"]
    T, S = e * (1 + TARGET / 100), e * (1 - STOP / 100)
    n = p["n"]
    o, h, l, c, ma = p["o"], p["h"], p["l"], p["c"], p["ma20"]
    pend = None                      # (익일 시가 청산 예약, 사유)
    runmax = -1e30
    for i in range(n):
        if pend is not None:         # 어제 신호 → 오늘 시가 청산
            return {"gain": (o[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": pend}
        hit_t = h[i] >= T
        hit_s = l[i] <= S
        if hit_t and hit_s:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "both_same_day"}
        if hit_t:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "target"}
        if hit_s:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "stop"}
        if c[i] > runmax:
            runmax = c[i]
        # ── 변형 (전부 종가 기준 신호) ──
        if kind == "timecut" and i >= param:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "timecut"}
        if kind == "ma20" and ma[i] is not None:
            if tie_counter is not None and abs(c[i] - ma[i]) <= EPS:
                tie_counter[0] += 1
            if c[i] < ma[i] - EPS:
                pend = "ma20"
        elif kind == "day5" and i == 5:
            if (c[i] / e - 1) * 100 <= param:
                pend = "day5"
        elif kind == "trail":
            if c[i] <= runmax * (1 - param / 100):
                pend = "trail"
    i = n - 1
    return {"gain": (c[i] / e - 1) * 100, "days": i,
            "resolve_date": p["dates"][i], "reason": "last_close"}


def build(P, kind, param, keys=None, tie_counter=None):
    out = []
    reasons = defaultdict(int)
    for k, p in P.items():
        if keys is not None and k not in keys:
            continue
        r = simulate(p, kind, param, tie_counter)
        reasons[r["reason"]] += 1
        out.append({"code": k[1], "pattern": k[2], "scan_date": k[0],
                    "entry_date": p["entry_date"], "resolve_date": r["resolve_date"],
                    "gain": r["gain"], "days": r["days"], "reason": r["reason"],
                    "result": label(r["reason"], r["gain"])})
    return out, dict(reasons)


def bh(pvals):
    """Benjamini-Hochberg FDR 보정값."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        v = min(prev, pvals[i] * m / (rank + 1))
        adj[i] = v
        prev = v
    return adj


def main():
    P = load_paths()
    all_dates = sorted({d for p in P.values() for d in p["dates"]})
    byday = grid.build_byday(P)
    cache = grid.build_order_cache(byday, N_PAIR)
    conf_keys = {k for k, p in P.items() if p["orig_result"] in ("win", "loss")}
    print("유니버스 3,776키 · 옛 확정 표본 %d키" % len(conf_keys), flush=True)

    res = {"n_universe": len(P), "n_confirmed_old": len(conf_keys),
           "n_level_runs": N_LEVEL, "n_pair_runs": N_PAIR, "eps": EPS, "runs": {}}

    for uname, keys in [("3,776키 · M1 적용 (주 판정)", None),
                        ("옛 확정 3,681키 (부가)", conf_keys)]:
        print("\n===== 유니버스: %s =====" % uname, flush=True)
        rows, base_eq, base_tr = {}, None, None
        for vid, vlabel, kind, param in VARIANTS:
            ties = [0]
            tr, reasons = build(P, kind, param, keys, ties if kind == "ma20" else None)
            r = grid.run_cell(tr, cache, byday, all_dates)
            if vid == "0":
                base_eq, base_tr = r["equities"], tr
            diffs = [r["equities"][i] - base_eq[i] for i in range(N_PAIR)]
            worse = sum(1 for x in diffs if x < 0) / N_PAIR
            dy = grid.drop_year_scan(tr, base_tr, cache, byday, all_dates)
            nets = [slot_sim.net(t["gain"]) for t in tr]
            rows[vid] = {
                "label": vlabel, "n": len(tr), "reasons": reasons,
                "ma20_ties_within_eps": ties[0] if kind == "ma20" else None,
                "win_rate": sum(1 for t in tr if t["result"] == "win") / len(tr) * 100,
                "mean_net": st.mean(nets),
                "median": r["median"], "p5": r["p5"], "p95": r["p95"],
                "median_drop5": r["median_drop5"],
                "sign_flips_on_drop5": r["sign_flips_on_drop5"],
                "drop_year": dy, "n_filled": r["n_filled"], "mdd": r["mdd"],
                "loss_streak": r["loss_streak"],
                "vs_base_win_pct": sum(1 for x in diffs if x > 0) / N_PAIR * 100,
                "vs_base_diff_median": st.median(diffs),
                "p_raw": worse if vid != "0" else None,
                "median_days": st.median([t["days"] for t in tr])}
            print("[%2s] %-26s n=%d 승률 %5.1f%% 거래당 %+6.3f%% | 슬롯5 중앙 %+7.1f%% "
                  "(상위5 %+7.1f%% · %s제거 %+7.1f%%%s) 우세율 %5.1f%% 체결 %4.0f"
                  % (vid, vlabel, len(tr), rows[vid]["win_rate"], rows[vid]["mean_net"],
                     r["median"], r["median_drop5"], dy["year_dropped"],
                     dy["median_without"],
                     " ⚠" if dy["sign_flips_on_drop_year"] else "",
                     rows[vid]["vs_base_win_pct"], r["n_filled"]), flush=True)
            if kind == "ma20":
                print("     20일선 부등호: |종가 − ma20| ≤ 1e-9 인 날 %d개" % ties[0],
                      flush=True)

        praw = [rows[v]["p_raw"] for v, _, _, _ in VARIANTS if v != "0"]
        padj = bh(praw)
        for (v, _, _, _), pa in zip([x for x in VARIANTS if x[0] != "0"], padj):
            rows[v]["p_bh"] = pa
        beat = [v for v in rows if v != "0" and rows[v]["p_bh"] < 0.10
                and rows[v]["vs_base_win_pct"] > 50]
        print("  BH 0.10 통과(현행보다 나음) 변형: %s" % (beat or "없음"), flush=True)

        # 구간별
        seg = {}
        for sname, lo, hi in SEGMENTS:
            skeys = {k for k, p in P.items()
                     if lo <= p["entry_date"] <= hi and (keys is None or k in keys)}
            sdates = sorted({d for k in skeys for d in P[k]["dates"]})
            sbyday = grid.build_byday({k: P[k] for k in skeys})
            scache = grid.build_order_cache(sbyday, N_PAIR)
            sbase = None
            srow = {}
            for vid, vlabel, kind, param in VARIANTS:
                tr, _ = build(P, kind, param, skeys)
                r = grid.run_cell(tr, scache, sbyday, sdates, drop5=False)
                if vid == "0":
                    sbase = r["equities"]
                d = [r["equities"][i] - sbase[i] for i in range(N_PAIR)]
                srow[vid] = {"win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
                             "median": r["median"], "n_filled": r["n_filled"]}
            seg[sname] = srow
            print("  구간 %s 완료 (기준선 체결 %.0f)" % (sname, srow["0"]["n_filled"]),
                  flush=True)
        res["runs"][uname] = {"variants": rows, "segments": seg}
        (OUT / "06-early-exit-10.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n저장: .cache/bt5y/out/06-early-exit-10.json")


if __name__ == "__main__":
    main()
