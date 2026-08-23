# -*- coding: utf-8 -*-
"""15 — "5일차 −5% 청산"만 따로, 자료 기반 부트스트랩으로.

지시서: research/handoff/tasks/15-variant2-followup.md

질문 하나: **"매수 후 5거래일째 종가가 −5% 이하면 다음날 시가에 판다"는 규칙이
자료가 달랐어도 현행보다 나았을 것인가?**

불확실성의 원천을 **seed 가 아니라 자료**로 바꾼다 —
연속 20~40거래일 블록으로 진입일 축을 복원추출(1,000회), 복제마다 현행과 변형 2를
**같은 복제 자료·같은 seed**로 계산해 **차이**를 기록한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/15-variant2-followup.py
난수 seed: 부트스트랩 블록 추출 20000 · 슬롯 순서 seed 0 (부가 판 0~4) · 최악연도 0~199
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

import importlib.util  # noqa: E402


def _load(name, fname):
    sp = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / fname)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


grid = _load("grid", "12-exit-grid.py")
e6 = _load("e6", "06-early-exit-10.py")

OUT = ROOT / ".cache" / "bt5y" / "out"
N_BOOT = 1000
BOOT_SEED = 20000
BLOCK_MIN, BLOCK_MAX = 20, 40
N_LEVEL = 200
SLIP = 0.5
RUN_NEIGHBORS = False      # 이웃 일차는 15b-neighbor-days.py 로 분리(메모리)
DAYS = [3, 4, 5, 6, 7]
SEGMENTS = [("2021", "2021-01-01", "2021-12-31"), ("2022", "2022-01-01", "2022-12-31"),
            ("2023", "2023-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
            ("2025~26", "2025-01-01", "2026-12-31")]
net = slot_sim.net


def boot_sim(by_pos, n_pos, seed, slots=5):
    """새 시간축(정수 위치) 위의 슬롯5 — 정본 ④."""
    eq = 1.0
    held = []
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * net(h[1]["gain"]) / 100
                    h[3] = True
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0:
            c = by_pos.get(p)
            if c:
                if len(c) > 1:
                    c = sorted(c, key=lambda t: slot_sim.order_key(seed, t))
                wgt = eq / slots
                for t in c[:free]:
                    held.append([p + t["days"], t, wgt, False])
    for h in held:
        if not h[3]:
            eq += h[2] * net(h[1]["gain"]) / 100
    return (eq - 1) * 100


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def index_by_pos(trades, pos_of):
    d = defaultdict(list)
    for t in trades:
        d[pos_of[t["entry_date"]]].append(t)
    return d


def bootstrap(arms, pos_of, n_pos, seeds=(0,), n_boot=N_BOOT, seed0=BOOT_SEED):
    """arms = {이름: 거래목록}. 복제마다 모든 팔을 같은 블록·같은 seed로 계산."""
    idx = {k: index_by_pos(v, pos_of) for k, v in arms.items()}
    rnd = random.Random(seed0)
    out = {k: [] for k in arms}
    for _ in range(n_boot):
        blocks = make_blocks(rnd, n_pos)
        for k in arms:
            by_pos = defaultdict(list)
            off = 0
            for a, L in blocks:
                src = idx[k]
                for j in range(L):
                    ts = src.get(a + j)
                    if ts:
                        by_pos[off + j].extend(ts)
                off += L
            vals = [boot_sim(by_pos, n_pos, s) for s in seeds]
            out[k].append(st.mean(vals))
    return out


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    n = len(s)
    return s[int(n * lo / 100)], s[int(n * hi / 100) - 1]


def apply_slip(trades, reason, pct):
    out = []
    for t in trades:
        u = dict(t)
        if u["reason"] == reason:
            u["gain"] = u["gain"] - pct
        out.append(u)
    return out


def main():
    P = e6.load_paths()
    all_dates = sorted({d for p in P.values() for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)
    byday = grid.build_byday(P)
    cache = grid.build_order_cache(byday, grid.N_PAIR)   # run_cell 이 400 seed 를 쓴다

    base, base_reasons = e6.build(P, None, None)

    def build_dayN(dday):
        out = []
        for k, p in P.items():
            r = simulate_dayN(p, dday)
            out.append({"code": k[1], "pattern": k[2], "scan_date": k[0],
                        "entry_date": p["entry_date"], "resolve_date": r["resolve_date"],
                        "gain": r["gain"], "days": r["days"], "reason": r["reason"],
                        "result": e6.label(r["reason"], r["gain"])})
        return out

    def simulate_dayN(p, dday):
        e = p["entry_price"]
        T, S = e * 1.2, e * 0.9
        n = p["n"]
        o, h, l, c = p["o"], p["h"], p["l"], p["c"]
        pend = None
        for i in range(n):
            if pend is not None:
                return {"gain": (o[i] / e - 1) * 100, "days": i,
                        "resolve_date": p["dates"][i], "reason": "dayN"}
            hit_t, hit_s = h[i] >= T, l[i] <= S
            if hit_t and hit_s:
                return {"gain": (c[i] / e - 1) * 100, "days": i,
                        "resolve_date": p["dates"][i], "reason": "both_same_day"}
            if hit_t:
                return {"gain": (c[i] / e - 1) * 100, "days": i,
                        "resolve_date": p["dates"][i], "reason": "target"}
            if hit_s:
                return {"gain": (c[i] / e - 1) * 100, "days": i,
                        "resolve_date": p["dates"][i], "reason": "stop"}
            if i == dday and (c[i] / e - 1) * 100 <= -5.0:
                pend = "dayN"
        i = n - 1
        return {"gain": (c[i] / e - 1) * 100, "days": i,
                "resolve_date": p["dates"][i], "reason": "last_close"}

    arms_days = {("%d일차" % dd): build_dayN(dd) for dd in DAYS}
    v2 = arms_days["5일차"]
    print("현행 %d건 · 변형2(5일차) %d건" % (len(base), len(v2)), flush=True)

    # ── 규칙이 실제로 무엇을 하는가 ──
    bm = {(t["scan_date"], t["code"], t["pattern"]): t for t in base}
    fired = [t for t in v2 if t["reason"] == "dayN"]
    orig = Counter(bm[(t["scan_date"], t["code"], t["pattern"])]["reason"] for t in fired)
    by_year = Counter(t["scan_date"][:4] for t in fired)
    gain_delta = [t["gain"] - bm[(t["scan_date"], t["code"], t["pattern"])]["gain"]
                  for t in fired]
    print("발동 %d건 (%.1f%%) · 원래 결과 %s" % (len(fired), len(fired) / len(v2) * 100,
                                                dict(orig)), flush=True)
    print("  연도별 발동: %s" % dict(sorted(by_year.items())), flush=True)
    print("  발동 건 손익 변화 합계 %+.1f%%p · 중앙 %+.2f%%p · 버린 승자(원래 목표도달) %d건"
          % (sum(gain_delta), st.median(gain_delta), orig.get("target", 0)), flush=True)
    fired_days = Counter(bm[(t["scan_date"], t["code"], t["pattern"])]["days"]
                         for t in fired)
    res = {"n_universe": len(P), "n_fired": len(fired),
           "fired_original_reason": dict(orig), "fired_by_year": dict(sorted(by_year.items())),
           "fired_gain_delta_sum": sum(gain_delta),
           "fired_gain_delta_median": st.median(gain_delta),
           "abandoned_winners": orig.get("target", 0),
           "fired_original_days_held": dict(sorted(fired_days.items()))}

    # ── 문턱 1: 부트스트랩 차이 95% 구간 ──
    print("\n[문턱1] 블록 부트스트랩 %d회 (seed 고정 0) …" % N_BOOT, flush=True)
    bs = bootstrap({"base": base, "v2": v2}, pos_of, n_pos, seeds=(0,))
    diff = [bs["v2"][i] - bs["base"][i] for i in range(N_BOOT)]
    lo, hi = ci(diff)
    print("  차이 중앙 %+.2f%%p · 95%% 구간 %+.2f ~ %+.2f · 0 제외? %s · 양수 비율 %.1f%%"
          % (st.median(diff), lo, hi, "예" if lo > 0 or hi < 0 else "아니오",
             sum(1 for x in diff if x > 0) / N_BOOT * 100), flush=True)
    res["boot_main"] = {"diff_median": st.median(diff), "ci_lo": lo, "ci_hi": hi,
                        "excludes_zero": bool(lo > 0 or hi < 0),
                        "pct_positive": sum(1 for x in diff if x > 0) / N_BOOT * 100,
                        "base_median": st.median(bs["base"]),
                        "v2_median": st.median(bs["v2"])}

    bs5 = bootstrap({"base": base, "v2": v2}, pos_of, n_pos, seeds=(0, 1, 2, 3, 4))
    d5 = [bs5["v2"][i] - bs5["base"][i] for i in range(N_BOOT)]
    l5, h5 = ci(d5)
    print("  (부가) seed 5개 평균: 차이 중앙 %+.2f%%p · 95%% 구간 %+.2f ~ %+.2f"
          % (st.median(d5), l5, h5), flush=True)
    res["boot_seed5"] = {"diff_median": st.median(d5), "ci_lo": l5, "ci_hi": h5,
                         "excludes_zero": bool(l5 > 0 or h5 < 0)}

    # ── 문턱 2: 구간 5/5 ──
    print("[문턱2] 구간별 부트스트랩 …", flush=True)
    segs = {}
    for sname, slo, shi in SEGMENTS:
        skeys = {k for k, p in P.items() if slo <= p["entry_date"] <= shi}
        sdates = sorted({d for k in skeys for d in P[k]["dates"]})
        spos = {d: i for i, d in enumerate(sdates)}
        sb = [t for t in base if (t["scan_date"], t["code"], t["pattern"]) in skeys]
        sv = [t for t in v2 if (t["scan_date"], t["code"], t["pattern"]) in skeys]
        r = bootstrap({"base": sb, "v2": sv}, spos, len(sdates), seeds=(0,))
        dd = [r["v2"][i] - r["base"][i] for i in range(N_BOOT)]
        a, b = ci(dd)
        segs[sname] = {"n": len(sv), "diff_median": st.median(dd), "ci_lo": a, "ci_hi": b,
                       "pct_positive": sum(1 for x in dd if x > 0) / N_BOOT * 100}
        print("  %s n=%d 차이 중앙 %+.2f%%p (95%% %+.2f ~ %+.2f) 양수 %.1f%%"
              % (sname, len(sv), st.median(dd), a, b, segs[sname]["pct_positive"]),
              flush=True)
    res["segments"] = segs
    res["segment_signs"] = [1 if segs[s]["diff_median"] > 0 else -1
                            for s, _, _ in SEGMENTS]

    # ── 문턱 3: 최악 연도 제거 ──
    print("[문턱3] 최악 연도 제거 …", flush=True)
    years = sorted({t["scan_date"][:4] for t in base})
    dy = {}
    for y in years:
        sb = [t for t in base if t["scan_date"][:4] != y]
        sv = [t for t in v2 if t["scan_date"][:4] != y]
        rb = grid.run_cell(sb, cache, byday, all_dates, drop5=False)
        rv = grid.run_cell(sv, cache, byday, all_dates, drop5=False)
        dd = [rv["equities"][i] - rb["equities"][i] for i in range(len(rb["equities"]))]
        dy[y] = {"diff_median": st.median(dd),
                 "base": rb["median"], "v2": rv["median"]}
        print("  %s 제거 → 차이 중앙 %+.2f%%p (현행 %+.1f%% · 변형2 %+.1f%%)"
              % (y, dy[y]["diff_median"], rb["median"], rv["median"]), flush=True)
    worst = min(dy, key=lambda y: dy[y]["diff_median"])
    res["drop_year"] = {"by_year": dy, "worst_year": worst,
                        "worst_diff": dy[worst]["diff_median"],
                        "sign_holds": dy[worst]["diff_median"] > 0}

    # ── 문턱 4: 기여 상위 5건 제거 ──
    order = sorted(fired, key=lambda t: -(t["gain"] -
                                          bm[(t["scan_date"], t["code"], t["pattern"])]["gain"]))
    top5 = {(t["scan_date"], t["code"], t["pattern"]) for t in order[:5]}
    sb = [t for t in base if (t["scan_date"], t["code"], t["pattern"]) not in top5]
    sv = [t for t in v2 if (t["scan_date"], t["code"], t["pattern"]) not in top5]
    r4 = bootstrap({"base": sb, "v2": sv}, pos_of, n_pos, seeds=(0,))
    d4 = [r4["v2"][i] - r4["base"][i] for i in range(N_BOOT)]
    a4, b4 = ci(d4)
    print("[문턱4] 기여 상위 5건 제거 → 차이 중앙 %+.2f%%p (95%% %+.2f ~ %+.2f)"
          % (st.median(d4), a4, b4), flush=True)
    res["drop_top5"] = {"diff_median": st.median(d4), "ci_lo": a4, "ci_hi": b4,
                        "sign_holds": st.median(d4) > 0,
                        "removed": sorted(top5)}

    # ── 문턱 5: 슬리피지 0.5%p (변형이 더한 익일 시가 청산에만) ──
    v2s = apply_slip(v2, "dayN", SLIP)
    r5 = bootstrap({"base": base, "v2": v2s}, pos_of, n_pos, seeds=(0,))
    d5s = [r5["v2"][i] - r5["base"][i] for i in range(N_BOOT)]
    a5, b5 = ci(d5s)
    print("[문턱5] 슬리피지 %.1f%%p → 차이 중앙 %+.2f%%p (95%% %+.2f ~ %+.2f)"
          % (SLIP, st.median(d5s), a5, b5), flush=True)
    res["slippage"] = {"pct": SLIP, "diff_median": st.median(d5s), "ci_lo": a5,
                       "ci_hi": b5, "sign_holds": st.median(d5s) > 0}
    (OUT / "15-variant2-followup.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  (중간 저장 완료 — 문턱 다섯까지)", flush=True)

    # ── 이웃 일차 3·4·5·6·7 (판정 아님) ──
    print("\n[이웃 일차] 판정 아님 — 5일차만 튀는지 본다", flush=True)
    nb = {}
    for name, tr in arms_days.items():
        rr = bootstrap({"base": base, "v": tr}, pos_of, n_pos, seeds=(0,))
        dd = [rr["v"][i] - rr["base"][i] for i in range(N_BOOT)]
        a, b = ci(dd)
        nfire = sum(1 for t in tr if t["reason"] == "dayN")
        lv = grid.run_cell(tr, cache, byday, all_dates, drop5=False)
        nb[name] = {"n_fired": nfire, "diff_median": st.median(dd), "ci_lo": a, "ci_hi": b,
                    "pct_positive": sum(1 for x in dd if x > 0) / N_BOOT * 100,
                    "slot5_median": lv["median"], "n_filled": lv["n_filled"]}
        print("  %s 발동 %4d건 · 차이 중앙 %+.2f%%p (95%% %+.2f ~ %+.2f) 양수 %.1f%% "
              "· 슬롯5 중앙 %+.1f%% 체결 %.0f"
              % (name, nfire, st.median(dd), a, b, nb[name]["pct_positive"],
                 lv["median"], lv["n_filled"]), flush=True)
    res["neighbor_days"] = nb

    (OUT / "15-variant2-followup.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/15-variant2-followup.json")


if __name__ == "__main__":
    main()
