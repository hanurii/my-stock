# -*- coding: utf-8 -*-
"""82 — **지수 스위칭을 «커밋된 스크립트»로 처음 만든다**. 사전등록 `tasks/82-index-switch-rebuilt.md`

🚨 70번에는 산출 스크립트가 «없다». `+442.61%` · `+423.41%` · 메모리의 `+417.10%` 전부
   재현 경로가 없는 값이다. **82번은 재현이 아니라 처음 만들기다.**
🚨 **`+417.10%` 를 맞히는 것이 목적이 아니다.** 맞으면 우연이고, 안 맞으면 82번이 정본이다.

규칙(사전등록 §1):
```
매월 첫 거래일에, «직전 거래일» 종가로 S&P500 > 200MA 인가
  on  → 그 달은 매매          off → 그 달은 지수를 든다
청산/매수 = off 달 «첫 거래일 종가»   ·   재개 = on 달 «첫 거래일 종가»
전환비용 = 방향마다 한 번씩
```

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/82-index-switch.py [--quick]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r74", HERE / "74-pyramid-rebuilt.py")
r74 = _u.module_from_spec(_s)
_s.loader.exec_module(r74)
r41 = r74.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST = r74.COST                       # 우대수수료 (0.0, 0.002)
SLOTS, RISK, CAP = r74.SLOTS, r74.RISK, r74.CAP
N_SEED = 200
N_RAND = 300
N_RAND_SEED = 5                       # 무작위 대조는 «관측도 같은 판수»로 비교한다
SWITCH_COSTS = (0.0, 0.002, 0.005, 0.010, 0.020)
HEADLINE_COST = 0.002
NASDAQ_9Y = 307.73                    # 72번 — C 문턱
SP_ALWAYS = None                      # ②에서 계산해 채운다


# ═════════════════════════════════════════════════════════════════════════
# 1. 지수와 깃발
# ═════════════════════════════════════════════════════════════════════════
def load_index(name="US500"):
    d = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))[name]
    cal = sorted(d)
    return cal, [d[k] for k in cal]


def ma_above(cal, v, w):
    """날짜 → (그날 종가 ≥ 그날까지의 w일 단순평균).  자료 부족이면 None."""
    out, run = {}, 0.0
    for i, d in enumerate(cal):
        run += v[i]
        if i >= w:
            run -= v[i - w]
        out[d] = None if i + 1 < w else (v[i] >= run / w)
    return out


def month_flags(cal, above):
    """달 → on?  «그 달 첫 거래일의 직전 거래일» 종가로 판정 (룩어헤드 없음)."""
    on, first = {}, {}
    for i, d in enumerate(cal):
        ym = d[:7]
        if ym in on:
            continue
        first[ym] = d
        f = above.get(cal[i - 1]) if i > 0 else None
        on[ym] = True if f is None else f          # 자료 부족 = 막지 않는다
    return on, first


def spans(cal, on):
    """지수를 «드는» 구간 = [off 달 첫 거래일, 다음 on 달 첫 거래일] (양 끝 종가 포함).

    반환: (idx_hold, no_entry, n_switch)
      idx_hold  날짜 → 그날 «종가 이후» 지수를 들고 있나 (구간 시작일 포함)
      no_entry  진입이 «없는» 날 = off 달 전체 ∪ 재개일
    """
    idx_hold, no_entry, n_sw = {}, set(), 0
    i, n = 0, len(cal)
    while i < n:
        if on.get(cal[i][:7], True):
            i += 1
            continue
        # off 구간 시작
        j = i
        while j < n and not on.get(cal[j][:7], True):
            no_entry.add(cal[j])
            j += 1
        end = j if j < n else n - 1        # 재개일 (자료가 끝나면 마지막 날)
        for k in range(i, end + 1):
            idx_hold[cal[k]] = True
        if j < n:
            no_entry.add(cal[end])          # 재개일 «종가»에 지수를 판다 → 그날은 안 산다
        n_sw += 2 if j < n else 1
        i = j + 1
    return idx_hold, no_entry, n_sw


# ═════════════════════════════════════════════════════════════════════════
# 2. 거래를 «자른다» — 경로 재해결 없이 exits 만 손본다
# ═════════════════════════════════════════════════════════════════════════
def cut_events(ev, pmap, no_entry, idx_hold, cal):
    """off 달 첫 거래일 종가에 전량 청산 + off 달 진입 차단.

    🚨 `open_until` 은 «자르기 전» 결착일로 이미 정해졌다. 자르면 실제로는 더 일찍
       풀려 재진입이 가능해지지만 여기서는 «안 늘린다» → **보수적**이다. 한계에 적는다.
    """
    starts = sorted(d for d in idx_hold if not idx_hold.get(_prev(cal, d)))
    out, n_cut, n_block, n_gone = [], 0, 0, 0
    for t in ev:
        if t["entry_date"] in no_entry:
            n_block += 1
            continue
        m = t["masks"][()]
        ex = m["exits"]
        if not ex:
            out.append(t)
            continue
        last = ex[-1][0]
        k = bisect.bisect_right(starts, t["entry_date"])
        if k >= len(starts) or starts[k] > last:
            out.append(t)
            continue
        cut = starts[k]
        p = pmap.get((t["scan_date"], t["code"], t["pattern"]))
        if p is None:
            out.append(t)
            continue
        try:
            j = p["d"].index(cut)
        except ValueError:
            out.append(t)
            continue
        keep = [e for e in ex if e[0] < cut]
        rest = 1.0 - sum(e[1] for e in keep)
        if rest <= 1e-9:
            out.append(t)
            continue
        new_ex = keep + [(cut, rest, p["c"][j])]
        gain = sum(f * (px / t["entry_px"] - 1) for _d, f, px in new_ex)
        out.append({**t, "masks": {(): {**m, "exits": new_ex, "resolve_date": cut,
                                        "result": "win" if gain > 0 else "loss",
                                        "at_end": False}}})
        n_cut += 1
        n_gone += (not keep)
    return out, n_cut, n_block, n_gone


def _prev(cal, d):
    i = bisect.bisect_left(cal, d)
    return cal[i - 1] if i > 0 else None


# ═════════════════════════════════════════════════════════════════════════
# 3. 지수 다리를 «곡선 위에» 얹는다
# ═════════════════════════════════════════════════════════════════════════
def overlay_fold(curve, idx_hold, ipx, cost):
    """`overlay` 의 «정산까지» 판 — 재개일 종가에 지수를 팔고 그 값을 이후에 곱한다."""
    out, mult, anchor, n_sw = [], 1.0, None, 0
    prev_in = False
    for d, eq in curve:
        now_in = bool(idx_hold.get(d))
        if now_in and not prev_in:
            mult *= (1.0 - cost)
            anchor = ipx(d)
            n_sw += 1
        if (not now_in) and prev_in:
            mult *= (ipx(_last_in) / anchor) * (1.0 - cost)
            n_sw += 1
        out.append((d, eq * mult * (ipx(d) / anchor if now_in else 1.0)))
        if now_in:
            _last_in = d                            # noqa: F841
        prev_in = now_in
    if prev_in:                                    # 자료 끝까지 지수를 든 채 끝났다
        mult *= (ipx(_last_in) / anchor) * (1.0 - cost)
        n_sw += 1
        out[-1] = (out[-1][0], curve[-1][1] * mult)
    return out, n_sw


def eq_of(curve):
    return (curve[-1][1] - 1.0) * 100.0


def mdd_of(curve):
    peak, mdd = -1e18, 0.0
    for _d, v in curve:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return mdd * 100.0


# ═════════════════════════════════════════════════════════════════════════
def run_sims(ev, n_seed):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def main() -> int:
    global SP_ALWAYS
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    n_rand = 30 if quick else N_RAND
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2

    print("=" * 100, flush=True)
    print("82 — 지수 스위칭을 «커밋된 스크립트»로 처음 만든다 (사전등록 tasks/82)", flush=True)
    print("=" * 100, flush=True)

    by2, n_all, n_sel, n_ext = r74.load_filtered()
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}
    ev0, blk, _sp = r74.replay_masks(by2, (1.0,), "floor_entry")
    print("경로 %d → 조합 %d (%.1f%%) · 진입 **%d** · seed %d"
          % (n_all, n_sel, 100.0 * n_sel / n_all, len(ev0), n_seed), flush=True)

    cal, v = load_index("US500")
    ipx_d = dict(zip(cal, v))
    ci = sorted(ipx_d)

    def ipx(d):
        i = bisect.bisect_right(ci, d) - 1
        return ipx_d[ci[max(0, i)]]

    above = ma_above(cal, v, 200)
    on, first = month_flags(cal, above)
    idx_hold, no_entry, n_sw_flag = spans(cal, on)
    n_off_m = sum(1 for m in on if not on[m])
    print("깃발 — 달 %d개 중 off **%d개(%.1f%%)** · off 거래일 %d(%.1f%%) · 전환 **%d회 = 연 %.1f회**"
          % (len(on), n_off_m, 100.0 * n_off_m / len(on), sum(1 for d in cal if idx_hold.get(d)),
             100.0 * sum(1 for d in cal if idx_hold.get(d)) / len(cal),
             n_sw_flag, n_sw_flag / 8.956), flush=True)
    print("   off 달 %s"
          % ", ".join(sorted(m for m in on if not on[m]))[:220], flush=True)

    # ── 관문 ③ ─────────────────────────────────────────────────────────
    frac = 100.0 * n_off_m / len(on)
    ok3 = 5.0 < 100.0 - frac < 95.0
    print("\n관문 ③  깃발이 상수가 아닌가 (on 비율 %.1f%%) → **%s**"
          % (100.0 - frac, "통과" if ok3 else "🚨 미통과"), flush=True)
    if not ok3:
        return 3

    # ── 바탕 ────────────────────────────────────────────────────────────
    base = run_sims(ev0, n_seed)
    base_eq = sorted(r["equity_pct"] for r in base)
    BASE = st.median(base_eq)
    print("\n바탕 (스위칭 «없음» · 74번 P0)  자산 중앙 **%+.2f%%** · 하위5%% %+.2f%% · MDD %.1f%%"
          % (BASE, base_eq[int(n_seed * .05)], st.median(r["mdd_pct"] for r in base)),
          flush=True)

    # ── 관문 ① 항상 켜짐 ────────────────────────────────────────────────
    ev_on, c1, b1, _g = cut_events(ev0, pmap, set(), {}, cal)
    r_on = run_sims(ev_on, min(20, n_seed))
    w1 = max(abs(a["equity_pct"] - b["equity_pct"]) / max(1e-12, abs(a["equity_pct"]))
             for a, b in zip(base[:len(r_on)], r_on))
    print("관문 ①  깃발 «항상 켜짐» = 바탕  (자르기 %d · 차단 %d)  %.3e → **%s**"
          % (c1, b1, w1, "통과" if w1 < 1e-9 else "🚨 미통과"), flush=True)
    if w1 >= 1e-9:
        return 3

    # ── 관문 ② 항상 꺼짐 ────────────────────────────────────────────────
    all_hold = {d: True for d in cal}
    ev_off, c2, b2, _g2 = cut_events(ev0, pmap, set(cal), all_hold, cal)
    flat = [(d, 1.0) for d in cal]
    cv2, sw2 = overlay_fold(flat, all_hold, ipx, HEADLINE_COST)
    want = (ipx(cal[-1]) / ipx(cal[0])) * (1 - HEADLINE_COST) ** 2
    got = cv2[-1][1]
    print("관문 ②  깃발 «항상 꺼짐» = 지수 보유 × (1−비용)²  (진입 %d 남음)  %.3e → **%s**"
          % (len(ev_off), abs(got - want) / want, "통과" if abs(got - want) / want < 1e-9
             else "🚨 미통과"), flush=True)
    if abs(got - want) / want >= 1e-9:
        return 3
    w0, w1_ = base[0]["curve"][0][0], base[0]["curve"][-1][0]
    SP_ALWAYS = (ipx(w1_) / ipx(w0) - 1) * 100
    print("        (항상 지수 = **%+.2f%%** — 우리 곡선과 «같은 창» %s ~ %s)"
          % (SP_ALWAYS, w0, w1_), flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    ev_sw, n_cut, n_block, n_gone = cut_events(ev0, pmap, no_entry, idx_hold, cal)
    print("\n관문 ④  강제청산 **%d건** · 차단된 진입 **%d건** · 진입 %d → **%d**"
          % (n_cut, n_block, len(ev0), len(ev_sw)), flush=True)
    print("        (그중 «다리 하나도 못 내고» 통째로 잘린 것 %d건)" % n_gone, flush=True)

    # ── ★ 분해 — 스위칭은 «두 조각»이다 (진입차단 · 강제청산) ────────────
    print(chr(10) + "★ 분해 — 스위칭 규칙의 «두 조각»을 따로 켜 본다 (seed %d)" % n_seed,
          flush=True)
    print("  %-20s %6s %6s %12s %9s %12s"
          % ("칸", "진입", "체결", "자산중앙", "MDD", "거래당산술"), flush=True)
    print("  " + "-" * 72, flush=True)
    DEC = {}
    for nm, neu, ihu in (("바탕(둘 다 없음)", set(), {}),
                         ("㉠ 진입차단만", no_entry, {}),
                         ("㉡ 강제청산만", set(), idx_hold),
                         ("㉢ 둘 다(=현금판)", no_entry, idx_hold)):
        evd, _c, _b, _g = cut_events(ev0, pmap, neu, ihu, cal)
        rd = run_sims(evd, n_seed)
        DEC[nm] = {"equity": st.median(r["equity_pct"] for r in rd),
                   "mdd": st.median(r["mdd_pct"] for r in rd),
                   "arith": st.median(r["arith_pct"] for r in rd),
                   "n_entry": len(evd),
                   "n_filled": st.median(r["n_filled"] for r in rd)}
        d = DEC[nm]
        print("  %-20s %6d %6d %+11.2f%% %8.1f%% %+11.2f%%"
              % (nm, d["n_entry"], d["n_filled"], d["equity"], d["mdd"], d["arith"]),
              flush=True)

    # 막힌 진입이 «누구»였나
    def _g1(t):
        return sum(f * (px / t["entry_px"] - 1) * 100 for _d, f, px in t["masks"][()]["exits"])
    bl = [(_g1(t), t["code"], t["entry_date"]) for t in ev0 if t["entry_date"] in no_entry]
    kp = [_g1(t) for t in ev0 if t["entry_date"] not in no_entry]
    print("  막힌 진입 n=%d 평균 **%+.3f%%** · ≥+50%% %d건   |   "
          "남은 것 n=%d 평균 **%+.3f%%** · ≥+50%% %d건"
          % (len(bl), st.mean(x for x, _c, _d in bl), sum(1 for x, _c, _d in bl if x >= 50),
             len(kp), st.mean(kp), sum(1 for x in kp if x >= 50)), flush=True)
    bl.sort(reverse=True)
    print("  막힌 것 중 최고 5건: %s"
          % " · ".join("%s %s %+.1f%%" % (c, d, x) for x, c, d in bl[:5]), flush=True)
    from collections import Counter as _C
    print("  막힌 진입의 달별 %s" % dict(sorted(_C(d[:7] for _x, _c, d in bl).items())),
          flush=True)

    sw = run_sims(ev_sw, n_seed)
    curves = [r["curve"] for r in sw]
    # 관문 ④′ — off 구간에서 자산이 «평평»한가 (지수 얹기 «전»)
    bad = 0
    for d0, e0 in zip(curves[0][:-1], curves[0][1:]):
        if idx_hold.get(d0[0]) and idx_hold.get(e0[0]) and abs(e0[1] - d0[1]) > 1e-12:
            bad += 1
    print("관문 ④′ off 구간에서 지수 얹기 «전» 자산이 평평한가 — 어긋난 날 %d → **%s**"
          % (bad, "통과" if bad == 0 else "🚨 미통과"), flush=True)

    print("\n" + "─" * 100, flush=True)
    print("본체 — 전환비용별 (seed %d 중앙)" % n_seed, flush=True)
    print("  %8s %12s %12s %9s %9s" % ("전환비용", "자산중앙", "운나쁠때", "MDD", "나스닥위"),
          flush=True)
    print("  " + "-" * 56, flush=True)
    RES, head_curves = {}, None
    for c in SWITCH_COSTS:
        cvs = [overlay_fold(cv, idx_hold, ipx, c)[0] for cv in curves]
        eqs = sorted(eq_of(x) for x in cvs)
        m = st.median(eqs)
        RES[c] = {"equity": m, "p5": eqs[int(n_seed * .05)],
                  "mdd": st.median(mdd_of(x) for x in cvs)}
        if abs(c - HEADLINE_COST) < 1e-12:
            head_curves = cvs
        print("  %7.1f%% %+11.2f%% %+11.2f%% %8.1f%% %9s"
              % (c * 100, m, RES[c]["p5"], RES[c]["mdd"],
                 "✅" if m > NASDAQ_9Y else "❌"), flush=True)

    HEAD = RES[HEADLINE_COST]["equity"]

    # ── D. 「쉰다(현금)」 ────────────────────────────────────────────────
    cash_eqs = sorted(eq_of(cv) for cv in curves)
    CASH = st.median(cash_eqs)
    d_gap = abs(CASH - BASE)
    print("\nD  「쉰다(현금)」 %+.2f%%  vs  바탕 %+.2f%%   차 **%.2f%%p** (문턱 %.1f%%p) → **%s**"
          % (CASH, BASE, d_gap, 0.05 * abs(BASE),
             "통과 — 70번 발견 재현" if d_gap < 0.05 * abs(BASE) else "미통과"), flush=True)
    print("   → 「지수를 산다」가 더하는 몫 = **%+.2f%%p**" % (HEAD - CASH), flush=True)

    # ── F. 짝비교 ───────────────────────────────────────────────────────
    pr = sorted(((1 + eq_of(a) / 100) / (1 + b["equity_pct"] / 100) - 1) * 100
                for a, b in zip(head_curves, base))
    pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
    print("\nF  짝지은 %d판 (같은 seed 안에서만) — 중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · "
          "**이기는 판 %.1f%%** → **%s**"
          % (n_seed, pr[len(pr) // 2], pr[int(len(pr) * .05)], pw,
             "통과" if pr[len(pr) // 2] > 0 and pw > 50 else "미통과"), flush=True)

    # ── B. 무작위 대조 ──────────────────────────────────────────────────
    print("\nB  무작위 대조 %d판 — 같은 on-비율로 달 이름표를 섞는다 (seed %d 중앙으로 비교)"
          % (n_rand, N_RAND_SEED), flush=True)
    months = sorted(on)
    lbl = [on[m] for m in months]
    obs_small = st.median(eq_of(x) for x in
                          [overlay_fold(cv, idx_hold, ipx, HEADLINE_COST)[0]
                           for cv in curves[:N_RAND_SEED]])
    rnd = random.Random(20260826)
    nulls, nulls_blk = [], []
    for mode, store in (("shuffle", nulls), ("block", nulls_blk)):
        for it in range(n_rand):
            if mode == "shuffle":
                z = lbl[:]
                rnd.shuffle(z)
            else:
                k = rnd.randrange(1, len(lbl))
                z = lbl[k:] + lbl[:k]            # 회전 — 자기상관 보존
            fake = dict(zip(months, z))
            ih, ne, _n = spans(cal, fake)
            evf, _c, _b, _g = cut_events(ev0, pmap, ne, ih, cal)
            rs = run_sims(evf, N_RAND_SEED)
            store.append(st.median(
                eq_of(overlay_fold(r["curve"], ih, ipx, HEADLINE_COST)[0]) for r in rs))
            if it % 50 == 0:
                print("     %s %d/%d" % (mode, it, n_rand), flush=True)
    for nm, arr in (("섞기(등록된 것)", nulls), ("회전(자기상관 보존·추가)", nulls_blk)):
        a = sorted(arr)
        print("  %-22s 보통 %+8.2f%% · 95%% %+8.2f%% · **최대 %+8.2f%%**  vs 관측 %+8.2f%% → **%s**"
              % (nm, a[len(a) // 2], a[int(len(a) * .95)], a[-1], obs_small,
                 "통과" if obs_small > a[-1] else "미통과"), flush=True)

    # ── E. 연도 검정 ────────────────────────────────────────────────────
    print("\nE  연도 검정 — 한 해를 빼고 다시 쌓아도 「항상 지수」 위인가", flush=True)
    yr_ours = _year_factors(head_curves[len(head_curves) // 2])
    idx_curve = [(d, ipx(d) / ipx(w0)) for d in cal if w0 <= d <= w1_]
    yr_idx = _year_factors(idx_curve)
    years = sorted(set(yr_ours) & set(yr_idx))
    win = 0
    print("  %6s %11s %11s" % ("뺀 해", "우리", "항상지수"), flush=True)
    for y in years:
        a = _prod(yr_ours, skip=y)
        b = _prod(yr_idx, skip=y)
        win += a > b
        print("  %6s %+10.2f%% %+10.2f%% %s"
              % (y, (a - 1) * 100, (b - 1) * 100, "✅" if a > b else "❌"), flush=True)
    print("  → **%d / %d** (문턱 ≥ 8/9)" % (win, len(years)), flush=True)

    # ── 50MA 부수 ───────────────────────────────────────────────────────
    ab50 = ma_above(cal, v, 50)
    on50, _f50 = month_flags(cal, ab50)
    ih50, ne50, sw50 = spans(cal, on50)
    ev50, _c, _b, _g = cut_events(ev0, pmap, ne50, ih50, cal)
    r50 = run_sims(ev50, min(40, n_seed))
    e50 = st.median(eq_of(overlay_fold(r["curve"], ih50, ipx, HEADLINE_COST)[0]) for r in r50)
    print("\n부수 — 50MA 판(전환 %d회): **%+.2f%%** (seed %d) · 200MA 판 %+.2f%% (seed %d)"
          % (sw50, e50, min(40, n_seed), HEAD, n_seed), flush=True)

    # ── 판정 ────────────────────────────────────────────────────────────
    print("\n" + "=" * 100, flush=True)
    print("사전등록 §2 판정", flush=True)
    A = HEAD > BASE
    B = obs_small > sorted(nulls)[-1]
    C = RES[HEADLINE_COST]["equity"] > NASDAQ_9Y
    D = d_gap < 0.05 * abs(BASE)
    E = win >= 8
    F = pr[len(pr) // 2] > 0 and pw > 50
    for k, ok, txt in (("A★", A, "스위칭 %+.2f%% > 바탕 %+.2f%%" % (HEAD, BASE)),
                       ("B★", B, "무작위 300판 최대 %+.2f%% vs 관측 %+.2f%%"
                        % (sorted(nulls)[-1], obs_small)),
                       ("C ", C, "%+.2f%% vs 나스닥 %+.2f%%" % (HEAD, NASDAQ_9Y)),
                       ("D ", D, "현금판 차 %.2f%%p" % d_gap),
                       ("E ", E, "%d/%d" % (win, len(years))),
                       ("F ", F, "짝 중앙 %+.2f%% · 이기는 판 %.1f%%"
                        % (pr[len(pr) // 2], pw))):
        print("  %s  %s  — %s" % (k, "✅ 통과" if ok else "❌ 미통과", txt), flush=True)

    (OUT / "82-index-switch.json").write_text(json.dumps(
        {"base": BASE, "head": HEAD, "cash": CASH, "sp_always": SP_ALWAYS,
         "costs": {str(k): v for k, v in RES.items()},
         "pair_median": pr[len(pr) // 2], "pair_win": pw,
         "null_max": sorted(nulls)[-1], "null_max_block": sorted(nulls_blk)[-1],
         "obs_small": obs_small, "n_switch": n_sw_flag, "n_off_month": n_off_m,
         "n_cut": n_cut, "n_block": n_block, "n_entry": len(ev_sw),
         "year_win": win, "year_n": len(years), "ma50": e50,
         "decomp": DEC,
         "blocked_mean": st.mean(x for x, _c, _d in bl),
         "kept_mean": st.mean(kp),
         "gates": {"A": A, "B": B, "C": C, "D": D, "E": E, "F": F},
         "n_seed": n_seed, "n_rand": n_rand}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: 82-index-switch.json", flush=True)
    return 0


def _year_factors(curve):
    """연도 → 그 해의 곱셈 인자."""
    out, prev = {}, None
    last = {}
    for d, v in curve:
        last[d[:4]] = v
        if prev is None:
            prev = v
    ys = sorted(last)
    f, base = {}, curve[0][1]
    for y in ys:
        f[y] = last[y] / base
        base = last[y]
    return f


def _prod(f, skip=None):
    r = 1.0
    for y, v in f.items():
        if y != skip:
            r *= v
    return r


if __name__ == "__main__":
    raise SystemExit(main())
