# -*- coding: utf-8 -*-
"""10 - 돌파 순서대로 사라 (페이지 주장 12).

지시서: research/handoff/tasks/10-breakout-order.md (v2 + M9-10 ~ M27)

★ 못 박을 한계: 장중 실제 돌파 시각은 알 수 없다(5.6년치 분봉 없음).
   글자 그대로의 "돌파 순서"는 판정불가로 시작하고, 아래 대리 지표로만 잰다.
   대리 지표 gap_up_pct = (체결가 ÷ 피벗 − 1) × 100.
   0 = 장중에 피벗을 넘음 · 양수 = 시가부터 피벗 위(= 아침에 가장 먼저 돌파).

1순위 (M18-2, 값 기준) = **같은 날 안에서 `갭업 > 0` vs `갭업 == 0`**, 거래당 순수익 차이.
  순위 절반 방식은 부분 동점이 분할선을 가로질러 깨진다(부분 동점 351일).
  판정축 = 날 차이의 **평균**(M19) · 동등성 폭 **거래당 ±0.5%p**(M16-2) ·
  MDE = 2.80 × 블록 부트스트랩 차이 SD.
슬롯5 정렬 세 팔은 **부차**(M12-4). 동점은 (seed,date) 공유 순열로 무작위 배치(M9-10) —
  slot_sim.sim(order=...) 이 셔플 뒤 안정 정렬을 하므로 **동점만 무작위**가 된다.
원형이동 순열은 폐기(M15). 렌즈 넷 L1·L2′·L3·L4, 전부 **부호 일치까지 본다**(M27).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/10-breakout-order.py
난수 seed: 슬롯 순서 0~399 · 블록 부트스트랩 100000 · 같은 건수 대조 101000
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
N_PAIR, N_LEVEL = 400, 200
N_BOOT, N_CTRL = 1000, 200
BOOT_SEED, CTRL_SEED = 100000, 101000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K, EQUIV = 2.80, 0.5
BUCKETS = [("0%", 0.0, 0.0), ("0~1%", 0.0, 1.0), ("1~3%", 1.0, 3.0),
           ("3~5%", 3.0, 5.0), ("5%+", 5.0, 1e9)]
THIN = {"3~5%", "5%+"}          # M9-10: 얇은 칸은 참고·판정 제외
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")
net = slot_sim.net


def load():
    """경로에서 +20/−10 결착(그날 종가) + gap_up_pct. 확정판/M1판 둘 다 만든다."""
    rows = []
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            e = p["entry_price"]
            h, l, c, dts = p["h"], p["l"], p["c"], p["dates"]
            n = len(c)
            T, S = e * (1 + TARGET / 100), e * (1 - STOP / 100)
            rmax, rmin = [], []
            mh, ml = -1e30, 1e30
            for i in range(n):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rmin.append(-ml)
            ti = bisect.bisect_left(rmax, T)
            si = bisect.bisect_left(rmin, -S)
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
            g = (c[i] / e - 1) * 100
            rows.append({"code": p["code"], "pattern": p["pattern"],
                         "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                         "resolve_date": dts[i], "gain": g, "net": net(g),
                         "gap": p["gap_up_pct"], "year": p["entry_date"][:4],
                         "orig": p.get("orig_result"),
                         "result": ("win" if why == "target" else
                                    "loss" if why in ("stop", "both_same_day") else
                                    ("win" if g > 0 else "loss"))})
    return rows


def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(xs):
    n = len(xs)
    pos = sum(1 for x in xs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_pos": pos, "p": p, "how": how}


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    out, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        out.append((a, LL))
        total += LL
    return out


def day_pairs(rows):
    """같은 날 갭업>0 vs 갭업==0. 두 쪽이 다 있는 날만."""
    by = defaultdict(lambda: ([], []))
    for t in rows:
        by[t["entry_date"]][0 if t["gap"] > 0 else 1].append(t)
    out = {}
    for d, (a, b) in by.items():
        if a and b:
            out[d] = {"diff": st.mean(x["net"] for x in a) - st.mean(x["net"] for x in b),
                      "n_a": len(a), "n_b": len(b),
                      "wr_a": sum(1 for x in a if x["result"] == "win") / len(a) * 100,
                      "wr_b": sum(1 for x in b if x["result"] == "win") / len(b) * 100}
    return out


def primary(tag, rows):
    pairs = day_pairs(rows)
    dates = sorted(pairs)
    diffs = [pairs[d]["diff"] for d in dates]
    n_tr = sum(pairs[d]["n_a"] + pairs[d]["n_b"] for d in dates)
    mean, med = st.mean(diffs), st.median(diffs)
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d, hi_d = min(dates), max(dates)
    win = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(win)}
    n_pos = len(win)
    rnd = random.Random(BOOT_SEED)
    bm, bmd = [], []
    for _ in range(N_BOOT):
        s = []
        for st_, L in make_blocks(rnd, n_pos):
            for j in range(L):
                d = win[st_ + j]
                if d in pairs:
                    s.append(pairs[d]["diff"])
        if s:
            bm.append(st.mean(s))
            bmd.append(st.median(s))
    lo, hi = ci(bm)
    mlo, mhi = ci(bmd)
    sd = st.stdev(bm)
    mde = MDE_K * sd
    excl = lo > 0 or hi < 0
    within = -EQUIV <= lo and hi <= EQUIV
    label = ("폐기(0 제외)" if excl else "유지(동등성)" if within else
             ("판정불가(문턱 사각지대)" if (hi - lo) <= 2 * EQUIV
              else "확인 불가(검정력 부족)"))
    sg = 1 if mean > 0 else -1
    # L4 집중도 — 상위 5일 제거
    top5 = {d for d in sorted(dates, key=lambda x: abs(pairs[x]["diff"]))[-5:]}
    m4 = st.mean([pairs[d]["diff"] for d in dates if d not in top5])
    # L2′ leave-one-year
    l2 = {y: (st.mean([pairs[d]["diff"] for d in dates if d[:4] != y])
              if any(d[:4] != y for d in dates) else None) for y in YEARS}
    # L3 다섯 구간
    l3 = {}
    for sn, y0, y1 in SEGMENTS:
        v = [pairs[d]["diff"] for d in dates if y0 <= d[:4] <= y1]
        l3[sn] = {"n_days": len(v), "mean": st.mean(v) if v else None}
    stt = sign_test(diffs)
    lens = {"L1": bool(stt["p"] < 0.05 and (mlo > 0 or mhi < 0)
                       and (med > 0) == (sg > 0)),
            "L2p": all(v is not None and (v > 0) == (sg > 0) for v in l2.values()),
            "L3": all(v["mean"] is not None and (v["mean"] > 0) == (sg > 0)
                      for v in l3.values()),
            "L4": (m4 > 0) == (sg > 0)}
    l1_sig = bool(stt["p"] < 0.05 and (mlo > 0 or mhi < 0))
    # M27-3 날 가중 무게 분포
    items = sorted((pairs[d]["n_a"] + pairs[d]["n_b"], pairs[d]["diff"]) for d in dates)
    n = len(items)
    tot = sum(a for a, _ in items)
    ter = [items[:n // 3], items[n // 3:2 * n // 3], items[2 * n // 3:]]
    weight = [{"range": [g[0][0], g[-1][0]], "n_days": len(g),
               "share": sum(a for a, _ in g) / tot * 100,
               "mean": st.mean([b for _, b in g]),
               "median": st.median([b for _, b in g])} for g in ter]
    r = {"tag": tag, "n_days": len(dates), "n_trades": n_tr,
         "mean": mean, "mean_ci": [lo, hi], "ci_width": hi - lo, "sd": sd, "MDE": mde,
         "median": med, "median_ci": [mlo, mhi], "sign": stt,
         "excludes_zero": excl, "within_equiv": within, "verdict_axis": label,
         "L4_top5_removed": m4, "L2p": l2, "L3": l3, "lenses": lens,
         "L1_significant_only": l1_sig, "weight_terciles": weight}
    print("\n[1순위] %s — 같은 날 갭업>0 vs 갭업==0 (거래당 순수익 %%p)" % tag, flush=True)
    print("   날 %d일 · 거래 %d건 · 평균 %+.4f%%p · 중앙 %+.4f%%p"
          % (len(dates), n_tr, mean, med), flush=True)
    print("   평균 95%% %+.4f ~ %+.4f (폭 %.4f) · SD %.4f · MDE %.4f%%p · "
          "0제외 %s · ±0.5%%p 안 %s -> %s"
          % (lo, hi, hi - lo, sd, mde, "예" if excl else "아니오",
             "예" if within else "아니오", label), flush=True)
    print("   중앙 95%% %+.4f ~ %+.4f · 부호검정 %d일 중 양수 %d · p=%.4f (%s)"
          % (mlo, mhi, stt["n"], stt["n_pos"], stt["p"], stt["how"]), flush=True)
    print("   [M27-3 무게] " + " | ".join(
        "%d~%d건 %d일(표식 %.1f%%) 평균 %+.3f 중앙 %+.3f"
        % (g["range"][0], g["range"][1], g["n_days"], g["share"], g["mean"], g["median"])
        for g in weight), flush=True)
    print("   [렌즈] L1 %s · L2′ %s · L3 %s · L4 %+.4f -> %+.4f %s · 합계 %d/4"
          % (("통과" if lens["L1"] else
              ("미통과(유의하나 판정축과 반대 부호)" if l1_sig else "미통과")),
             "통과" if lens["L2p"] else "미통과",
             "통과" if lens["L3"] else "미통과",
             mean, m4, "통과" if lens["L4"] else "미통과", sum(lens.values())), flush=True)
    print("       L2′ %s" % {y: (None if v is None else round(v, 4))
                             for y, v in l2.items()}, flush=True)
    print("       L3 %s" % {k: (None if v["mean"] is None else round(v["mean"], 4))
                            for k, v in l3.items()}, flush=True)
    return r


def tie_diag(rows):
    by = defaultdict(list)
    for t in rows:
        by[t["entry_date"]].append(t["gap"])
    k2 = {d: v for d, v in by.items() if len(v) >= 2}
    all_tied = {d for d, v in k2.items() if len(set(v)) == 1}
    part_tied = {d for d, v in k2.items()
                 if len(set(v)) > 1 and len(set(v)) < len(v)}
    both = {d for d, v in k2.items() if any(x > 0 for x in v) and any(x == 0 for x in v)}
    return {"days_k2": len(k2), "all_tied": len(all_tied),
            "remaining": len(k2) - len(all_tied), "partial_tied": len(part_tied),
            "days_both_groups": len(both)}


def m29_3(rows, pairs):
    """M29-3 — 두 팔이 정의상 동일하거나 통계량이 고정되는 관측이 표본의 몇 %인가.

    (a) 정렬 세 팔: 그날 후보의 갭업이 전부 같으면(1건인 날 포함) **정렬이 무엇이든 결과가 같다.**
    (b) 1순위: 한쪽 무리가 1건뿐인 날은 그 무리 평균이 거래 하나로 고정된다.
    """
    by = defaultdict(list)
    for t in rows:
        by[t["entry_date"]].append(t["gap"])
    inert_days = [d for d, v in by.items() if len(set(v)) == 1]
    inert_tr = sum(len(by[d]) for d in inert_days)
    n_tr = len(rows)
    solo_a = [d for d in pairs if pairs[d]["n_a"] == 1]
    solo_b = [d for d in pairs if pairs[d]["n_b"] == 1]
    solo = set(solo_a) | set(solo_b)
    tr_pairs = sum(pairs[d]["n_a"] + pairs[d]["n_b"] for d in pairs)
    return {"sort_inert_days": len(inert_days), "sort_all_days": len(by),
            "sort_inert_day_pct": len(inert_days) / len(by) * 100,
            "sort_inert_trades": inert_tr, "sort_inert_trade_pct": inert_tr / n_tr * 100,
            "solo_a_days": len(solo_a), "solo_b_days": len(solo_b),
            "solo_days": len(solo), "solo_day_pct": len(solo) / len(pairs) * 100,
            "solo_trades": sum(pairs[d]["n_a"] + pairs[d]["n_b"] for d in solo),
            "solo_trade_pct": sum(pairs[d]["n_a"] + pairs[d]["n_b"]
                                  for d in solo) / tr_pairs * 100}


def bucket_table(rows):
    out = {}
    for name, lo, hi in BUCKETS:
        if name == "0%":
            sel = [t for t in rows if t["gap"] == 0]
        else:
            sel = [t for t in rows if lo < t["gap"] <= hi]
        segs = {}
        for sn, y0, y1 in SEGMENTS:
            v = [t for t in sel if y0 <= t["year"] <= y1]
            segs[sn] = {"n": len(v), "net": st.mean(x["net"] for x in v) if v else None}
        out[name] = {"n": len(sel), "thin": name in THIN,
                     "win_rate": (sum(1 for t in sel if t["result"] == "win")
                                  / len(sel) * 100) if sel else None,
                     "net": st.mean(t["net"] for t in sel) if sel else None,
                     "segments": segs}
    return out


def main():
    print("경로 적재 ...", flush=True)
    allrows = load()
    conf = [t for t in allrows if t["orig"] in ("win", "loss")]
    print("확정 %d건 · M1 %d건" % (len(conf), len(allrows)), flush=True)
    res = {"n_confirmed": len(conf), "n_m1": len(allrows), "equiv_bound": EQUIV,
           "limit": "장중 실제 돌파 시각은 알 수 없다(5.6년치 분봉 없음). "
                    "글자 그대로의 '돌파 순서'는 판정불가로 시작한다."}

    print("\n[동점 진단] (M17-2·M18-2)", flush=True)
    for nm, rs in (("확정 3,681", conf), ("M1 3,776", allrows)):
        td = tie_diag(rs)
        res.setdefault("tie_diag", {})[nm] = td
        print("  %s — 후보 2개+ 인 날 %d일 · 전부 동점 %d일 · 잔여 %d일 · "
              "부분 동점 %d일 · 두 쪽 다 있는 날 %d일"
              % (nm, td["days_k2"], td["all_tied"], td["remaining"],
                 td["partial_tied"], td["days_both_groups"]), flush=True)
    g0 = sum(1 for t in conf if t["gap"] == 0)
    print("  갭업==0 건수 %d / %d = %.1f%% (확정판)" % (g0, len(conf),
                                                   g0 / len(conf) * 100), flush=True)

    res["primary"] = {"confirmed": primary("확정 3,681 (1순위)", conf),
                      "m1": primary("M1 3,776 (부가)", allrows)}

    m = m29_3(conf, day_pairs(conf))
    res["m29_3"] = m
    print("\n[M29-3 정의상 고정·동일 관측] 확정 3,681", flush=True)
    print("  (a) 정렬 세 팔이 **정의상 같은 결과**를 내는 날: 갭업이 전부 같은 날 "
          "%d일 / %d일 = **%.1f%%** · 그 날들의 거래 %d건 / %d건 = **%.1f%%**"
          % (m["sort_inert_days"], m["sort_all_days"], m["sort_inert_day_pct"],
             m["sort_inert_trades"], len(conf), m["sort_inert_trade_pct"]), flush=True)
    print("  (b) 1순위에서 한쪽 무리가 1건뿐이라 그 평균이 거래 하나로 고정되는 날: "
          "%d일(>0쪽 %d · ==0쪽 %d) / %d일 = **%.1f%%** · 거래 %.1f%%"
          % (m["solo_days"], m["solo_a_days"], m["solo_b_days"],
             len(day_pairs(conf)), m["solo_day_pct"], m["solo_trade_pct"]), flush=True)

    print("\n[갭업 구간표] 거래당 순수익 %p · 확정 3,681", flush=True)
    bt = bucket_table(conf)
    res["buckets"] = bt
    for name, _, _ in BUCKETS:
        v = bt[name]
        print("  %-5s n=%4d %s 승률 %5.1f%% · 거래당순 %+7.3f%%p · %s"
              % (name, v["n"], "[참고·판정제외]" if v["thin"] else "              ",
                 v["win_rate"], v["net"],
                 " ".join("%s %s" % (sn, ("n<3" if v["segments"][sn]["n"] < 3
                                          else "%+.2f" % v["segments"][sn]["net"]))
                          for sn, _, _ in SEGMENTS)), flush=True)

    print("\n[부차 슬롯5] 정렬 세 팔 (판정 미사용, M18-1 밴드 폭 병기)", flush=True)
    arms = {"(가) 무작위": None,
            "(나) 갭업 우선": (lambda t: -t["gap"]),
            "(다) 갭업 회피": (lambda t: t["gap"])}
    eqs, fills, wrs = {}, {}, {}
    for nm, od in arms.items():
        e, f, w = [], [], []
        for s in range(N_PAIR):
            r = slot_sim.sim(conf, seed=s, order=od)
            e.append(r["equity_pct"])
            f.append(r["n_filled"])
            w.append(r["win_rate"])
        eqs[nm], fills[nm], wrs[nm] = e, f, w
        lo2, hi2 = ci(e[:N_LEVEL])
        d = [e[i] - eqs["(가) 무작위"][i] for i in range(N_PAIR)] if nm != "(가) 무작위" else None
        rec = {"median": st.median(e[:N_LEVEL]), "band": [lo2, hi2],
               "band_width": hi2 - lo2, "n_filled": st.median(f),
               "win_rate": st.median(w)}
        if d is not None:
            rec.update({"win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
                        "diff_median": st.median(d), "diff_ci": list(ci(d))})
        res.setdefault("slot5", {})[nm] = rec
        print("  %-14s 중앙 %+7.1f%% · 폭 %6.1f%%p · 체결 %4.0f · 승률 %4.1f%%%s"
              % (nm, rec["median"], rec["band_width"], rec["n_filled"], rec["win_rate"],
                 "" if d is None else (" · 우세율(참고) %5.1f%% · 차이중앙 %+6.2f%%p "
                                       "(95%% %+.2f ~ %+.2f)"
                                       % (rec["win_pct"], rec["diff_median"],
                                          rec["diff_ci"][0], rec["diff_ci"][1]))),
              flush=True)

    # 체결 건수 효과와 분리 (지시서 5단계). 감축 대조는 (나)가 **더 많이** 살 때 성립하지 않는다.
    fa = st.median(fills["(가) 무작위"])
    fb = st.median(fills["(나) 갭업 우선"])
    print("\n[체결 건수 효과 분리] 체결 (가) %.0f vs (나) %.0f (%+.1f%%)"
          % (fa, fb, (fb / fa - 1) * 100), flush=True)
    if fb > fa:
        # 갭업 우선이 오히려 더 많이 산다 → "덜 산 효과"로 설명될 차이가 없다.
        # 감축 대조는 건수를 **줄이는** 방향만 만들 수 있으므로 이 방향에는 못 쓴다.
        # 대신 '몇 건을 샀나'와 '무엇을 샀나'를 가르기 위해 **체결분의 거래당 순수익**을 낸다.
        per = {}
        for nm, od in arms.items():
            v = []
            for s in range(min(N_CTRL, N_PAIR)):
                r = slot_sim.sim(conf, seed=s, order=od)
                v.append(r["equity_pct"] / r["n_filled"])
            per[nm] = {"median": st.median(v), "ci": list(ci(v))}
        res["fill_count_split"] = {"applicable": False,
                                   "reason": "(나)가 (가)보다 더 많이 산다 — 감축 대조는 "
                                             "건수를 줄이는 방향만 만들 수 있어 못 쓴다",
                                   "n_filled_a": fa, "n_filled_b": fb,
                                   "per_fill": per}
        print("  (나)가 오히려 더 많이 산다 → '덜 산 효과'로 설명될 차이가 없고, "
              "감축 대조는 이 방향에 쓸 수 없다(건수를 줄이는 방향만 만들 수 있다).", flush=True)
        for nm in arms:
            print("     %-14s 체결 1건당 자산곡선 기여 중앙 %+.4f%%p (95%% %+.4f ~ %+.4f)"
                  % (nm, per[nm]["median"], per[nm]["ci"][0], per[nm]["ci"][1]), flush=True)
    else:
        cr = random.Random(CTRL_SEED)
        ctrl = []
        k = int(round(fa - fb))
        keys = [(t["scan_date"], t["code"], t["pattern"]) for t in conf]
        for s in range(N_CTRL):
            drop = set(cr.sample(keys, k))
            sub = [t for t in conf
                   if (t["scan_date"], t["code"], t["pattern"]) not in drop]
            ctrl.append(slot_sim.sim(sub, seed=s)["equity_pct"])
        d = [eqs["(나) 갭업 우선"][i] - ctrl[i] for i in range(N_CTRL)]
        res["fill_count_split"] = {"applicable": True, "n_dropped": k,
                                   "ctrl_median": st.median(ctrl),
                                   "diff_median": st.median(d), "diff_ci": list(ci(d))}
        print("  무작위 감축 중앙 %+.1f%% · 차이 중앙 %+.2f%%p (95%% %+.2f ~ %+.2f)"
              % (st.median(ctrl), st.median(d), *ci(d)), flush=True)

    (OUT / "10-breakout-order.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/10-breakout-order.json")


if __name__ == "__main__":
    main()
