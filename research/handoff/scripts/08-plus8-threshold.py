# -*- coding: utf-8 -*-
"""08 — +8% 도달하면 열에 일곱 (페이지 주장 10).

지시서: research/handoff/tasks/08-plus8-threshold.md (v2 + M9-1·M9-2 + M10~M22)

주 지표: **P(최종 승 | 보유 중 최고 상승 ≥ +8%)**
  승은 정의상 전부 +20%를 넘으므로 분자에 다 들어간다. 분모의 **패 중 max_gain ≥ 8** 만 세면 된다.

판정 (M9-1 · M16-2 · M16-3)
---------------------------
· **동등성 미적용.** 08은 자체 규칙을 쓴다.
· **95% 신뢰구간**으로 판정한다(점추정 아님):
    유지 = 전체 CI 하한 ≥ 65% **그리고** 다섯 구간 전부 CI 하한 ≥ 55%
    폐기 = 전체 CI 상한 < 55%
    그 사이 = 판정불가(수치 수정)
· **렌즈는 셋**(L1 불성립 — 집단 비교가 아니라 조건부 확률이다):
    L2′(leave-one-year) · L3(구간 5/5) · **L4(집중도 = 한 종목·한 달이 분모의 5% 이하)**
    → 3/3 유지 · 2 판정불가 · 0~1 폐기.
· **L4는 "상위 5건 제거"가 아니다**(M9-2) — 조건부 확률이라 5건을 빼도 0.1%p밖에 안 움직여
  **원리적으로 실패할 수 없는 검정**이었다.

신뢰구간 방법
-------------
같은 날 여러 건이 함께 움직이므로 **연속 20~40거래일 블록 부트스트랩 1,000회**를 정본으로 쓰고,
독립 가정의 **Wilson 구간**을 참고로 병기한다(둘을 나란히 보면 군집의 크기가 보인다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/08-plus8-threshold.py
난수 seed: 블록 부트스트랩 80000 (구간별 +1..+5 · 연도별 +10..)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
N_BOOT = 1000
BOOT_SEED = 80000
BLOCK_MIN, BLOCK_MAX = 20, 40
Z = 1.959963985
THRESHOLDS = [5, 8, 10, 12, 15]
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]


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
            ev.append({"key": k, "code": e["code"], "name": e.get("name"),
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"], "result": e["result"],
                       "max_gain": e["max_gain_pct"], "days_held": e["days_held"],
                       "year": e["entry_date"][:4], "month": e["entry_date"][:7]})
    return ev


def load_path_days(keys):
    """+8% 통과 시점 · +20% 도달 시점 · 손절 시점을 경로에서 뽑아 **스칼라로만** 남긴다."""
    out = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            k = (p["scan_date"], p["code"], p["pattern"])
            if k not in keys:
                continue
            e = p["entry_price"]
            h, l = p["h"], p["l"]
            n = len(h)
            T8, T20, S = e * 1.08, e * (1 + TARGET / 100), e * (1 - STOP / 100)
            d8 = d20 = ds = None
            mh, ml = -1e30, 1e30
            for i in range(n):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                if d8 is None and mh >= T8:
                    d8 = i
                if d20 is None and mh >= T20:
                    d20 = i
                if ds is None and ml <= S:
                    ds = i
                if d20 is not None and ds is not None:
                    break
            out[k] = {"d8": d8, "d20": d20, "dstop": ds}
        print("  경로 %d 스캔 · 누적 %d" % (y, len(out)), flush=True)
    return out


def wilson(k, n):
    if n == 0:
        return None, None, None
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    hw = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return p * 100, (c - hw) * 100, (c + hw) * 100


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def block_boot_rate(by_pos, n_pos, seed):
    """블록 부트스트랩으로 조건부 확률(승/(승+패))의 분포를 낸다.
    by_pos[p] = [(is_win, ...), ...] — 이미 max_gain ≥ 문턱으로 거른 건만 담는다."""
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        w = t = 0
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                for is_w in by_pos.get(a + j, ()):
                    t += 1
                    w += is_w
        if t:
            out.append(w / t * 100)
    return out


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    n = len(s)
    return s[int(n * lo / 100)], s[int(n * hi / 100) - 1]


def rate_block(rows, pos_of, n_pos, seed, thr=8.0):
    """rows 에서 max_gain ≥ thr 인 건만 골라 조건부 승률 + 두 가지 구간."""
    g = [r for r in rows if r["max_gain"] >= thr]
    k = sum(1 for r in g if r["result"] == "win")
    n = len(g)
    pt, wlo, whi = wilson(k, n)
    by_pos = defaultdict(list)
    for r in g:
        by_pos[pos_of[r["entry_date"]]].append(1 if r["result"] == "win" else 0)
    bb = block_boot_rate(by_pos, n_pos, seed)
    blo, bhi = ci(bb) if bb else (None, None)
    return {"n": n, "n_win": k, "n_loss": n - k, "rate": pt,
            "wilson_lo": wlo, "wilson_hi": whi,
            "boot_lo": blo, "boot_hi": bhi,
            "boot_median": st.median(bb) if bb else None}


def main():
    ev = load_events()
    print("확정 %d건 (승 %d · 패 %d)"
          % (len(ev), sum(1 for e in ev if e["result"] == "win"),
             sum(1 for e in ev if e["result"] == "loss")), flush=True)
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(e["entry_date"] for e in ev)
    hi_d = max(e["resolve_date"] for e in ev)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    n_pos = len(dates)
    ev = [e for e in ev if e["entry_date"] in pos_of]
    print("달력 %d거래일" % n_pos, flush=True)

    res = {"n_events": len(ev), "n_boot": N_BOOT, "boot_seed": BOOT_SEED}

    # ── 주 지표 (+8%) ──
    main8 = rate_block(ev, pos_of, n_pos, BOOT_SEED, 8.0)
    print("\n★ 주 지표 P(승 | max_gain ≥ 8%%)", flush=True)
    print("   분모 %d (승 %d · 패 %d) · 점추정 **%.2f%%**"
          % (main8["n"], main8["n_win"], main8["n_loss"], main8["rate"]), flush=True)
    print("   블록 부트스트랩 95%% **%.2f ~ %.2f** (중앙 %.2f) · Wilson 95%% %.2f ~ %.2f"
          % (main8["boot_lo"], main8["boot_hi"], main8["boot_median"],
             main8["wilson_lo"], main8["wilson_hi"]), flush=True)
    print("   ※ 승 %d건이 분자에 전부 들어가므로 '전체 ≥65%%' 는 "
          "'max_gain≥8 인 패가 %d건 이하' 와 같은 말이다."
          % (main8["n_win"], int(main8["n_win"] / 0.65 - main8["n_win"])), flush=True)
    res["main8"] = main8

    # 판정 (M9-1)
    seg = {}
    for i, (sn, y0, y1) in enumerate(SEGMENTS):
        g = [e for e in ev if y0 <= e["year"] <= y1]
        seg[sn] = rate_block(g, pos_of, n_pos, BOOT_SEED + 1 + i, 8.0)
        print("   %-8s 분모 %4d (승 %4d) · %.2f%% · 부트 95%% %.2f ~ %.2f · Wilson %.2f ~ %.2f"
              % (sn, seg[sn]["n"], seg[sn]["n_win"], seg[sn]["rate"],
                 seg[sn]["boot_lo"], seg[sn]["boot_hi"],
                 seg[sn]["wilson_lo"], seg[sn]["wilson_hi"]), flush=True)
    res["segments"] = seg
    ok_all = main8["boot_lo"] >= 65
    ok_seg = all(v["boot_lo"] >= 55 for v in seg.values())
    verdict = ("유지" if (ok_all and ok_seg) else
               "폐기" if main8["boot_hi"] < 55 else "판정불가(수치 수정)")
    res["verdict_axis"] = {"all_ci_lo_ge65": ok_all, "seg_all_ci_lo_ge55": ok_seg,
                           "verdict": verdict}
    print("   → 전체 CI 하한 ≥65%% %s · 구간 전부 CI 하한 ≥55%% %s → **%s**"
          % ("예" if ok_all else "아니오", "예" if ok_seg else "아니오", verdict),
          flush=True)

    # ── 렌즈 셋 ──
    # L2′ leave-one-year: 한 해씩 빼도 전체 CI 하한 ≥ 65%
    dyr = {}
    years = sorted({e["year"] for e in ev})
    for i, y in enumerate(years):
        g = [e for e in ev if e["year"] != y]
        dyr[y] = rate_block(g, pos_of, n_pos, BOOT_SEED + 10 + i, 8.0)
    l2p = all(v["boot_lo"] >= 65 for v in dyr.values())
    print("\n[L2′] 한 해씩 빼도 CI 하한 ≥65%% 유지? %s" % ("예" if l2p else "아니오"), flush=True)
    for y, v in dyr.items():
        print("      %s 제거 → %.2f%% (부트 95%% %.2f ~ %.2f)"
              % (y, v["rate"], v["boot_lo"], v["boot_hi"]), flush=True)
    # 2026 제외 5년 (M14-3)
    g5 = [e for e in ev if e["year"] != "2026"]
    excl26 = rate_block(g5, pos_of, n_pos, BOOT_SEED + 30, 8.0)
    print("      (2026 제외 5년) %.2f%% · 부트 95%% %.2f ~ %.2f"
          % (excl26["rate"], excl26["boot_lo"], excl26["boot_hi"]), flush=True)

    # L4 집중도: 한 종목·한 달이 분모의 5% 이하
    g8 = [e for e in ev if e["max_gain"] >= 8]
    c_code = Counter(e["code"] for e in g8)
    c_month = Counter(e["month"] for e in g8)
    top_code, n_code = c_code.most_common(1)[0]
    top_month, n_month = c_month.most_common(1)[0]
    l4 = (n_code / len(g8) <= 0.05) and (n_month / len(g8) <= 0.05)
    print("\n[L4 집중도] 분모 %d · 최다 종목 %s %d건(%.2f%%) · 최다 달 %s %d건(%.2f%%) → %s"
          % (len(g8), top_code, n_code, n_code / len(g8) * 100,
             top_month, n_month, n_month / len(g8) * 100,
             "통과" if l4 else "미통과"), flush=True)
    l3 = ok_seg
    lenses = {"L2p": l2p, "L3": l3, "L4": l4}
    print("[렌즈] L2′ %s · L3 %s · L4 %s → **%d/3**"
          % (*["통과" if lenses[k] else "미통과" for k in ("L2p", "L3", "L4")],
             sum(lenses.values())), flush=True)
    res["lenses"] = {"L2p": {"pass": l2p, "by_year": dyr, "excl_2026": excl26},
                     "L3": {"pass": l3},
                     "L4": {"pass": l4, "n_denom": len(g8),
                            "top_code": top_code, "top_code_n": n_code,
                            "top_code_pct": n_code / len(g8) * 100,
                            "top_month": top_month, "top_month_n": n_month,
                            "top_month_pct": n_month / len(g8) * 100},
                     "n_passed": sum(lenses.values())}

    # ── 문턱 민감도 ──
    print("\n[문턱 민감도] (판정은 +8% 로만)", flush=True)
    sens = {}
    for i, t in enumerate(THRESHOLDS):
        r = rate_block(ev, pos_of, n_pos, BOOT_SEED + 40 + i, float(t))
        sens[t] = r
        print("   ≥%2d%%  분모 %4d (승 %4d · 패 %4d) · %.2f%% · 부트 95%% %.2f ~ %.2f"
              % (t, r["n"], r["n_win"], r["n_loss"], r["rate"], r["boot_lo"], r["boot_hi"]),
              flush=True)
    res["threshold_sensitivity"] = sens

    # ── 경로: +8% → +20% 걸린 일수 · 뺏긴 건들 ──
    print("\n경로 스캔 …", flush=True)
    pd = load_path_days({e["key"] for e in ev})
    gaps, no8 = [], 0
    for e in ev:
        if e["result"] != "win":
            continue
        v = pd.get(e["key"])
        if not v or v["d8"] is None or v["d20"] is None:
            no8 += 1
            continue
        gaps.append(v["d20"] - v["d8"])
    gaps.sort()

    def q(a, p):
        return a[min(len(a) - 1, int(len(a) * p))]

    res["gap_8_to_20"] = {"n": len(gaps), "median": st.median(gaps),
                          "q3": q(gaps, 0.75), "p90": q(gaps, 0.90), "max": gaps[-1],
                          "mean": st.mean(gaps), "same_day_pct":
                          sum(1 for x in gaps if x == 0) / len(gaps) * 100,
                          "n_win_without_8": no8}
    print("[+8%% → +20%% 걸린 거래일] n=%d · 중앙 **%.0f일** · Q3 %d · P90 %d · 최대 %d · "
          "평균 %.1f · 같은 날 %.1f%% (페이지: 보통 3일 더)"
          % (len(gaps), st.median(gaps), q(gaps, 0.75), q(gaps, 0.90), gaps[-1],
             st.mean(gaps), res["gap_8_to_20"]["same_day_pct"]), flush=True)

    # +8% 통과했는데 결국 손절난 건들
    lost = []
    for e in ev:
        if e["result"] != "loss" or e["max_gain"] < 8:
            continue
        v = pd.get(e["key"])
        if not v or v["d8"] is None or v["dstop"] is None:
            continue
        lost.append({"code": e["code"], "name": e.get("name"), "max_gain": e["max_gain"],
                     "d8": v["d8"], "dstop": v["dstop"], "days": v["dstop"] - v["d8"]})
    mg = sorted(x["max_gain"] for x in lost)
    dd = sorted(x["days"] for x in lost)
    res["taken_back"] = {"n": len(lost),
                         "max_gain": {"median": st.median(mg), "q3": q(mg, 0.75),
                                      "p90": q(mg, 0.90), "max": mg[-1]},
                         "days_8_to_stop": {"median": st.median(dd), "q3": q(dd, 0.75),
                                            "p90": q(dd, 0.90), "max": dd[-1]},
                         "ge12_pct": sum(1 for x in mg if x >= 12) / len(mg) * 100,
                         "ge15_pct": sum(1 for x in mg if x >= 15) / len(mg) * 100}
    print("[뺏긴 건들] +8%% 통과 후 손절 **%d건** · 최고 상승 중앙 %.1f%% (Q3 %.1f · P90 %.1f · 최대 %.1f)"
          % (len(lost), st.median(mg), q(mg, 0.75), q(mg, 0.90), mg[-1]), flush=True)
    print("            그중 +12%% 이상 갔던 건 %.1f%% · +15%% 이상 %.1f%%"
          % (res["taken_back"]["ge12_pct"], res["taken_back"]["ge15_pct"]), flush=True)
    print("            +8%% 통과 → 손절까지 중앙 **%.0f거래일** (Q3 %d · P90 %d · 최대 %d)"
          % (st.median(dd), q(dd, 0.75), q(dd, 0.90), dd[-1]), flush=True)

    (OUT / "08-plus8-threshold.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/08-plus8-threshold.json")


if __name__ == "__main__":
    main()
