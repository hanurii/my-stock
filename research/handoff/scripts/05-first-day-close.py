# -*- coding: utf-8 -*-
"""05 — 첫날 종가가 매수가 아래 (페이지 주장 7).

지시서: research/handoff/tasks/05-first-day-close.md (v2 + M9-6 + M10~M19)

**★ 페이지 표현 정정 (결과 첫 줄):** 페이지는 "첫날 종가가 매수가 아래인 318건"이라 적어
**일부 예외처럼** 읽히는데, 5.6년으로 늘리면 **전체의 55%** — 예외가 아니라
**매매 둘 중 하나꼴의 보통 상황**이다. 규칙의 무게가 달라진다.

판정 (M9-6 · M14-1 · M15 · M19)
-------------------------------
· 05는 **"효과 있다"(= 팔면 손해다)** 쪽 주장이다.
· **1순위 = 집단 A 의 거래당 짝차이 (완주 − 익일매도), %p.** 양수면 "팔면 손해"를 지지.
  (M14-2: 슬롯5는 **부차**로 내린다. 단 반드시 함께 싣고
   **"거래당은 슬롯 회전 이득을 못 잰다"**를 명시한다 — 그게 원래 슬롯5를 고른 이유였다.)
· 판정축 = 1순위의 블록 부트스트랩 95% 구간(M14-1). 동등성 폭 **±0.5%p**(M16-2).
· **L2(원형이동)는 해당없음** — 같은 거래에 두 규칙이라 회전해도 거래별 결과가 안 바뀐다(M11).
  → **4렌즈 기준**: L1(같은날) · L2′(leave-one-year) · L3(구간 5/5) · L4(집중도).
· MDE = 2.80 × 부트스트랩 차이 SD.

두 팔
-----
  (가) 규칙대로 완주 : +20% / −10% 선착, 체결은 닿은 날 종가
  (나) 익일 시가 매도 : **매수 다음날 시가**에 판다.
       단 **매수 당일에 이미 목표·손절에 닿은 건은 (나)에서도 원래 결과**를 쓴다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/05-first-day-close.py
난수 seed: 블록 부트스트랩 50000 · L1 중앙값 부트스트랩 50005 · 슬롯 순서 0~399
"""
from __future__ import annotations

import bisect
import json
import random
import statistics as st
import sys
from collections import defaultdict
from math import comb, erf, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
N_BOOT, N_LEVEL, N_PAIR = 1000, 200, 400
BOOT_SEED = 50000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
EQUIV = 0.5
SEED5 = (0, 1, 2, 3, 4)
BUCKETS = [(-2.0, 0.0, "−0~−2%"), (-4.0, -2.0, "−2~−4%"),
           (-6.0, -4.0, "−4~−6%"), (-1e9, -6.0, "−6%~")]
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
net = slot_sim.net


def load_and_resolve():
    """경로를 읽어 **바로 두 팔의 결과 스칼라로 줄인다**(배열은 즉시 버려 메모리를 낮춘다)."""
    rows = []
    year_last = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        last = max(p["dates"][-1] for p in d["paths"])
        year_last[y] = last
        for p in d["paths"]:
            e = p["entry_price"]
            h, l, c, o, dts = p["h"], p["l"], p["c"], p["o"], p["dates"]
            n = len(c)
            T, S = e * (1 + TARGET / 100), e * (1 - STOP / 100)
            mh, ml = -1e30, 1e30
            rmax, rminn = [], []
            for i in range(n):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rminn.append(-ml)
            ti = bisect.bisect_left(rmax, T)
            si = bisect.bisect_left(rminn, -S)
            ti = ti if ti < n else None
            si = si if si < n else None
            if ti is None and si is None:
                i, why = n - 1, "last_close"
            elif si is None:
                i, why = ti, "target"
            elif ti is None:
                i, why = si, "stop"
            elif ti < si:
                i, why = ti, "target"
            elif si < ti:
                i, why = si, "stop"
            else:
                i, why = ti, "both_same_day"
            full = {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": dts[i], "reason": why}
            if i == 0 or n < 2:
                sell = dict(full)          # 매수 당일 결착 → (나)도 원래 결과
                sell_kind = "당일결착(원래 결과)"
            else:
                sell = {"gain": (o[1] / e - 1) * 100, "days": 1,
                        "resolve_date": dts[1], "reason": "next_open"}
                sell_kind = "익일 시가"
            rows.append({
                "key": (p["scan_date"], p["code"], p["pattern"]),
                "code": p["code"], "pattern": p["pattern"], "scan_date": p["scan_date"],
                "entry_date": p["entry_date"], "year": p["entry_date"][:4],
                "c_pct0": (c[0] / e - 1) * 100, "n_days": n,
                "full": full, "sell": sell, "sell_kind": sell_kind,
                "vanished": p["dates"][-1] < last, "year_file": y})
        print("  경로 %d 적재 · 누적 %d" % (y, len(rows)), flush=True)
    return rows


def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(diffs):
    n = len(diffs)
    pos = sum(1 for x in diffs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_positive": pos, "mean": st.mean(diffs),
            "median": st.median(diffs), "p": p, "how": how}


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    n = len(s)
    return s[int(n * lo / 100)], s[int(n * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def block_boot_values(by_pos, n_pos, seed, stat=st.mean):
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        acc = []
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                acc.extend(by_pos.get(a + j, ()))
        if acc:
            out.append(stat(acc))
    return out


def to_trade(r, arm):
    d = r[arm]
    return {"code": r["code"], "pattern": r["pattern"], "scan_date": r["scan_date"],
            "entry_date": r["entry_date"], "resolve_date": d["resolve_date"],
            "gain": d["gain"],
            "result": ("win" if d["reason"] == "target" else
                       "loss" if d["reason"] in ("stop", "both_same_day") else
                       ("win" if d["gain"] > 0 else "loss"))}


def main():
    print("경로 적재 · 두 팔 결착 …", flush=True)
    rows = load_and_resolve()
    print("전체 %d건" % len(rows), flush=True)

    A = [r for r in rows if r["c_pct0"] < 0]
    same_day = [r for r in A if r["sell_kind"].startswith("당일")]
    paired = [r for r in A if not r["sell_kind"].startswith("당일")]
    n_one_day = sum(1 for r in A if r["n_days"] < 2)
    print("★ 집단 A(매수일 종가 < 매수가) = **%d건 / %d = %.1f%%**"
          % (len(A), len(rows), len(A) / len(rows) * 100), flush=True)
    print("   진입일 수 %d일 · 경로 1일뿐 %d건 · 당일 이미 결착(둘이 같은 건) %d건(%.1f%%) · "
          "**실제로 갈리는 짝 %d건**"
          % (len({r["entry_date"] for r in A}), n_one_day, len(same_day),
             len(same_day) / len(A) * 100, len(paired)), flush=True)
    yr = defaultdict(int)
    for r in A:
        yr[r["year"]] += 1
    print("   연도별 %s" % dict(sorted(yr.items())), flush=True)

    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(r["entry_date"] for r in rows)
    hi_d = max(max(r["full"]["resolve_date"], r["sell"]["resolve_date"]) for r in rows)
    all_dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)

    res = {"n_all": len(rows), "n_group_a": len(A),
           "group_a_pct": len(A) / len(rows) * 100,
           "n_entry_days": len({r["entry_date"] for r in A}),
           "n_one_day_path": n_one_day, "n_same_day_resolved": len(same_day),
           "n_paired": len(paired), "by_year": dict(sorted(yr.items())),
           "equiv": EQUIV, "mde_k": MDE_K}

    # ── 1순위: 집단 A 의 거래당 짝차이 (완주 − 익일매도) ──
    diffs = {}
    for r in A:
        diffs[r["key"]] = net(r["full"]["gain"]) - net(r["sell"]["gain"])
    vals = list(diffs.values())
    by_pos = defaultdict(list)
    for r in A:
        by_pos[pos_of[r["entry_date"]]].append(diffs[r["key"]])
    bmean = block_boot_values(by_pos, n_pos, BOOT_SEED, st.mean)
    bmed = block_boot_values(by_pos, n_pos, BOOT_SEED, st.median)
    lo, hi = ci(bmean)
    mlo, mhi = ci(bmed)
    sd = st.stdev(bmean)
    excl = lo > 0 or hi < 0
    within = -EQUIV <= lo and hi <= EQUIV
    point = st.mean(vals)
    verdict = ("유지(나머지 렌즈 충족 시)" if (excl and point > 0) else
               "폐기(반대 방향)" if excl else
               "폐기(동등성)" if within else "판정불가(검정력 부족)")
    print("\n★ 1순위 S = 완주 − 익일매도 (거래당 순수익 %p)", flush=True)
    print("   평균 %+.4f%%p · 중앙 %+.4f%%p · 95%% 구간 %+.4f ~ %+.4f (0 제외 %s) · "
          "±0.5 안 %s · SD %.4f · **MDE %.4f%%p** → **%s**"
          % (point, st.median(vals), lo, hi, "예" if excl else "아니오",
             "예" if within else "아니오", sd, MDE_K * sd, verdict), flush=True)
    print("   중앙값 95%% 구간 %+.4f ~ %+.4f (0 제외 %s)"
          % (mlo, mhi, "예" if (mlo > 0 or mhi < 0) else "아니오"), flush=True)

    # 2026 제외 5년
    v5 = [diffs[r["key"]] for r in A if r["year"] != "2026"]
    bp5 = defaultdict(list)
    for r in A:
        if r["year"] != "2026":
            bp5[pos_of[r["entry_date"]]].append(diffs[r["key"]])
    b5 = block_boot_values(bp5, n_pos, BOOT_SEED + 1, st.mean)
    l5, h5 = ci(b5)
    print("   2026 제외 5년: n=%d · 평균 %+.4f%%p · 95%% %+.4f ~ %+.4f (0 제외 %s)"
          % (len(v5), st.mean(v5), l5, h5, "예" if (l5 > 0 or h5 < 0) else "아니오"),
          flush=True)

    # ── 렌즈 ──
    byday = defaultdict(list)
    for r in A:
        byday[r["entry_date"]].append(diffs[r["key"]])
    daily = [st.mean(v) for _, v in sorted(byday.items())]
    l1 = sign_test(daily)
    rnd = random.Random(BOOT_SEED + 5)
    dboot = sorted(st.median([daily[rnd.randrange(len(daily))] for _ in range(len(daily))])
                   for _ in range(N_BOOT))
    dlo, dhi = dboot[int(N_BOOT * 0.025)], dboot[int(N_BOOT * 0.975) - 1]
    years = sorted({r["year"] for r in A})
    dyr = {y: st.mean([diffs[r["key"]] for r in A if r["year"] != y]) for y in years}
    segs = {}
    for sn, y0, y1 in SEGMENTS:
        g = [diffs[r["key"]] for r in A if y0 <= r["year"] <= y1]
        segs[sn] = {"n": len(g), "mean": st.mean(g) if g else None}
    srt = sorted(vals, reverse=True)
    S4 = st.mean(sorted(vals, reverse=True)[5:])
    lens = {"L1": bool(l1["p"] < 0.05 and (dlo > 0 or dhi < 0)),
            "L2p": all(v > 0 for v in dyr.values()),
            "L3": all(v["mean"] is not None and v["mean"] > 0 for v in segs.values()),
            "L4": S4 > 0}
    print("\n[렌즈] L1 날 %d · 양수 %d · 중앙 %+.4f · p=%.4f (%s) · 중앙 95%% %+.4f ~ %+.4f"
          % (l1["n"], l1["n_positive"], l1["median"], l1["p"], l1["how"], dlo, dhi),
          flush=True)
    print("       L2′ 연도별 %s" % {y: round(v, 3) for y, v in dyr.items()}, flush=True)
    print("       L3 구간별 %s" % {k: (None if v["mean"] is None else round(v["mean"], 3))
                                  for k, v in segs.items()}, flush=True)
    print("       L4 상위5 제거 %+.4f → %+.4f" % (point, S4), flush=True)
    print("       → L1 %s · L2′ %s · L3 %s · L4 %s → **%d/4**"
          % (*["통과" if lens[k] else "미통과" for k in ("L1", "L2p", "L3", "L4")],
             sum(lens.values())), flush=True)
    res["primary"] = {"n": len(A), "mean": point, "median": st.median(vals),
                      "ci_lo": lo, "ci_hi": hi, "excludes_zero": excl,
                      "median_ci": [mlo, mhi], "within_equiv": within,
                      "boot_sd": sd, "MDE": MDE_K * sd, "verdict_axis": verdict,
                      "excl_2026": {"n": len(v5), "mean": st.mean(v5),
                                    "ci_lo": l5, "ci_hi": h5},
                      "L1": l1, "L1_median_ci": [dlo, dhi], "drop_year": dyr,
                      "segments": segs, "S_drop_top5": S4, "lenses": lens,
                      "n_lenses": sum(lens.values())}

    # ── 두 전략 요약표 ──
    def summ(rs, arm):
        g = [net(r[arm]["gain"]) for r in rs]
        w = sum(1 for r in rs if to_trade(r, arm)["result"] == "win")
        return {"n": len(rs), "win_rate": w / len(rs) * 100, "mean_net": st.mean(g)}

    # ★ 두 팔의 '승률'은 정의가 다르다 — 완주는 +20% 도달, 익일매도는 순수익>0.
    #   같은 정의(순수익>0)로도 맞춰 함께 낸다.
    def pos_rate(rs, arm):
        return sum(1 for r in rs if net(r[arm]["gain"]) > 0) / len(rs) * 100

    res["strategy_table"] = {
        "완주": {**summ(A, "full"),
               "reach20_pct": sum(1 for r in A if r["full"]["reason"] == "target")
               / len(A) * 100,
               "net_positive_pct": pos_rate(A, "full")},
        "익일매도": {**summ(A, "sell"),
                 "reach20_pct": sum(1 for r in A if r["sell"]["reason"] == "target")
                 / len(A) * 100,
                 "net_positive_pct": pos_rate(A, "sell")}}
    t = res["strategy_table"]
    print("\n[집단 A 두 전략] (승률 정의를 갈라 적는다)", flush=True)
    print("  완주      +20%% 도달 %.1f%% · 순수익>0 %.1f%% · 거래당 %+.3f%%"
          % (t["완주"]["reach20_pct"], t["완주"]["net_positive_pct"],
             t["완주"]["mean_net"]), flush=True)
    print("  익일매도  +20%% 도달 %.1f%% · 순수익>0 **%.1f%%** · 거래당 %+.3f%%"
          % (t["익일매도"]["reach20_pct"], t["익일매도"]["net_positive_pct"],
             t["익일매도"]["mean_net"]), flush=True)

    # ── "산수인가 정보인가" — 첫날 손실폭 구간별 ──
    print("\n[산수 검정] 첫날 손실폭 구간별", flush=True)
    bt = {}
    for lo_b, hi_b, name in BUCKETS:
        g = [r for r in A if lo_b <= r["c_pct0"] < hi_b]
        if not g:
            continue
        dv = [diffs[r["key"]] for r in g]
        s = sign_test(dv) if len(dv) > 1 else None
        bp = defaultdict(list)
        for r in g:
            bp[pos_of[r["entry_date"]]].append(diffs[r["key"]])
        bb = block_boot_values(bp, n_pos, BOOT_SEED + 10, st.mean)
        blo, bhi = ci(bb)
        n_same = sum(1 for r in g if r["sell_kind"].startswith("당일"))
        bt[name] = {"n": len(g), "n_identical_pair": n_same,
                    "identical_pct": n_same / len(g) * 100,
                    "full": st.mean([net(r["full"]["gain"]) for r in g]),
                    "sell": st.mean([net(r["sell"]["gain"]) for r in g]),
                    "diff": st.mean(dv), "ci_lo": blo, "ci_hi": bhi,
                    "excludes_zero": bool(blo > 0 or bhi < 0),
                    "p": s["p"] if s else None, "median": st.median(dv),
                    "reach20_pct": sum(1 for r in g if r["full"]["reason"] == "target")
                    / len(g) * 100}
        print("  %-8s n=%4d (두 팔 동일 %d건 %.1f%%) 완주 %+7.3f%% · 익일매도 %+7.3f%% · "
              "차이 %+7.3f%%p (95%% %+.3f ~ %+.3f, 0제외 %s) · 중앙 %+.3f · p=%.4f · +20%% 도달 %.1f%%"
              % (name, len(g), n_same, bt[name]["identical_pct"],
                 bt[name]["full"], bt[name]["sell"], bt[name]["diff"],
                 blo, bhi, "예" if bt[name]["excludes_zero"] else "아니오",
                 st.median(dv), bt[name]["p"], bt[name]["reach20_pct"]), flush=True)
    res["buckets"] = bt

    # ── 부가: 집단 A 의 +20% 도달률 (페이지 29%) ──
    reach = sum(1 for r in A if r["full"]["reason"] == "target") / len(A) * 100
    reach_seg = {}
    for sn, y0, y1 in SEGMENTS:
        g = [r for r in A if y0 <= r["year"] <= y1]
        reach_seg[sn] = {"n": len(g),
                         "pct": sum(1 for r in g if r["full"]["reason"] == "target")
                         / len(g) * 100 if g else None}
    notA = [r for r in rows if r["c_pct0"] >= 0]
    reach_notA = sum(1 for r in notA if r["full"]["reason"] == "target") / len(notA) * 100
    res["reach20"] = {"group_a_pct": reach, "not_a_pct": reach_notA,
                      "by_segment": reach_seg, "n_not_a": len(notA)}
    print("\n[부가] 집단 A 의 +20%% 도달률 %.1f%% (페이지 29%%) · 그 밖의 거래 %.1f%% (페이지 52%%)"
          % (reach, reach_notA), flush=True)
    print("   구간별 %s" % {k: (None if v["pct"] is None else round(v["pct"], 1))
                           for k, v in reach_seg.items()}, flush=True)

    # ── 부차: 슬롯5 (판정 미사용) ──
    print("\n[부차·슬롯5] — 거래당은 슬롯 회전 이득을 못 잰다. 그래서 함께 싣는다.", flush=True)
    keep = {r["key"] for r in A}
    arm_full = [to_trade(r, "full") for r in rows]
    arm_sell = [to_trade(r, "sell") if r["key"] in keep else to_trade(r, "full")
                for r in rows]
    slot = {}
    for nm, tr in (("전부 완주", arm_full), ("집단A만 익일매도", arm_sell)):
        b = slot_sim.band(tr, n_runs=N_LEVEL)
        slot[nm] = {**b, "band_width": b["p95"] - b["p5"]}
        print("  %-16s 중앙 %+7.1f%% · 5~95%% %+7.1f~%+7.1f (폭 %.1f%%p) · 체결 %.0f"
              % (nm, b["median"], b["p5"], b["p95"], b["p95"] - b["p5"], b["n_filled"]),
              flush=True)
    pr = slot_sim.paired(arm_full, arm_sell, n_runs=N_PAIR)
    print("  (강건성 참고·문턱 없음) 완주 우세율 %.1f%% · 차이중앙 %+.1f%%p"
          % (pr["win_rate_pct"], pr["diff_median"]), flush=True)
    res["slot5"] = {"bands": slot, "paired_reference_only": pr}

    (OUT / "05-first-day-close.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/05-first-day-close.json")


if __name__ == "__main__":
    main()
