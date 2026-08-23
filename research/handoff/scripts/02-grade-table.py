# -*- coding: utf-8 -*-
"""02 — 🟢🟡🔴 4칸 등급표 (페이지 주장 4).

지시서: research/handoff/tasks/02-grade-table.md (v2 개정 반영)

두 축은 이미 따로따로 무너졌다(나스닥 33변형 BH 생존 0 · 국면 5기준 중 3실패).
이번에 보는 것은 **그 곱**이다.

날짜 정렬 (M9-9)
----------------
  국면   : `scan_date` **종가** 기준 `up_ew20` (매수는 다음 날이므로 룩어헤드 없음)
  나스닥 : `nas_up(E) = up[ max{ d ∈ keys(up) : d < E } ]`  (E = entry_date)
           키는 **미국 날짜**다. 매수일 아침에 이미 끝나 있는 직전 미국장 종가만 쓴다.

1순위 가설: **🔴칸(둘 다 나쁨)의 거래당 순수익 < 나머지 세 칸 평균.**
통계량 S = mean(나머지 세 칸) − mean(🔴). **S > 0 이면 가설을 지지한다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/02-grade-table.py
난수 seed: 원형이동 순열 3000~3999 · 부트스트랩 4000 · 슬롯5 짝비교 0~399
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_PERM = 1000
PERM_SEED = 3000
N_BOOT = 1000
BOOT_SEED = 4000
N_PAIR = 400
SEGMENTS = [("2021", "2021-01-01", "2021-12-31"), ("2022", "2022-01-01", "2022-12-31"),
            ("2023", "2023-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
            ("2025~26", "2025-01-01", "2026-12-31")]
NINE_MONTH_FROM = "2025-11-26"
net = slot_sim.net


def load_events():
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            if e["result"] not in ("win", "loss"):
                continue
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append(e)
    return ev


def load_axes():
    reg = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))
    up_ew = dict(zip(reg["dates"], reg["up_ew20"]))
    up_ks = dict(zip(reg["dates"], reg["up_ks20"]))
    nas = json.loads((BT / "nasdaq.json").read_text(encoding="utf-8"))
    nkeys = sorted(nas["up"])
    return up_ew, up_ks, nas["up"], nkeys


def nas_up(nup, nkeys, entry_date):
    """M9-9: up[ max{ d ∈ keys : d < E } ]. 없으면 None."""
    i = bisect_left(nkeys, entry_date)
    if i == 0:
        return None, None
    d = nkeys[i - 1]
    return nup[d], d


def cell_of(regime, nas):
    if regime is None or nas is None:
        return None
    if regime and nas:
        return "🟢 둘 다 좋음"
    if regime and not nas:
        return "🟡 상승국면+나스닥↓"
    if (not regime) and nas:
        return "🟡 조정국면+나스닥↑"
    return "🔴 둘 다 나쁨"


CELLS = ["🟢 둘 다 좋음", "🟡 상승국면+나스닥↓", "🟡 조정국면+나스닥↑", "🔴 둘 다 나쁨"]
RED = "🔴 둘 다 나쁨"


def summarize(rows):
    if not rows:
        return {"n": 0, "win_rate": None, "mean_net": None}
    v = [net(r["gain"]) for r in rows]
    return {"n": len(v),
            "win_rate": sum(1 for r in rows if r["result"] == "win") / len(rows) * 100,
            "mean_net": st.mean(v)}


def stat_S(rows):
    """S = mean(나머지 세 칸) − mean(🔴). 양수면 '🔴가 더 나쁘다'를 지지."""
    red = [net(r["gain"]) for r in rows if r["cell"] == RED]
    oth = [net(r["gain"]) for r in rows if r["cell"] and r["cell"] != RED]
    if not red or not oth:
        return None
    return st.mean(oth) - st.mean(red)


def main():
    ev = load_events()
    up_ew, up_ks, nup, nkeys = load_axes()
    print("확정 이벤트 %d건 · 나스닥 키 %d개 (%s ~ %s)"
          % (len(ev), len(nkeys), nkeys[0], nkeys[-1]), flush=True)

    rows, miss_reg, miss_nas = [], 0, 0
    sample = []
    for e in ev:
        r = up_ew.get(e["scan_date"])
        n_, nd = nas_up(nup, nkeys, e["entry_date"])
        if r is None:
            miss_reg += 1
        if n_ is None:
            miss_nas += 1
        c = cell_of(r, n_)
        rows.append({"code": e["code"], "pattern": e["pattern"],
                     "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                     "resolve_date": e["resolve_date"],
                     "gain": e["gain_at_resolve_pct"], "result": e["result"],
                     "regime": r, "nas": n_, "nas_date": nd, "cell": c,
                     "month": e["entry_date"][:7]})
        if len(sample) < 10:
            sample.append({"scan_date": e["scan_date"], "entry_date": e["entry_date"],
                           "nasdaq_date_used": nd, "nas_up": n_,
                           "regime_up_ew20": r, "cell": c})
    used = [r for r in rows if r["cell"]]
    print("칸 배정 %d건 · 국면 결측 %d · 나스닥 결측 %d (제외 %d)"
          % (len(used), miss_reg, miss_nas, len(rows) - len(used)), flush=True)
    print("나스닥 날짜 정렬 표본 10건:", flush=True)
    for s in sample:
        print("   scan %s → entry %s · 쓴 나스닥 날짜 %s (상승 %s) · 칸 %s"
              % (s["scan_date"], s["entry_date"], s["nasdaq_date_used"],
                 s["nas_up"], s["cell"]), flush=True)

    # ── 4칸 표 ──
    table = {c: summarize([r for r in used if r["cell"] == c]) for c in CELLS}
    for c in CELLS:
        t = table[c]
        seg = {}
        for name, lo, hi in SEGMENTS:
            g = [r for r in used if r["cell"] == c and lo <= r["scan_date"] <= hi]
            seg[name] = summarize(g)
        t["segments"] = seg
        print("%-22s n=%4d 승률 %5.1f%% 거래당 %+6.3f%%  구간별 %s"
              % (c, t["n"], t["win_rate"], t["mean_net"],
                 {k: (v["n"], None if v["mean_net"] is None else round(v["mean_net"], 2))
                  for k, v in seg.items()}), flush=True)

    S = stat_S(used)
    print("\n1순위 통계량 S = 나머지 세 칸 거래 전체 평균 − 🔴 평균 = %+.4f%%p (합산 평균, 판정용)"
          % S, flush=True)
    # 부가 한 줄: 칸별 평균의 단순 평균 (판정 미사용 — 두뇌 세션 지시).
    #   둘이 어긋나면 합산 평균이 건수 많은 🟢칸(1,498건)에 끌려간 것인지 알 수 있다.
    simple = st.mean([table[c]["mean_net"] for c in CELLS[:3]]) - table[RED]["mean_net"]
    print("   (부가) 칸별 평균의 단순 평균 기준 = %+.4f%%p — 판정 미사용" % simple, flush=True)

    # ── 최악 연도 제거 (12번·14번에서 표준 검사가 된 것) ──
    years = sorted({r["scan_date"][:4] for r in used})
    S_dy = {y: stat_S([r for r in used if r["scan_date"][:4] != y]) for y in years}
    worst_y = min(S_dy, key=lambda y: S_dy[y])
    print("최악 연도 제거: %s 를 빼면 S = %+.4f%%p (부호 %s) · 연도별 %s"
          % (worst_y, S_dy[worst_y], "유지" if S_dy[worst_y] > 0 else "뒤집힘",
             {y: round(v, 3) for y, v in S_dy.items()}), flush=True)
    # 칸마다: 그 칸의 주장을 가장 크게 떠받치는 한 해를 뺀 값
    cell_dy = {}
    for c in CELLS:
        vals = {}
        for y in years:
            g = [r for r in used if r["cell"] == c and r["scan_date"][:4] != y]
            vals[y] = st.mean([net(r["gain"]) for r in g]) if g else None
        # 🔴는 '가장 덜 나쁜' 값, 나머지는 '가장 덜 좋은' 값이 무너뜨리기 방향이다
        pick = (max if c == RED else min)(vals, key=lambda y: vals[y])
        cell_dy[c] = {"by_year": vals, "worst_year": pick, "value": vals[pick]}

    res = {"n_events": len(ev), "n_used": len(used), "n_missing_regime": miss_reg,
           "n_missing_nasdaq": miss_nas, "nasdaq_align_sample": sample,
           "table": table, "S": S, "S_simple_cell_average": simple,
           "S_drop_year": {"by_year": S_dy, "worst_year": worst_y,
                           "value": S_dy[worst_y], "sign_holds": S_dy[worst_y] > 0},
           "cell_drop_year": cell_dy}

    # ── L1 대체: 같은 달 안 비교 ──
    months = defaultdict(list)
    for r in used:
        months[r["month"]].append(r)
    diffs = []
    for m, g in sorted(months.items()):
        red = [net(x["gain"]) for x in g if x["cell"] == RED]
        oth = [net(x["gain"]) for x in g if x["cell"] != RED]
        if red and oth:
            diffs.append(st.mean(oth) - st.mean(red))
    pos = sum(1 for x in diffs if x > 0)
    n = len(diffs)
    # 부호검정 (양측, 정규근사 아님 — 이항 정확검정)
    from math import comb
    k = min(pos, n - pos)
    p_sign = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n))
    rnd = random.Random(BOOT_SEED)
    bmed = sorted(st.median([diffs[rnd.randrange(n)] for _ in range(n)])
                  for _ in range(N_BOOT))
    lo, hi = bmed[int(N_BOOT * 0.025)], bmed[int(N_BOOT * 0.975) - 1]
    l1 = {"n_months": n, "n_positive": pos, "median_diff": st.median(diffs),
          "p_sign": p_sign, "ci_lo": lo, "ci_hi": hi,
          "pass": bool(p_sign < 0.05 and (lo > 0 or hi < 0))}
    print("[L1 대체·같은 달 비교] 달 %d개 중 양수 %d · 차이 중앙 %+.3f%%p · 부호검정 p=%.4f "
          "· 95%% 구간 %+.3f ~ %+.3f → %s"
          % (n, pos, l1["median_diff"], p_sign, lo, hi,
             "통과" if l1["pass"] else "미통과"), flush=True)

    # ── L2 원형이동 순열 ──
    dates = sorted({r["scan_date"] for r in used})
    ed = sorted({r["entry_date"] for r in used})
    cal = sorted(set(up_ew))
    pr = random.Random(PERM_SEED)
    ge = 0
    perm_vals = []
    for _ in range(N_PERM):
        k2 = pr.randrange(1, len(cal))
        shifted_reg = {cal[i]: up_ew[cal[(i + k2) % len(cal)]] for i in range(len(cal))}
        shifted_nas = {}
        for i in range(len(nkeys)):
            shifted_nas[nkeys[i]] = nup[nkeys[(i + k2) % len(nkeys)]]
        tmp = []
        for r in used:
            rr = shifted_reg.get(r["scan_date"])
            nn, _ = nas_up(shifted_nas, nkeys, r["entry_date"])
            c = cell_of(rr, nn)
            if c:
                tmp.append({"cell": c, "gain": r["gain"]})
        s2 = stat_S(tmp)
        if s2 is not None:
            perm_vals.append(s2)
            if s2 >= S:
                ge += 1
    p_perm = (ge + 1) / (len(perm_vals) + 1)
    l2 = {"n_perm": len(perm_vals), "p": p_perm, "pass": bool(p_perm < 0.05),
          "null_p95": sorted(perm_vals)[int(len(perm_vals) * 0.95)]}
    print("[L2 원형이동 순열] %d회 · p=%.4f (귀무 95%% %+.3f) → %s"
          % (len(perm_vals), p_perm, l2["null_p95"], "통과" if l2["pass"] else "미통과"),
          flush=True)

    # ── L3 구간 5/5 ──
    seg_S = {}
    for name, lo2, hi2 in SEGMENTS:
        g = [r for r in used if lo2 <= r["scan_date"] <= hi2]
        seg_S[name] = stat_S(g)
    signs = [1 if (seg_S[n2] or 0) > 0 else -1 for n2, _, _ in SEGMENTS]
    l3 = {"by_segment": seg_S, "signs": signs, "pass": all(x > 0 for x in signs)}
    print("[L3 구간 5/5] %s → %s"
          % ({k: round(v, 3) for k, v in seg_S.items()},
             "통과" if l3["pass"] else "미통과"), flush=True)

    # ── L4 집중도: 가설을 가장 크게 떠받치는 5건 제거 ──
    #   각 거래를 하나씩 빼 S 를 다시 계산해, S 를 가장 많이 **떨어뜨리는**(= 가설 지지에
    #   가장 크게 기여한) 5건을 골라 함께 제거한다.
    #   (누적합으로 O(n) 계산 — 리스트를 매번 다시 만들면 3,681² 이라 느리다)
    rv = [net(r["gain"]) for r in used]
    is_red = [r["cell"] == RED for r in used]
    rs = sum(v for v, b in zip(rv, is_red) if b)
    rn = sum(is_red)
    os_ = sum(v for v, b in zip(rv, is_red) if not b)
    on = len(rv) - rn
    eff = []
    for i, v in enumerate(rv):
        if is_red[i]:
            s2 = os_ / on - (rs - v) / (rn - 1)
        else:
            s2 = (os_ - v) / (on - 1) - rs / rn
        eff.append((s2, i))
    eff.sort()
    # ★ M30 (정본) — 제거 대상은 **|기여|가 큰 5건**, 즉 양쪽 꼬리다.
    #   한쪽(가장 양수 기여)만 빼면 S 가 이미 음수일 때 부호가 뒤집힐 수 없어
    #   **실패할 수 없는 검정**이 된다.
    two = sorted(eff, key=lambda t: -abs(t[0] - S))
    drop2 = {i for _, i in two[:5]}
    S4 = stat_S([r for i, r in enumerate(used) if i not in drop2])
    sg = 1 if S > 0 else -1
    drop1 = {i for _, i in eff[:5]}          # 옛 한쪽 꼬리 판 (참고)
    S4_one = stat_S([r for i, r in enumerate(used) if i not in drop1])
    l4 = {"S_after": S4, "pass": bool((S4 > 0) == (sg > 0)),
          "rule": "|기여| 상위 5건 = 양쪽 꼬리 (M30)",
          "S_after_one_tail": S4_one,
          "removed": [{"code": used[i]["code"], "scan_date": used[i]["scan_date"],
                       "cell": used[i]["cell"],
                       "net": round(net(used[i]["gain"]), 2)} for i in sorted(drop2)]}
    print("[L4 |기여|상위5 제거(양쪽 꼬리)] S %+.4f → %+.4f → %s "
          "(참고: 한쪽 꼬리 판이면 %+.4f)"
          % (S, S4, "통과" if l4["pass"] else "미통과", S4_one), flush=True)

    # ── L2′ leave-one-year (M13·M15 정본 렌즈. 02는 그 전에 돌아 빠져 있었다) ──
    l2p = {"by_year": S_dy,
           "pass": bool(all(v is not None and (v > 0) == (sg > 0) for v in S_dy.values()))}
    print("[L2′ leave-one-year] %s → %s"
          % ({y: round(v, 4) for y, v in S_dy.items()},
             "통과" if l2p["pass"] else "미통과"), flush=True)

    # ── L5 슬롯5 세 판 ──
    def trades(filt):
        return [{"code": r["code"], "pattern": r["pattern"], "scan_date": r["scan_date"],
                 "entry_date": r["entry_date"], "resolve_date": r["resolve_date"],
                 "gain": r["gain"], "result": r["result"]} for r in used if filt(r)]

    A = trades(lambda r: True)
    B = trades(lambda r: r["cell"] != RED)
    C = trades(lambda r: r["cell"] == CELLS[0])
    pb = slot_sim.paired(B, A, n_runs=N_PAIR)
    pc = slot_sim.paired(C, A, n_runs=N_PAIR)
    ba = slot_sim.band(A, n_runs=200)
    bb = slot_sim.band(B, n_runs=200)
    bc = slot_sim.band(C, n_runs=200)
    l5 = {"n_all": len(A), "n_no_red": len(B), "n_green_only": len(C),
          "paired_no_red_vs_all": pb, "paired_green_only_vs_all": pc,
          "band_all": ba, "band_no_red": bb, "band_green_only": bc,
          "pass": bool(pb["win_rate_pct"] >= 75 and pb["diff_median"] > 0)}
    print("[L5 슬롯5] 🔴금지 vs 무필터 우세율 %.1f%% (차이중앙 %+.1f%%p) · "
          "🟢만 vs 무필터 우세율 %.1f%% (%+.1f%%p) → %s"
          % (pb["win_rate_pct"], pb["diff_median"], pc["win_rate_pct"],
             pc["diff_median"], "통과" if l5["pass"] else "미통과"), flush=True)
    print("     체결(중앙) 무필터 %.0f · 🔴금지 %.0f · 🟢만 %.0f"
          % (ba["n_filled"], bb["n_filled"], bc["n_filled"]), flush=True)

    res["lenses"] = {"L1_alt_month": l1, "L2_perm": l2, "L2p_leave_one_year": l2p,
                     "L3_segments": l3, "L4_drop5": l4, "L5_slot5": l5}
    res["n_lenses_passed"] = sum(1 for k in ("L2_perm", "L3_segments", "L4_drop5",
                                             "L5_slot5")
                                 if res["lenses"][k]["pass"])
    print("\n판정용 4렌즈(L2·L3·L4·L5) 통과 수: %d / 4 (L1 대체는 %s, 판정 미포함)"
          % (res["n_lenses_passed"], "통과" if l1["pass"] else "미통과"), flush=True)
    # M15 정본 렌즈 구성(L1·L2′·L3·L4)으로 다시 세면 — 02는 M15 이전에 돌아 구성이 달랐다
    m15 = {"L1": l1["pass"], "L2p": l2p["pass"], "L3": l3["pass"], "L4": l4["pass"]}
    res["n_lenses_m15"] = sum(m15.values())
    print("M15 정본 구성(L1·L2′·L3·L4)으로 세면: %s → %d / 4"
          % ({k: ("통과" if v else "미통과") for k, v in m15.items()},
             res["n_lenses_m15"]), flush=True)

    # ── 9개월 대조 (참고) ──
    nine = [r for r in used if r["scan_date"] >= NINE_MONTH_FROM]
    res["nine_month"] = {"n": len(nine),
                         "table": {c: summarize([r for r in nine if r["cell"] == c])
                                   for c in CELLS}}
    print("\n[9개월 대조 · 참고] %s 이후 확정 %d건" % (NINE_MONTH_FROM, len(nine)), flush=True)
    for c in CELLS:
        t = res["nine_month"]["table"][c]
        print("   %-22s n=%3d 승률 %s 거래당 %s"
              % (c, t["n"], "—" if t["win_rate"] is None else "%.1f%%" % t["win_rate"],
                 "—" if t["mean_net"] is None else "%+.2f%%" % t["mean_net"]), flush=True)

    # ── 부가: up_ks20 (코스피 20일선) 판 ──
    ks_rows = []
    for r in used:
        c = cell_of(up_ks.get(r["scan_date"]), r["nas"])
        if c:
            ks_rows.append({**r, "cell": c})
    res["ks20"] = {"n": len(ks_rows),
                   "table": {c: summarize([r for r in ks_rows if r["cell"] == c])
                             for c in CELLS},
                   "S": stat_S(ks_rows)}
    print("\n[부가 · up_ks20 코스피 20일선] n=%d · S=%+.4f%%p"
          % (len(ks_rows), res["ks20"]["S"] or 0), flush=True)
    for c in CELLS:
        t = res["ks20"]["table"][c]
        print("   %-22s n=%4d 승률 %s 거래당 %s"
              % (c, t["n"], "—" if t["win_rate"] is None else "%.1f%%" % t["win_rate"],
                 "—" if t["mean_net"] is None else "%+.3f%%" % t["mean_net"]), flush=True)

    (OUT / "02-grade-table.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/02-grade-table.json")


if __name__ == "__main__":
    main()
