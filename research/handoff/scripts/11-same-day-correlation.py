# -*- coding: utf-8 -*-
"""11 - 같은날 전멸은 정상인가 (페이지 주장 13).

지시서: research/handoff/tasks/11-same-day-correlation.md (v2 + M9-3 · M9-16 · M25 · M29-3)

★ 이 과제는 **렌즈로 판정하지 않는다**(M16-3). 집단 비교가 아니라 분포 적합이라
  **사전등록 문턱 하나로만** 판정한다:
    유지 = ρ의 95% 구간이 0을 제외 **그리고** 사후예측 p가 5~95% 안 (M9-3)
    폐기 = ρ 구간이 0을 포함하거나, 실제 전멸일수가 예측보다 50% 이상 많음
    그 사이 = 판정불가
  **ρ의 동등성 폭은 정의하지 않는다**(±0.02는 관례값일 뿐이라 문턱으로 쓰지 않음).

★ M9-16 주 판정 단위 = **슬롯 제약 없는 하루 진입 건수**. 슬롯5 판은 병기한다.
★ M29-3 = 통계량이 정의상 고정되는 관측의 비율을 함께 센다.
★ L2′(연도별)는 **참고만** — 연도별 전멸일수가 2~3일이라 잡음으로 실패한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/11-same-day-correlation.py
난수 seed: 날짜 부트스트랩 110000 · 사후예측 111000 · 슬롯 순서 0~199
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from math import lgamma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_BOOT, N_PP = 1000, 1000
BOOT_SEED, PP_SEED = 110000, 111000
N_SEED_SLOT = 200
NINE = "2025-11-26"
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")


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
            ev.append({"code": e["code"], "pattern": e["pattern"],
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"], "result": e["result"],
                       "gain": e["gain_at_resolve_pct"], "year": e["entry_date"][:4]})
    return ev


def days_of(rows):
    """진입일별 (건수 k, 승 w)."""
    by = defaultdict(lambda: [0, 0])
    for t in rows:
        by[t["entry_date"]][0] += 1
        by[t["entry_date"]][1] += (t["result"] == "win")
    return {d: tuple(v) for d, v in by.items()}


# ── ρ (급내 상관) — 이항 자료의 ANOVA 추정량 ──────────────────────────────

def icc(days):
    """days: {날짜: (k, w)}. Fleiss 의 ANOVA 급내 상관."""
    ks = [k for k, _ in days.values()]
    ws = [w for _, w in days.values()]
    n = sum(ks)
    N = len(ks)
    if N < 2 or n <= N:
        return None
    pbar = sum(ws) / n
    msb = sum(k * (w / k - pbar) ** 2 for k, w in zip(ks, ws)) / (N - 1)
    msw = sum(k * (w / k) * (1 - w / k) for k, w in zip(ks, ws)) / (n - N)
    m0 = (n - sum(k * k for k in ks) / n) / (N - 1)
    den = msb + (m0 - 1) * msw
    if den == 0:
        return None
    return (msb - msw) / den


# ── 베타-이항 적합 (μ, ρ 재모수화) ────────────────────────────────────────

def _lbeta(a, b):
    return lgamma(a) + lgamma(b) - lgamma(a + b)


def bb_loglik(days, mu, rho):
    if not (0 < mu < 1) or not (0 < rho < 1):
        return -1e30
    s = (1 - rho) / rho
    a, b = mu * s, (1 - mu) * s
    if a <= 0 or b <= 0:
        return -1e30
    lb = _lbeta(a, b)
    tot = 0.0
    for k, w in days.values():
        tot += _lbeta(w + a, k - w + b) - lb
    return tot


def fit_bb(days):
    """거친 격자 → 세 번 정밀화. scipy 없이 재현 가능하게."""
    lo_m, hi_m, lo_r, hi_r = 0.05, 0.95, 1e-4, 0.90
    best = (None, None, -1e30)
    for _ in range(4):
        ms = [lo_m + (hi_m - lo_m) * i / 40 for i in range(41)]
        rs = [lo_r + (hi_r - lo_r) * i / 40 for i in range(41)]
        for m in ms:
            for r in rs:
                v = bb_loglik(days, m, r)
                if v > best[2]:
                    best = (m, r, v)
        dm, dr = (hi_m - lo_m) / 20, (hi_r - lo_r) / 20
        lo_m, hi_m = max(1e-4, best[0] - dm), min(0.9999, best[0] + dm)
        lo_r, hi_r = max(1e-6, best[1] - dr), min(0.9999, best[1] + dr)
    mu, rho, ll = best
    s = (1 - rho) / rho
    return {"mu": mu, "rho": rho, "alpha": mu * s, "beta": (1 - mu) * s, "loglik": ll}


def bb_pmf0(k, a, b):
    """0승 확률."""
    return __import__("math").exp(_lbeta(a, k + b) - _lbeta(a, b))


def bb_pmfk(k, a, b):
    """전승(k승) 확률."""
    return __import__("math").exp(_lbeta(k + a, b) - _lbeta(a, b))


def binom_pmf0(k, p):
    return (1 - p) ** k


def binom_pmfk(k, p):
    return p ** k


# ── 사후예측 (M9-3) ───────────────────────────────────────────────────────

def post_pred(days, fit, seed, kmin=2):
    """적합 모형에서 자료를 N_PP 번 생성해 전멸/전승 일수 분포를 만든다."""
    rnd = random.Random(seed)
    a, b = fit["alpha"], fit["beta"]
    ks = [k for k, _ in days.values() if k >= kmin]
    wipe, good = [], []
    for _ in range(N_PP):
        w = g = 0
        for k in ks:
            p = rnd.betavariate(a, b)
            hit = sum(1 for _ in range(k) if rnd.random() < p)
            w += (hit == 0)
            g += (hit == k)
        wipe.append(w)
        good.append(g)
    return wipe, good


def pctl_of(xs, v):
    s = sorted(xs)
    return sum(1 for x in s if x < v) / len(s) * 100


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def main():
    ev = load_events()
    days = days_of(ev)
    n_tr = sum(k for k, _ in days.values())
    print("확정 %d건 · 진입일 %d일 · 최대 하루 %d건"
          % (len(ev), len(days), max(k for k, _ in days.values())), flush=True)
    res = {"n_trades": len(ev), "n_days": len(days),
           "note": "판정은 사전등록 문턱 하나로만 한다(M16-3). 렌즈 미적용. "
                   "ρ 동등성 폭은 정의하지 않는다."}

    kc = Counter(k for k, _ in days.values())
    print("  하루 건수 분포: " + " · ".join("k=%d %d일" % (k, kc[k])
                                       for k in sorted(kc)), flush=True)
    res["k_distribution"] = dict(sorted(kc.items()))

    # ── M29-3 ──
    k1 = kc.get(1, 0)
    m29 = {"k1_days": k1, "k1_day_pct": k1 / len(days) * 100,
           "k1_trades": k1, "k1_trade_pct": k1 / n_tr * 100,
           "k_ge2_days": len(days) - k1}
    res["m29_3"] = m29
    print("\n[M29-3 정의상 고정되는 관측] 하루 1건인 날 %d일 / %d일 = **%.1f%%** "
          "(거래로는 %d / %d = %.1f%%)"
          % (k1, len(days), m29["k1_day_pct"], k1, n_tr, m29["k1_trade_pct"]), flush=True)
    print("  1건인 날은 **'전멸'과 '그 한 건이 졌다'가 같은 사건**이고, 날 안 상관에 "
          "정보를 주지 않는다(ρ 계산에서 MSW 기여가 0). k≥2 인 날은 %d일."
          % m29["k_ge2_days"], flush=True)

    # ── ρ ──
    rho = icc(days)
    rnd = random.Random(BOOT_SEED)
    dl = list(days.values())
    boot = []
    for _ in range(N_BOOT):
        smp = {i: dl[rnd.randrange(len(dl))] for i in range(len(dl))}
        v = icc(smp)
        if v is not None:
            boot.append(v)
    rlo, rhi = ci(boot)
    print("\n★ ρ (급내 상관, ANOVA 추정량) = **%+.5f** · 날짜 부트스트랩 95%% "
          "**%+.5f ~ %+.5f** · 0 제외 %s"
          % (rho, rlo, rhi, "예" if (rlo > 0 or rhi < 0) else "아니오"), flush=True)
    res["rho"] = {"point": rho, "ci": [rlo, rhi],
                  "excludes_zero": bool(rlo > 0 or rhi < 0)}

    seg_rho, yr_rho = {}, {}
    for sn, y0, y1 in SEGMENTS:
        sd = {d: v for d, v in days.items() if y0 <= d[:4] <= y1}
        seg_rho[sn] = {"n_days": len(sd), "n_trades": sum(k for k, _ in sd.values()),
                       "rho": icc(sd)}
    for y in YEARS:
        sd = {d: v for d, v in days.items() if d[:4] == y}
        yr_rho[y] = {"n_days": len(sd), "rho": icc(sd)}
    res["rho_by_segment"], res["rho_by_year"] = seg_rho, yr_rho
    print("  구간별 ρ: " + " · ".join(
        "%s %.5f(%d일)" % (k, v["rho"], v["n_days"]) for k, v in seg_rho.items()),
        flush=True)
    print("  연도별 ρ(참고): " + " · ".join(
        "%s %.5f" % (k, v["rho"]) for k, v in yr_rho.items()), flush=True)

    # ── 베타-이항 적합 ──
    fit = fit_bb(days)
    p_hat = sum(w for _, w in days.values()) / n_tr
    print("\n★ 베타-이항 적합: μ=%.5f · **ρ_bb = 1/(α+β+1) = %.5f** · α=%.3f β=%.3f "
          "· logL=%.2f  (단순 이항 p̂ = %.5f)"
          % (fit["mu"], fit["rho"], fit["alpha"], fit["beta"], fit["loglik"], p_hat),
          flush=True)
    res["beta_binomial"] = fit
    res["p_hat"] = p_hat

    # ── k별 전멸/전승 표 ──
    print("\n[하루 매수 k별 전멸·전승] 실제 vs 베타-이항 vs 독립 가정", flush=True)
    tab = {}
    for k in range(2, 9):
        dd = [(kk, w) for kk, w in days.values() if kk == k]
        if not dd:
            continue
        nd = len(dd)
        tab[k] = {"n_days": nd,
                  "wipe_actual": sum(1 for _, w in dd if w == 0),
                  "wipe_bb": nd * bb_pmf0(k, fit["alpha"], fit["beta"]),
                  "wipe_indep": nd * binom_pmf0(k, p_hat),
                  "good_actual": sum(1 for _, w in dd if w == k),
                  "good_bb": nd * bb_pmfk(k, fit["alpha"], fit["beta"]),
                  "good_indep": nd * binom_pmfk(k, p_hat)}
        t = tab[k]
        print("  k=%d  날 %3d · 전멸 실제 %3d / 베타이항 %6.1f / 독립 %6.1f · "
              "전승 실제 %3d / 베타이항 %5.1f / 독립 %5.1f"
              % (k, nd, t["wipe_actual"], t["wipe_bb"], t["wipe_indep"],
                 t["good_actual"], t["good_bb"], t["good_indep"]), flush=True)
    res["k_table"] = tab

    # ── ★ 판정: 사후예측 p (M9-3) ──
    print("\n★ 사후예측 (M9-3) — 적합 모형에서 %d번 생성" % N_PP, flush=True)
    pp = {}
    for kmin in (2, 3):
        wipe, good = post_pred(days, fit, PP_SEED + kmin, kmin=kmin)
        aw = sum(1 for k, w in days.values() if k >= kmin and w == 0)
        ag = sum(1 for k, w in days.values() if k >= kmin and w == k)
        wl, wh = band(wipe)
        gl, gh = band(good)
        pp["k>=%d" % kmin] = {
            "wipe_actual": aw, "wipe_pred_median": st.median(wipe),
            "wipe_band_5_95": [wl, wh], "wipe_pctl": pctl_of(wipe, aw),
            "wipe_inside": bool(wl <= aw <= wh),
            "good_actual": ag, "good_pred_median": st.median(good),
            "good_band_5_95": [gl, gh], "good_pctl": pctl_of(good, ag),
            "good_inside": bool(gl <= ag <= gh),
            "wipe_excess_pct": (aw / st.median(wipe) - 1) * 100 if st.median(wipe) else None}
        v = pp["k>=%d" % kmin]
        print("  [k≥%d] 전멸 실제 **%d일** · 예측 중앙 %.1f · 5~95%% %d ~ %d → "
              "백분위 %.1f · 안 %s · 초과 %+.1f%%"
              % (kmin, aw, v["wipe_pred_median"], wl, wh, v["wipe_pctl"],
                 "예" if v["wipe_inside"] else "아니오", v["wipe_excess_pct"]), flush=True)
        print("        전승 실제 **%d일** · 예측 중앙 %.1f · 5~95%% %d ~ %d → "
              "백분위 %.1f · 안 %s"
              % (ag, v["good_pred_median"], gl, gh, v["good_pctl"],
                 "예" if v["good_inside"] else "아니오"), flush=True)
    res["posterior_predictive"] = pp

    # ── 앞 절반 적합 → 뒤 절반 예측 (M9-3) ──
    ds = sorted(days)
    half = ds[:len(ds) // 2]
    rest = ds[len(ds) // 2:]
    f1 = fit_bb({d: days[d] for d in half})
    d2 = {d: days[d] for d in rest}
    wipe2, good2 = post_pred(d2, f1, PP_SEED + 50, kmin=2)
    aw2 = sum(1 for k, w in d2.values() if k >= 2 and w == 0)
    ag2 = sum(1 for k, w in d2.values() if k >= 2 and w == k)
    w2l, w2h = band(wipe2)
    g2l, g2h = band(good2)
    res["holdout"] = {"fit_days": len(half), "test_days": len(rest),
                      "split_date": rest[0], "fit_rho": f1["rho"], "fit_mu": f1["mu"],
                      "wipe_actual": aw2, "wipe_pred_median": st.median(wipe2),
                      "wipe_band_5_95": [w2l, w2h], "wipe_inside": bool(w2l <= aw2 <= w2h),
                      "wipe_pctl": pctl_of(wipe2, aw2),
                      "good_actual": ag2, "good_pred_median": st.median(good2),
                      "good_band_5_95": [g2l, g2h], "good_inside": bool(g2l <= ag2 <= g2h)}
    print("\n★ 앞 절반 적합 → 뒤 절반 예측 (경계 %s · 적합 %d일 → 검정 %d일)"
          % (rest[0], len(half), len(rest)), flush=True)
    print("  적합값 μ=%.5f ρ=%.5f · 전멸 실제 **%d일** · 예측 중앙 %.1f · 5~95%% %d ~ %d "
          "→ 백분위 %.1f · 안 %s"
          % (f1["mu"], f1["rho"], aw2, st.median(wipe2), w2l, w2h,
             res["holdout"]["wipe_pctl"], "예" if res["holdout"]["wipe_inside"] else "아니오"),
          flush=True)
    print("  전승 실제 **%d일** · 예측 중앙 %.1f · 5~95%% %d ~ %d · 안 %s"
          % (ag2, st.median(good2), g2l, g2h,
             "예" if res["holdout"]["good_inside"] else "아니오"), flush=True)

    # ── 슬롯5 판 병기 (M9-16) ──
    print("\n[슬롯5 판 병기] (주 판정은 제약 없는 쪽 — M9-16)", flush=True)
    rhos, wipes, goods, kmax = [], [], [], []
    for s in range(N_SEED_SLOT):
        sd = defaultdict(lambda: [0, 0])
        held = []
        # slot_sim 과 같은 정본 ④ 규칙으로 '실제로 산' 건만 남긴다
        byday = defaultdict(list)
        for t in ev:
            byday[t["entry_date"]].append(t)
        for d in byday:
            byday[d].sort(key=lambda t: (t["code"], t["pattern"], t["scan_date"]))
        dates = sorted(set(list(byday) + [t["resolve_date"] for t in ev]))
        for d in dates:
            held = [h for h in held if h[0] >= d]
            free = 5 - len(held)
            c = sorted(byday.get(d, []), key=lambda t: slot_sim.order_key(s, t))
            for t in c[:max(0, free)]:
                held.append([t["resolve_date"], t])
                sd[d][0] += 1
                sd[d][1] += (t["result"] == "win")
        sdd = {d: tuple(v) for d, v in sd.items() if v[0] > 0}
        rhos.append(icc(sdd))
        wipes.append(sum(1 for k, w in sdd.values() if k >= 2 and w == 0))
        goods.append(sum(1 for k, w in sdd.values() if k >= 2 and w == k))
        kmax.append(max(k for k, _ in sdd.values()))
    res["slot5"] = {"rho_median": st.median(rhos), "rho_band": list(band(rhos)),
                    "wipe_median": st.median(wipes), "wipe_band": list(band(wipes)),
                    "good_median": st.median(goods), "good_band": list(band(goods)),
                    "kmax_median": st.median(kmax)}
    print("  ρ 중앙 %.5f (5~95%% %.5f ~ %.5f) · 하루 최대 %d건 · "
          "k≥2 전멸 중앙 %.0f일 (5~95%% %d~%d) · 전승 중앙 %.0f일 (%d~%d)"
          % (st.median(rhos), *band(rhos), st.median(kmax), st.median(wipes),
             *band(wipes), st.median(goods), *band(goods)), flush=True)

    # ── 9개월 대조 (M9-11 참고) ──
    nd = {d: v for d, v in days.items() if d >= NINE}
    n9 = sum(k for k, _ in nd.values())
    w9 = sum(1 for k, w in nd.values() if k >= 2 and w == 0)
    g9 = sum(1 for k, w in nd.values() if k >= 2 and w == k)
    wipe9, good9 = post_pred(nd, fit, PP_SEED + 90, kmin=2)
    res["nine_month"] = {"from": NINE, "n_days": len(nd), "n_trades": n9,
                         "wipe_actual": w9, "wipe_pred_median": st.median(wipe9),
                         "wipe_band_5_95": list(band(wipe9)),
                         "good_actual": g9, "good_pred_median": st.median(good9),
                         "good_band_5_95": list(band(good9)),
                         "page_wipe_pred": 12.3, "page_wipe_actual": 14,
                         "page_good_pred": 2.9, "page_good_actual": 2,
                         "page_inside_wipe": bool(band(wipe9)[0] <= 14 <= band(wipe9)[1]),
                         "page_inside_good": bool(band(good9)[0] <= 2 <= band(good9)[1])}
    print("\n[9개월 대조 · 참고(M9-11)] %s 이후 %d일 · 거래 %d건 (페이지 표본은 614건)"
          % (NINE, len(nd), n9), flush=True)
    print("  전멸 실제 %d일 · 우리 예측 중앙 %.1f (5~95%% %d~%d) | 페이지 예측 12.3 / 실제 14"
          % (w9, st.median(wipe9), *band(wipe9)), flush=True)
    print("  전승 실제 %d일 · 우리 예측 중앙 %.1f (5~95%% %d~%d) | 페이지 예측 2.9 / 실제 2"
          % (g9, st.median(good9), *band(good9)), flush=True)
    print("  페이지의 실제값이 우리 예측 구간 안인가: 전멸 14 → %s · 전승 2 → %s"
          % ("안" if res["nine_month"]["page_inside_wipe"] else "밖",
             "안" if res["nine_month"]["page_inside_good"] else "밖"), flush=True)

    (OUT / "11-same-day-correlation.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/11-same-day-correlation.json")


if __name__ == "__main__":
    main()
