# -*- coding: utf-8 -*-
"""09 - 연속 손절이면 쉬어라 (페이지 주장 11).

지시서: research/handoff/tasks/09-loss-streak-pause.md (v2 + M10~M25)

1순위(M14-2) = "쉼 규칙 발동일에 산 후보의 승률 vs 전체 평균 승률". 슬롯5는 부차.
동등성 폭 = 승률 ±1.5%p (M16-2). MDE = 2.80 × 블록 부트스트랩 차이 SD (M14).
M16-2-1(환산 효과) · M12-5(감축 대조 복제마다 재추첨) · M9-15(합치기 안 돌림) 준수.
렌즈 넷: L1(발동일 부호검정) · L2′(leave-one-year) · L3(구간 5/5) · L4(집중도).

★ 규칙 정의의 두 읽기 — 지시서 문장이 한쪽을 못 박지 않아 둘 다 돌린다(결과에 보고).
  판(가) 문자 그대로: "직전 결착 N건이 전부 손절"을 매일 다시 판정한다.
        → 쉬는 동안 새 결착이 안 생기므로 조건이 참으로 굳어 영구히 잠긴다.
  판(나) 발동 시 연속 카운터 초기화: M일 쉬고 재개, 다시 N건 연속 손절이 쌓여야 재발동.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/09-loss-streak-pause.py
난수 seed: 슬롯 순서 0~399 · 블록 부트스트랩 90000 · 감축 대조 91000
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
SLOTS = 5
N_SEED_MAIN = 200
N_PAIR = 400
N_LEVEL = 200
N_BOOT = 1000
N_CTRL = 200
BOOT_SEED, CTRL_SEED = 90000, 91000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
EQUIV = 1.5
VARIANTS = [(5, 1), (3, 1), (3, 3), (3, 5), (5, 3), (5, 5)]
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
net = slot_sim.net
_order_cache = {}


def load_trades():
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
            gain = (c[i] / e - 1) * 100
            rows.append({"code": p["code"], "pattern": p["pattern"],
                         "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                         "resolve_date": dts[i], "gain": gain, "reason": why,
                         "year": p["entry_date"][:4],
                         "result": ("win" if why == "target" else
                                    "loss" if why in ("stop", "both_same_day") else
                                    ("win" if gain > 0 else "loss"))})
        print("  경로 %d 적재 · 누적 %d" % (y, len(rows)), flush=True)
    return rows


def get_order(trades, seed):
    o = _order_cache.get(seed)
    if o is None:
        byday = defaultdict(list)
        for t in trades:
            byday[t["entry_date"]].append(t)
        for d in byday:
            byday[d].sort(key=lambda t: (t["code"], t["pattern"], t["scan_date"]))
        o = {d: sorted(v, key=lambda t: slot_sim.order_key(seed, t))
             for d, v in byday.items()}
        _order_cache[seed] = o
    return o


def sim(trades, dates, pos_of, seed, n_streak=None, m_days=0, reset_on_fire=True,
        shrink=False, drop_keys=None, mark_only=False):
    """슬롯5 정본 4 + 쉼 규칙.

    mark_only=True 면 발동일만 표시하고 실제로 쉬지는 않는다(규칙 없음 타임라인).
    reset_on_fire=True 가 판(나), False 가 판(가)(문자 그대로).
    """
    order = get_order(trades, seed)
    eq, held, streak, pause_until, slots = 1.0, [], 0, -1, SLOTS
    filled, fired, skipped = [], [], []
    for i, d in enumerate(dates):
        if held:
            for h in held:
                if not h[3] and h[0] < i:
                    t = h[1]
                    eq += h[2] * net(t["gain"]) / 100
                    h[3] = True
                    if t["reason"] in ("stop", "both_same_day"):
                        streak += 1
                    else:
                        streak = 0
                        if shrink and t["result"] == "win":
                            slots = SLOTS
            held = [h for h in held if h[0] >= i]
        if n_streak is not None and streak >= n_streak and i > pause_until:
            pause_until = i + m_days - 1
            fired.append(d)
            if reset_on_fire:
                streak = 0
        if mark_only:
            pause_until = -1
        if shrink and streak >= 5:
            slots = 2
        cands = order.get(d)
        if cands:
            free = slots - len(held)
            if n_streak is not None and i <= pause_until:
                skipped.extend(cands[:max(0, free)])
            elif free > 0:
                wgt, taken = eq / slots, 0
                for t in cands:
                    if drop_keys is not None and (t["scan_date"], t["code"],
                                                  t["pattern"]) in drop_keys:
                        continue
                    held.append([pos_of[t["resolve_date"]], t, wgt, False])
                    filled.append((d, t))
                    taken += 1
                    if taken >= free:
                        break
    for h in held:
        if not h[3]:
            eq += h[2] * net(h[1]["gain"]) / 100
    return {"equity": (eq - 1) * 100, "filled": filled, "fired": fired,
            "skipped": skipped}


def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(diffs):
    n = len(diffs)
    pos = sum(1 for x in diffs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_pos": pos, "mean": st.mean(diffs), "median": st.median(diffs),
            "p": p, "how": how}


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


def boot_ratio(num_by_date, den_by_date, dates, n_pos, seed):
    """분자/분모를 날짜 단위로 담은 비율에 블록 부트스트랩 95% 구간을 붙인다."""
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        nu = de = 0
        for st_, L in make_blocks(rnd, n_pos):
            for j in range(L):
                d = dates[st_ + j]
                de += den_by_date.get(d, 0)
                nu += num_by_date.get(d, 0)
        if de:
            out.append(nu / de * 100)
    return list(ci(out))


def _day_weight_diag(fire_by_date, wr_a):
    """날 가중과 건 가중이 갈리는 이유를 센다.

    fire_by_date[d] 는 **200개 seed를 합산한** 승패 표식이다. 한 날의 표식 수는
    "그 날이 몇 개 seed에서 발동했는가 × 그날 몇 건 샀는가"다.
    날 가중은 **seed 하나에서만 발동한 날과 200개 전부에서 발동한 날에 같은 한 표**를 준다.
    """
    items = sorted((len(v), st.mean(v) * 100 - wr_a) for v in fire_by_date.values() if v)
    n = len(items)
    tot = sum(a for a, _ in items)
    ter = [items[:n // 3], items[n // 3:2 * n // 3], items[2 * n // 3:]]
    return {"n_days": n,
            "flags_per_day": {"min": items[0][0],
                              "median": st.median([a for a, _ in items]),
                              "max": items[-1][0]},
            "terciles": [{"flags_range": [g[0][0], g[-1][0]], "n_days": len(g),
                          "mean_diff": st.mean([b for _, b in g]),
                          "median_diff": st.median([b for _, b in g]),
                          "share_of_flags": sum(a for a, _ in g) / tot * 100}
                         for g in ter]}


def primary(tag, fire_by_date, all_by_date, dates, n_pos, seed):
    """판정축(건 가중) + 하루 한 표(날 가중) 병기 + 블록 부트스트랩."""
    ff = [x for v in fire_by_date.values() for x in v]
    af = [x for v in all_by_date.values() for x in v]
    wr_f, wr_a = st.mean(ff) * 100, st.mean(af) * 100
    S = wr_f - wr_a
    day_d = [st.mean(v) * 100 - wr_a for d, v in sorted(fire_by_date.items()) if v]
    rnd = random.Random(seed)
    bp, bdm, bdmed = [], [], []
    for _ in range(N_BOOT):
        f, a, dl = [], [], []
        for st_, L in make_blocks(rnd, n_pos):
            for j in range(L):
                d = dates[st_ + j]
                v = fire_by_date.get(d)
                if v:
                    f.extend(v)
                    dl.append(st.mean(v) * 100)
                av = all_by_date.get(d)
                if av:
                    a.extend(av)
        if f and a and dl:
            wa = st.mean(a) * 100
            bp.append(st.mean(f) * 100 - wa)
            bdm.append(st.mean(dl) - wa)
            bdmed.append(st.median(dl) - wa)
    lo, hi = ci(bp)
    sd = st.stdev(bp)
    mde = MDE_K * sd
    excl = lo > 0 or hi < 0
    within = -EQUIV <= lo and hi <= EQUIV
    label = ("폐기(0 제외)" if excl else "유지(동등성)" if within else
             ("판정불가(문턱 사각지대)" if (hi - lo) <= 2 * EQUIV
              else "확인 불가(검정력 부족)"))
    srt = sorted(fire_by_date.items(), key=lambda kv: st.mean(kv[1]) if kv[1] else 0)
    drop5 = {d for d, _ in srt[-5:]}
    f4 = [x for d, v in fire_by_date.items() if d not in drop5 for x in v]
    S4 = st.mean(f4) * 100 - wr_a
    r = {"tag": tag, "n_fire_buys": len(ff), "n_all_buys": len(af),
         "wr_fire": wr_f, "wr_all": wr_a, "S": S, "ci": [lo, hi],
         "ci_width": hi - lo, "sd": sd, "MDE": mde, "excludes_zero": excl,
         "within_equiv": within, "verdict_axis": label,
         "day_mean": st.mean(day_d), "day_mean_ci": list(ci(bdm)),
         "day_median": st.median(day_d), "day_median_ci": list(ci(bdmed)),
         "n_fire_days": len(day_d), "sign": sign_test(day_d),
         "L4_top5_removed": S4,
         "day_weight_diag": _day_weight_diag(fire_by_date, wr_a)}
    print("\n[1순위] %s  발동일 후보 승률 vs 전체" % tag, flush=True)
    print("   건 가중(판정축) 발동일 %d건 %.3f%% vs 전체 %d건 %.3f%% -> 차이 %+.3f%%p"
          % (len(ff), wr_f, len(af), wr_a, S), flush=True)
    print("   블록 부트 95%% %+.3f ~ %+.3f (폭 %.3f%%p) · SD %.3f · MDE %.3f%%p · "
          "0제외 %s · +-1.5%%p 안 %s -> %s"
          % (lo, hi, hi - lo, sd, mde, "예" if excl else "아니오",
             "예" if within else "아니오", label), flush=True)
    print("   날 가중(하루 한 표, %d일) 평균 %+.3f%%p (95%% %+.3f ~ %+.3f) · "
          "중앙 %+.3f%%p (95%% %+.3f ~ %+.3f)"
          % (len(day_d), r["day_mean"], r["day_mean_ci"][0], r["day_mean_ci"][1],
             r["day_median"], r["day_median_ci"][0], r["day_median_ci"][1]), flush=True)
    return r


def main():
    print("경로 적재 ...", flush=True)
    trades = load_trades()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in trades)
    hi_d = max(t["resolve_date"] for t in trades)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    trades = [t for t in trades if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    n_pos = len(dates)
    print("거래 %d건 · 달력 %d거래일" % (len(trades), n_pos), flush=True)
    res = {"n_trades": len(trades), "n_calendar": n_pos, "equiv_bound": EQUIV}

    N1, M1 = 5, 1
    acc = {}
    for reset in (False, True):
        tag = "판(나) 발동시 초기화" if reset else "판(가) 문자 그대로"
        fb, ab = defaultdict(list), defaultdict(list)
        nfd, nbd, nfb, nab = [], [], [], []
        wipe_tot, wipe_fire, good_tot, good_fire = [], [], [], []
        # M25: 페이지 숫자와 견주려면 비율에도 구간이 필요하다 → 날짜별로 seed 합산해 둔다
        wd, wfd = defaultdict(int), defaultdict(int)
        gd, gfd = defaultdict(int), defaultdict(int)
        for s in range(N_SEED_MAIN):
            r = sim(trades, dates, pos_of, s, n_streak=N1, m_days=M1,
                    reset_on_fire=reset, mark_only=True)
            fired = set(r["fired"])
            by = defaultdict(list)
            for d, t in r["filled"]:
                by[d].append(t)
            nf = 0
            wt = wf = gt = gf = 0
            for d, ts in by.items():
                fl = [1 if x["result"] == "win" else 0 for x in ts]
                ab[d].extend(fl)
                if d in fired:
                    fb[d].extend(fl)
                    nf += len(fl)
                if sum(fl) == 0:
                    wt += 1
                    wf += (d in fired)
                    wd[d] += 1
                    wfd[d] += (d in fired)
                if sum(fl) == len(fl):
                    gt += 1
                    gf += (d in fired)
                    gd[d] += 1
                    gfd[d] += (d in fired)
            nfd.append(len(fired))
            nbd.append(len(by))
            nfb.append(nf)
            nab.append(len(r["filled"]))
            wipe_tot.append(wt)
            wipe_fire.append(wf)
            good_tot.append(gt)
            good_fire.append(gf)
            if (s + 1) % 100 == 0:
                print("  1순위 %s seed %d/%d" % (tag, s + 1, N_SEED_MAIN), flush=True)
        p = primary(tag, fb, ab, dates, n_pos, BOOT_SEED + (1 if reset else 0))
        share = st.mean(nfb) / st.mean(nab)
        p["m16_2_1"] = {"fire_days": st.mean(nfd), "buy_days": st.mean(nbd),
                        "fire_day_pct": st.mean(nfd) / st.mean(nbd) * 100,
                        "missed_buys": st.mean(nfb), "all_buys": st.mean(nab),
                        "share": share, "portfolio_effect": p["S"] * share}
        print("   [M16-2-1] (1)쉰 날 %.1f / 매수있는 날 %.1f (%.1f%%)  "
              "(2)못 산 후보 %.1f / 전체 진입 %.1f (%.1f%%)  "
              "(3)%+.3f%%p x %.3f = 포트폴리오 환산 %+.4f%%p"
              % (st.mean(nfd), st.mean(nbd), p["m16_2_1"]["fire_day_pct"],
                 st.mean(nfb), st.mean(nab), share * 100, p["S"], share,
                 p["m16_2_1"]["portfolio_effect"]), flush=True)
        wci = boot_ratio(wfd, wd, dates, n_pos, BOOT_SEED + 10 + (1 if reset else 0))
        gci = boot_ratio(gfd, gd, dates, n_pos, BOOT_SEED + 20 + (1 if reset else 0))
        p["page_claim"] = {
            "wipeout_days": st.mean(wipe_tot), "wipeout_avoided": st.mean(wipe_fire),
            "wipeout_pct": st.mean(wipe_fire) / st.mean(wipe_tot) * 100,
            "wipeout_ci": wci, "page_wipeout_pct": 100 / 14,
            "page_wipeout_inside": bool(wci[0] <= 100 / 14 <= wci[1]),
            "good_days": st.mean(good_tot), "good_missed": st.mean(good_fire),
            "good_pct": st.mean(good_fire) / st.mean(good_tot) * 100, "good_ci": gci}
        print("   [페이지 대조] 전멸일 %.1f일 중 %.1f일 회피 = %.2f%% "
              "(95%% %.2f ~ %.2f) · 페이지 1/14 = 7.14%% → 구간 %s"
              % (st.mean(wipe_tot), st.mean(wipe_fire), p["page_claim"]["wipeout_pct"],
                 wci[0], wci[1], "안" if p["page_claim"]["page_wipeout_inside"] else "밖"),
              flush=True)
        print("                전승일 %.1f일 중 %.1f일 놓침 = %.2f%% (95%% %.2f ~ %.2f) "
              "· 페이지는 '2일'이라 비율이 없다(건수만 주장)"
              % (st.mean(good_tot), st.mean(good_fire), p["page_claim"]["good_pct"],
                 gci[0], gci[1]), flush=True)
        dyr, segs = {}, {}
        for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
            f = [x for d, v in fb.items() if d[:4] != y for x in v]
            a = [x for d, v in ab.items() if d[:4] != y for x in v]
            dyr[y] = (st.mean(f) * 100 - st.mean(a) * 100) if f and a else None
        for sn, y0, y1 in SEGMENTS:
            f = [x for d, v in fb.items() if y0 <= d[:4] <= y1 for x in v]
            a = [x for d, v in ab.items() if y0 <= d[:4] <= y1 for x in v]
            segs[sn] = {"n": len(f),
                        "diff": (st.mean(f) * 100 - st.mean(a) * 100) if f and a else None}
        sg = 1 if p["S"] > 0 else -1
        # L1 은 다른 렌즈와 같이 **판정축과 부호가 맞을 때만** 통과로 센다.
        # 유의하기만 하고 반대 방향이면 뒷받침이 아니다.
        l1_sig = bool(p["sign"]["p"] < 0.05
                      and (p["day_median_ci"][0] > 0 or p["day_median_ci"][1] < 0))
        p["L1_significant_only"] = l1_sig
        p["L1_sign_matches"] = bool((p["day_median"] > 0) == (sg > 0))
        lens = {"L1": bool(l1_sig and (p["day_median"] > 0) == (sg > 0)),
                "L2p": all(v is not None and (v > 0) == (sg > 0) for v in dyr.values()),
                "L3": all(v["diff"] is not None and (v["diff"] > 0) == (sg > 0)
                          for v in segs.values()),
                "L4": (p["L4_top5_removed"] > 0) == (sg > 0)}
        p["lenses"] = {"L2p": dyr, "L3": segs, "pass": lens,
                       "n_passed": sum(lens.values())}
        dw = p["day_weight_diag"]
        print("   [날 가중 진단] 발동일 %d일 · 날별 표식 수(200 seed 합산) "
              "최소 %d · 중앙 %.0f · 최대 %d"
              % (dw["n_days"], dw["flags_per_day"]["min"],
                 dw["flags_per_day"]["median"], dw["flags_per_day"]["max"]), flush=True)
        for g in dw["terciles"]:
            print("      표식수 %5d~%5d (%3d일 · 전체 표식의 %5.1f%%) "
                  "평균 %+8.3f%%p · 중앙 %+8.3f%%p"
                  % (g["flags_range"][0], g["flags_range"][1], g["n_days"],
                     g["share_of_flags"], g["mean_diff"], g["median_diff"]), flush=True)
        print("   [렌즈] L1 %d일 중 양수 %d p=%.4f(%s) -> %s · L2p %s -> %s · "
              "L3 %s -> %s · L4 %+.3f -> %+.3f -> %s · 합계 %d/4"
              % (p["sign"]["n"], p["sign"]["n_pos"], p["sign"]["p"], p["sign"]["how"],
                 ("통과" if lens["L1"] else
                  ("미통과(유의하나 판정축과 반대 부호)" if l1_sig else "미통과")),
                 {k: (None if v is None else round(v, 2)) for k, v in dyr.items()},
                 "통과" if lens["L2p"] else "미통과",
                 {k: (None if v["diff"] is None else round(v["diff"], 2))
                  for k, v in segs.items()},
                 "통과" if lens["L3"] else "미통과",
                 p["S"], p["L4_top5_removed"], "통과" if lens["L4"] else "미통과",
                 sum(lens.values())), flush=True)
        acc["reset" if reset else "literal"] = p
    res["primary"] = acc

    print("\n[부차 슬롯5] (판정 미사용, M18-1 밴드 폭 병기)", flush=True)
    base = [sim(trades, dates, pos_of, s)["equity"] for s in range(N_PAIR)]
    base_f = len(sim(trades, dates, pos_of, 0)["filled"])
    bl, bh = ci(base[:N_LEVEL])
    print("  규칙없음            중앙 %+7.1f%% · 폭 %6.1f%%p · 체결 %4d"
          % (st.median(base[:N_LEVEL]), bh - bl, base_f), flush=True)
    var = {}

    def arm(name, **kw):
        eqs, fills = [], []
        for s in range(N_PAIR):
            r = sim(trades, dates, pos_of, s, **kw)
            eqs.append(r["equity"])
            fills.append(len(r["filled"]))
        d = [eqs[i] - base[i] for i in range(N_PAIR)]
        lo2, hi2 = ci(eqs[:N_LEVEL])
        v = {"median": st.median(eqs[:N_LEVEL]), "band": [lo2, hi2],
             "band_width": hi2 - lo2, "n_filled": st.median(fills),
             "win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
             "diff_median": st.median(d), "diff_ci": list(ci(d))}
        var[name] = v
        print("  %-20s 중앙 %+7.1f%% · 폭 %6.1f%%p · 체결 %4.0f · 우세율(참고) %5.1f%% · "
              "차이중앙 %+7.1f%%p" % (name, v["median"], v["band_width"], v["n_filled"],
                                    v["win_pct"], v["diff_median"]), flush=True)
        return v

    for (n_, m_) in VARIANTS:
        arm("N=%d M=%d 판(나)" % (n_, m_), n_streak=n_, m_days=m_, reset_on_fire=True)
    arm("N=5 M=1 판(가)", n_streak=5, m_days=1, reset_on_fire=False)
    arm("슬롯 5->2 축소", shrink=True)
    res["slot5"] = {"base_median": st.median(base[:N_LEVEL]),
                    "base_band_width": bh - bl, "base_filled": base_f,
                    "variants": var}

    print("\n[같은 건수 무작위 감축 대조] 복제마다 재추첨 (M12-5)", flush=True)
    cr = random.Random(CTRL_SEED)
    ctrl, rule = [], []
    for s in range(N_CTRL):
        r = sim(trades, dates, pos_of, s, n_streak=5, m_days=1, reset_on_fire=True)
        bf = sim(trades, dates, pos_of, s)["filled"]
        rule.append(r["equity"])
        k = len(bf) - len(r["filled"])
        keys = [(t["scan_date"], t["code"], t["pattern"]) for _, t in bf]
        drop = set(cr.sample(keys, k)) if 0 < k <= len(keys) else set()
        ctrl.append(sim(trades, dates, pos_of, s, drop_keys=drop)["equity"])
    dd = [rule[i] - ctrl[i] for i in range(N_CTRL)]
    dlo, dhi = ci(dd)
    res["same_count_control"] = {"rule_median": st.median(rule),
                                 "ctrl_median": st.median(ctrl),
                                 "rule_band": list(ci(rule)), "ctrl_band": list(ci(ctrl)),
                                 "diff_median": st.median(dd), "diff_ci": [dlo, dhi],
                                 "excludes_zero": bool(dlo > 0 or dhi < 0)}
    print("  쉼 N=5 M=1 판(나) 중앙 %+.1f%% · 무작위 감축 중앙 %+.1f%% · "
          "차이 중앙 %+.1f%%p (95%% %+.1f ~ %+.1f) 0제외 %s"
          % (st.median(rule), st.median(ctrl), st.median(dd), dlo, dhi,
             "예" if res["same_count_control"]["excludes_zero"] else "아니오"), flush=True)

    (OUT / "09-loss-streak-pause.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/09-loss-streak-pause.json")


if __name__ == "__main__":
    main()
