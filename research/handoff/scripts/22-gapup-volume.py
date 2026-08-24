# -*- coding: utf-8 -*-
"""22 — **진입일 거래량 × 갭업**의 동시발생 기술(記述).

지시서: 두뇌 세션 22번 (사용자 정정 — 실제 진입 = 장 시작 전 피벗 가격 예약매수)

★★ **오염 필드 사용 사유(결과 파일에도 명시)**
  `rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER`는 **진입일 종일 거래량**이라 살 때는 모르는 값이다.
  이번에 쓰는 이유: **예측이 아니라 기술**이기 때문이다. 이 값으로 **무엇을 고르거나 거르지 않는다.**
  **이미 일어난 두 사건(그날 거래량이 컸다 · 그날 갭업이었다)이 같이 일어나는지**만 본다.
  → **이 파일의 어떤 숫자도 매매 규칙의 근거가 될 수 없다.** 두뇌 세션 승인 하에 이번 한 번.

★ **검정력을 먼저 적는다(M37-5)** — 0단계가 성과값을 보기 전에 실행된다.
★ **판정 문장 금지 · 순위상관의 "원인" 금지.**

구간(19번과 동일): rel_vol < 1.0 / 1.0~1.5 / 1.5~2.0 / 2.0~3.0 / >= 3.0
갭업 구간(사전 고정): 0 / 0~1 / 1~2 / 2~3 / 3~5 / >= 5  (%)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/22-gapup-volume.py
난수 seed: 날짜 블록 부트스트랩 220000 · 순위상관 부트스트랩 221000
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"

N_BOOT = 1000
DAY_SEED, RHO_SEED = 220000, 221000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
K = (1 - 0.002034) / (1 + 0.000034)          # 17번 정본(우대 왕복 0.207%)

VOL_EDGES = [(None, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, None)]
VOL_NAMES = ["<1.0", "1.0~1.5", "1.5~2.0", "2.0~3.0", ">=3.0"]
GAP_EDGES = [(None, 0.0), (0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, None)]
GAP_NAMES = ["0 (피벗 체결)", "0~1", "1~2", "2~3", "3~5", ">=5"]


def net(g):
    return ((1 + g / 100) * K - 1) * 100


def bucket(v, edges, names):
    for (lo, hi), nm in zip(edges, names):
        if lo is None:
            if v <= hi:
                return nm
        elif hi is None:
            if v >= lo:
                return nm
        elif lo <= v < hi:
            return nm
    return names[-1]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def blocks(rnd, n, lo, hi):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(lo, hi)
        a = rnd.randint(0, n - L)
        LL = min(L, n - tot)
        out.append((a, LL))
        tot += LL
    return out


def rank(xs):
    """평균 순위(동점 처리)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0.0


def q(xs, p):
    s = sorted(xs)
    if not s:
        return None
    i = min(len(s) - 1, int(len(s) * p))
    return s[i]


def load():
    tr, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            tr.append({
                "code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
                "entry_date": e["entry_date"],
                "resolve_date": e["resolve_date"] or e["entry_date"],
                "gain": e["gain_at_resolve_pct"], "result": e["result"],
                "net": net(e["gain_at_resolve_pct"]),
                "gap": e.get("gap_up_pct"),
                "rv": e.get("rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER"),
            })
    return tr


def main():
    tr = load()
    print("중복제거 후 %d건" % len(tr), flush=True)
    miss_gap = sum(1 for t in tr if t["gap"] is None)
    miss_rv = sum(1 for t in tr if t["rv"] is None)
    print("결측: gap %d · rel_vol %d" % (miss_gap, miss_rv), flush=True)
    use = [t for t in tr if t["gap"] is not None and t["rv"] is not None]
    print("두 필드 다 있는 %d건으로 잰다" % len(use), flush=True)
    for t in use:
        t["vb"] = bucket(t["rv"], VOL_EDGES, VOL_NAMES)
        t["gb"] = bucket(t["gap"], GAP_EDGES, GAP_NAMES)
    res = {"n_all": len(tr), "n_used": len(use),
           "missing": {"gap": miss_gap, "rel_vol": miss_rv},
           "why_contaminated_field": (
               "예측이 아니라 기술. 이 값으로 고르거나 거르지 않는다. "
               "이미 일어난 두 사건의 동시발생만 본다. 두뇌 세션 승인 하 1회.")}

    dates = sorted({t["entry_date"] for t in use})
    n_gap = sum(1 for t in use if t["gap"] > 0)
    p_all = n_gap / len(use)
    sd_net = st.pstdev([t["net"] for t in use])

    # ══════════ 0단계 · 검정력 (성과값 보기 전) ══════════
    print("\n" + "=" * 62, flush=True)
    print("0단계 · **검정력** — 재기 전에 적는다(M37-5)", flush=True)
    print("=" * 62, flush=True)
    print("  전체 갭업 발생률 %.1f%% (%d/%d) · 순수익 표준편차 %.2f%%p"
          % (p_all * 100, n_gap, len(use), sd_net), flush=True)
    pw = {"gap_rate_overall": p_all * 100, "sd_net": sd_net, "buckets": {}}
    vb_n = {nm: sum(1 for t in use if t["vb"] == nm) for nm in VOL_NAMES}
    print("\n  [1] 거래량 구간별 **갭업 발생률**을 나머지와 비교할 때 가릴 수 있는 최소 차이", flush=True)
    for nm in VOL_NAMES:
        n1 = vb_n[nm]
        n2 = len(use) - n1
        if n1 == 0 or n2 == 0:
            print("    %-9s n=%4d — 비교 불가" % (nm, n1), flush=True)
            continue
        se = sqrt(p_all * (1 - p_all) * (1 / n1 + 1 / n2))
        print("    %-9s n=%4d → MDE **%.2f%%p** (95%% 폭 ±%.2f%%p)"
              % (nm, n1, MDE_K * se * 100, 1.96 * se * 100), flush=True)
        pw["buckets"][nm] = {"n": n1, "MDE_rate_pp": MDE_K * se * 100}
    rho_se = 1 / sqrt(len(use) - 3)
    print("\n  [2] **순위상관** — Fisher z 표준오차 %.4f → MDE **rho %.3f**"
          % (rho_se, MDE_K * rho_se), flush=True)
    pw["rho_MDE"] = MDE_K * rho_se
    n0, n1g = len(use) - n_gap, n_gap
    print("\n  [3] 갭업 0 (%d건) vs 갭업 발생 (%d건) — 순위합 검정" % (n0, n1g), flush=True)
    gb_n = {nm: sum(1 for t in use if t["gb"] == nm) for nm in GAP_NAMES}
    print("\n  [4] 갭업 구간별 **거래당**을 나머지와 비교할 때 가릴 수 있는 최소 차이", flush=True)
    for nm in GAP_NAMES:
        n1 = gb_n[nm]
        n2 = len(use) - n1
        if n1 < 2 or n2 < 2:
            print("    %-13s n=%4d — 비교 불가" % (nm, n1), flush=True)
            continue
        se = sd_net * sqrt(1 / n1 + 1 / n2)
        print("    %-13s n=%4d → MDE **%.2f%%p**" % (nm, n1, MDE_K * se), flush=True)
        pw.setdefault("gap_buckets", {})[nm] = {"n": n1, "MDE_per_trade_pp": MDE_K * se}
    print("\n  ⚠️ 위 MDE는 **독립 표본 가정**이다. 같은 날 여러 건이 들어가므로"
          "\n     실제 유효표본은 더 작다 — 아래 구간은 **날짜 블록 부트스트랩**으로 낸다.", flush=True)
    res["power"] = pw

    # ══════════ 1 · 거래량 구간별 갭업 분포 ══════════
    print("\n" + "=" * 62, flush=True)
    print("1 · 진입일 거래량 구간별 **갭업 분포**", flush=True)
    print("=" * 62, flush=True)
    rnd = random.Random(DAY_SEED)
    by_date = defaultdict(list)
    for t in use:
        by_date[t["entry_date"]].append(t)
    blk = [blocks(rnd, len(dates), BLOCK_MIN, BLOCK_MAX) for _ in range(N_BOOT)]

    rows1 = []
    print("  %-9s %6s %10s %12s %12s %12s"
          % ("거래량구간", "n", "갭업발생률", "갭업중앙(>0)", "상위10%(전체)", "구간95%"), flush=True)
    for nm in VOL_NAMES:
        sel = [t for t in use if t["vb"] == nm]
        if not sel:
            continue
        gaps = [t["gap"] for t in sel]
        pos = [g for g in gaps if g > 0]
        rate = len(pos) / len(sel) * 100
        bs = []
        for bl in blk:
            a = []
            for s_, L in bl:
                for j in range(L):
                    a.extend(x for x in by_date[dates[s_ + j]] if x["vb"] == nm)
            if a:
                bs.append(sum(1 for x in a if x["gap"] > 0) / len(a) * 100)
        lo, hi = ci(bs)
        # 갭업 크기 중앙(>0)·상위10%(전체)의 날짜 블록 구간
        bm, bp = [], []
        for bl in blk:
            a = []
            for s_, L in bl:
                for j in range(L):
                    a.extend(x for x in by_date[dates[s_ + j]] if x["vb"] == nm)
            p_ = [x["gap"] for x in a if x["gap"] > 0]
            if p_:
                bm.append(st.median(p_))
            if a:
                bp.append(q([x["gap"] for x in a], 0.90))
        mlo, mhi = ci(bm) if bm else (None, None)
        plo, phi = ci(bp) if bp else (None, None)
        rows1.append({"bucket": nm, "n": len(sel), "gap_rate": rate,
                      "gap_median_pos": st.median(pos) if pos else None,
                      "gap_p90_all": q(gaps, 0.90), "rate_ci": [lo, hi],
                      "median_ci": [mlo, mhi], "p90_ci": [plo, phi]})
        print("  %-9s %6d %9.1f%% %11s %11.2f%% %8.1f~%.1f"
              % (nm, len(sel), rate,
                 ("%+.2f%%" % st.median(pos)) if pos else "—",
                 q(gaps, 0.90), lo, hi), flush=True)
        print("            └ 중앙(>0) 95%% %+.2f ~ %+.2f · 상위10%% 95%% %.2f ~ %.2f"
              % (mlo, mhi, plo, phi), flush=True)
    res["by_volume"] = rows1

    # ══════════ 2 · 순위상관 ══════════
    print("\n" + "=" * 62, flush=True)
    print("2 · **순위상관**(진입일 거래량 × 갭업 크기)", flush=True)
    print("=" * 62, flush=True)
    rv = [t["rv"] for t in use]
    gp = [t["gap"] for t in use]
    rho = spearman(rv, gp)
    r2 = random.Random(RHO_SEED)
    bs = []
    for bl in blk:
        a = []
        for s_, L in bl:
            for j in range(L):
                a.extend(by_date[dates[s_ + j]])
        if len(a) > 10:
            bs.append(spearman([x["rv"] for x in a], [x["gap"] for x in a]))
    lo, hi = ci(bs)
    print("  전체 n=%d · **rho = %+.4f** · 날짜 블록 95%% %+.4f ~ %+.4f · 0 %s"
          % (len(use), rho, lo, hi, "제외" if (lo > 0 or hi < 0) else "**포함**"), flush=True)
    res["spearman_all"] = {"n": len(use), "rho": rho, "ci": [lo, hi],
                           "excludes_zero": bool(lo > 0 or hi < 0)}
    # 갭업 발생분만
    pos = [t for t in use if t["gap"] > 0]
    rho_pos = spearman([t["rv"] for t in pos], [t["gap"] for t in pos])
    print("  갭업 발생분만 n=%d · rho = %+.4f" % (len(pos), rho_pos), flush=True)
    res["spearman_gapup_only"] = {"n": len(pos), "rho": rho_pos}
    print("\n  구간 내부 rho:", flush=True)
    for nm in VOL_NAMES:
        sel = [t for t in use if t["vb"] == nm]
        if len(sel) > 10:
            r_ = spearman([t["rv"] for t in sel], [t["gap"] for t in sel])
            print("    %-9s n=%4d · rho = %+.4f" % (nm, len(sel), r_), flush=True)
            res.setdefault("spearman_within", {})[nm] = {"n": len(sel), "rho": r_}

    # ══════════ 3 · 뒤집어서 ══════════
    print("\n" + "=" * 62, flush=True)
    print("3 · **뒤집어서** — 갭업 0 vs 갭업 발생의 진입일 거래량 분포", flush=True)
    print("=" * 62, flush=True)
    a0 = [t["rv"] for t in use if t["gap"] == 0]
    a1 = [t["rv"] for t in use if t["gap"] > 0]
    print("  %-14s %6s %8s %8s %8s %8s %8s"
          % ("", "n", "P10", "Q1", "중앙", "Q3", "P90"), flush=True)
    for lab, a in (("갭업 0", a0), ("갭업 발생", a1)):
        print("  %-14s %6d %8.2f %8.2f %8.2f %8.2f %8.2f"
              % (lab, len(a), q(a, .10), q(a, .25), st.median(a), q(a, .75), q(a, .90)),
              flush=True)
    d_med = st.median(a1) - st.median(a0)
    bs = []
    for bl in blk:
        x0, x1 = [], []
        for s_, L in bl:
            for j in range(L):
                for t in by_date[dates[s_ + j]]:
                    (x1 if t["gap"] > 0 else x0).append(t["rv"])
        if x0 and x1:
            bs.append(st.median(x1) - st.median(x0))
    lo, hi = ci(bs)
    print("  중앙값 차이(발생 − 0) **%+.3f** · 날짜 블록 95%% %+.3f ~ %+.3f · 0 %s"
          % (d_med, lo, hi, "제외" if (lo > 0 or hi < 0) else "**포함**"), flush=True)
    # 순위합(정규근사)
    allv = a0 + a1
    r_all = rank(allv)
    R1 = sum(r_all[len(a0):])
    n0_, n1_ = len(a0), len(a1)
    mu = n1_ * (n0_ + n1_ + 1) / 2
    sg = sqrt(n0_ * n1_ * (n0_ + n1_ + 1) / 12)
    z = (R1 - mu) / sg
    print("  순위합 z = %+.2f  (⚠️ 같은 날 상관을 무시한 값이라 낙관적)" % z, flush=True)
    # 꼬리도 본다 — 중앙과 다를 수 있으므로
    d_p90 = q(a1, .90) - q(a0, .90)
    bs = []
    for bl in blk:
        x0, x1 = [], []
        for s_, L in bl:
            for j in range(L):
                for t in by_date[dates[s_ + j]]:
                    (x1 if t["gap"] > 0 else x0).append(t["rv"])
        if len(x0) > 10 and len(x1) > 10:
            bs.append(q(x1, .90) - q(x0, .90))
    plo2, phi2 = ci(bs)
    print("  P90 차이(발생 − 0)  **%+.3f** · 날짜 블록 95%% %+.3f ~ %+.3f · 0 %s"
          % (d_p90, plo2, phi2, "제외" if (plo2 > 0 or phi2 < 0) else "**포함**"), flush=True)
    res["reverse"] = {"n_gap0": n0_, "n_gapup": n1_,
                      "median_gap0": st.median(a0), "median_gapup": st.median(a1),
                      "median_diff": d_med, "ci": [lo, hi],
                      "excludes_zero": bool(lo > 0 or hi < 0), "rank_sum_z": z,
                      "p90_gap0": q(a0, .90), "p90_gapup": q(a1, .90),
                      "p90_diff": d_p90, "p90_ci": [plo2, phi2],
                      "p90_excludes_zero": bool(plo2 > 0 or phi2 < 0)}

    # ══════════ 4 · 결과까지 ══════════
    print("\n" + "=" * 62, flush=True)
    print("4 · **갭업 크기 구간별 거래당·승률** (사용자가 치르는 비용의 크기)", flush=True)
    print("=" * 62, flush=True)
    rows4 = []
    print("  %-13s %6s %12s %14s %9s"
          % ("갭업구간", "n", "거래당", "구간95%(vs 0)", "승률"), flush=True)
    base = [t for t in use if t["gb"] == GAP_NAMES[0]]
    for nm in GAP_NAMES:
        sel = [t for t in use if t["gb"] == nm]
        if not sel:
            continue
        pt = st.mean(t["net"] for t in sel)
        wr = sum(1 for t in sel if t["result"] == "win") / len(sel) * 100
        cstr = "—"
        cl = None
        if nm != GAP_NAMES[0]:
            bs = []
            for bl in blk:
                A, B = [], []
                for s_, L in bl:
                    for j in range(L):
                        for t in by_date[dates[s_ + j]]:
                            if t["gb"] == nm:
                                A.append(t["net"])
                            elif t["gb"] == GAP_NAMES[0]:
                                B.append(t["net"])
                if A and B:
                    bs.append(st.mean(A) - st.mean(B))
            if bs:
                l_, h_ = ci(bs)
                cl = [l_, h_]
                cstr = "%+.2f~%+.2f" % (l_, h_)
        rows4.append({"bucket": nm, "n": len(sel), "per_trade": pt,
                      "win_rate": wr, "ci_vs_zero": cl,
                      "excludes_zero": bool(cl and (cl[0] > 0 or cl[1] < 0))})
        print("  %-13s %6d %+11.4f%%p %14s %8.2f%%"
              % (nm, len(sel), pt, cstr, wr), flush=True)
    res["by_gap"] = rows4
    print("\n  기준 칸(갭업 0) 거래당 %+.4f%%p · 승률 %.2f%%"
          % (st.mean(t["net"] for t in base),
             sum(1 for t in base if t["result"] == "win") / len(base) * 100), flush=True)

    (OUT / "22-gapup-volume.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/22-gapup-volume.json", flush=True)


if __name__ == "__main__":
    main()
