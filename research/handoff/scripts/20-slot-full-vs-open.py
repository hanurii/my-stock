# -*- coding: utf-8 -*-
"""20 · 주지표 — **슬롯이 꽉 찬 날에 뜬 후보 vs 빈 슬롯이 있던 날에 뜬 후보**의 거래당.

지시서: research/handoff/tasks/20-monthly-occupancy.md + M37

★ 라벨은 **"판정"이 아니라 "상한 좁히기"**다(M37).
  **함정 ②(내생성)를 이 지표도 못 피한다** — 슬롯이 꽉 찬 것은 직전 거래들의 결과가 정하고,
  국면이 이어지면 그 날의 후보 성적도 같은 국면을 탄다.
  **"슬롯이 좋은 날을 놓친다"와 "좋은 국면에서 슬롯이 더 묶인다"가 이 자료로 갈리지 않는다.**

★ 함정 ①(체결률 = 후보 수의 역수)은 **피한다** — 체결률을 쓰지 않고 **그날 빈 칸 수**만 본다.
★ n = 3,776 전수. 월로 안 뭉갠다.
★ C(상한 없는 팔)는 **돌리지 않는다** — 대수적으로 `f × Σ(놓친 거래 수익)`이라
  놓친 거래 평균이 양수이기만 하면 무조건 이기는 **실패할 수 없는 검정**이다(M37).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/20-slot-full-vs-open.py
난수 seed: 슬롯 순서 0~199 · 날짜 블록 부트스트랩 200000 · 달 블록 201000
"""
from __future__ import annotations

import importlib.util
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g18", HERE / "18-slot-selection-cause.py")
g18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g18)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT = 1000
DAY_SEED, MON_SEED = 200000, 201000
BLOCK_MIN, BLOCK_MAX = 20, 40
MBLOCK_MIN, MBLOCK_MAX = 2, 4
MDE_K = 2.80
K = (1 - 0.002034) / (1 + 0.000034)


def net(g):
    return ((1 + g / 100) * K - 1) * 100


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


def boot(ha, hb, units, seed, lo, hi):
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        A, B = [], []
        for s_, L in blocks(rnd, len(units), lo, hi):
            for j in range(L):
                u = units[s_ + j]
                A.extend(ha.get(u, ()))
                B.extend(hb.get(u, ()))
        if A and B:
            out.append(st.mean(A) - st.mean(B))
    return out


def main():
    tr = g18.g.load() if hasattr(g18, "g") else None
    spec2 = importlib.util.spec_from_file_location("g17b", HERE / "17b-turnover-drag.py")
    g17b = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(g17b)
    tr = g17b.load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    for t in tr:
        t["net"] = net(t["gain"])
        t["month"] = t["entry_date"][:7]
    print("거래 %d건 · 거래일 %d" % (len(tr), len(dates)), flush=True)
    res = {"n": len(tr),
           "label": "판정이 아니라 상한 좁히기(M37). 내생성은 이 지표도 못 피한다."}

    # ── 주지표 ──
    print("\n═══ 주지표 · 슬롯이 꽉 찬 날 vs 빈 칸이 있던 날 ═══", flush=True)
    diffs, nfull, nopen = [], [], []
    ha0, hb0 = defaultdict(list), defaultdict(list)
    for s in range(N_SEED):
        _, _, free = g18.fill_split(tr, dates, pos_of, s)
        A = [t for t in tr if free.get(t["entry_date"], 0) == 0]      # 꽉 찬 날
        B = [t for t in tr if free.get(t["entry_date"], 0) > 0]       # 빈 칸 있던 날
        if not A or not B:
            continue
        diffs.append(st.mean(t["net"] for t in A) - st.mean(t["net"] for t in B))
        nfull.append(len(A))
        nopen.append(len(B))
        if s == 0:
            for t in A:
                ha0[t["entry_date"]].append(t["net"])
            for t in B:
                hb0[t["entry_date"]].append(t["net"])
    print("  꽉 찬 날 후보 중앙 **%.0f건** · 빈 칸 있던 날 **%.0f건**"
          % (st.median(nfull), st.median(nopen)), flush=True)
    print("  차이(꽉 참 − 빈 칸) seed 중앙 **%+.2f%%p** (5~95%% %+.2f ~ %+.2f)"
          % (st.median(diffs), *ci(diffs, 5, 95)), flush=True)
    bs = boot(ha0, hb0, dates, DAY_SEED, BLOCK_MIN, BLOCK_MAX)
    lo, hi = ci(bs)
    print("  **날짜 블록 부트스트랩 95%% %+.2f ~ %+.2f** · MDE %.2f%%p · 0 %s"
          % (lo, hi, MDE_K * st.stdev(bs), "제외" if (lo > 0 or hi < 0) else "**포함**"),
          flush=True)
    res["main"] = {"n_full": st.median(nfull), "n_open": st.median(nopen),
                   "diff_seed_median": st.median(diffs),
                   "diff_seed_band": list(ci(diffs, 5, 95)),
                   "day_block_ci": [lo, hi], "MDE": MDE_K * st.stdev(bs),
                   "excludes_zero": bool(lo > 0 or hi < 0)}

    # ── A · 월 축 (기술) — 달 단위 블록 부트스트랩 ──
    print("\n═══ A · 월 축 (**기술**) — 달 단위 블록 부트스트랩 ═══", flush=True)
    by_m = defaultdict(list)
    for t in tr:
        by_m[t["month"]].append(t)
    fills = defaultdict(list)
    for s in range(N_SEED):
        fl, _, _ = g18.fill_split(tr, dates, pos_of, s)
        c = Counter(t["month"] for t in fl)
        for m in by_m:
            fills[m].append(c.get(m, 0))
    months = sorted(by_m)
    rate = {m: st.median(fills[m]) / len(by_m[m]) * 100 for m in months}
    med_r = st.median(rate.values())
    hi_m = [m for m in months if rate[m] >= med_r]
    lo_m = [m for m in months if rate[m] < med_r]
    hA = {m: [t["net"] for t in by_m[m]] for m in hi_m}
    hB = {m: [t["net"] for t in by_m[m]] for m in lo_m}
    obs = (st.mean([x for m in hi_m for x in hA[m]])
           - st.mean([x for m in lo_m for x in hB[m]]))
    bs2 = boot(hA, hB, months, MON_SEED, MBLOCK_MIN, MBLOCK_MAX)
    l2, h2 = ci(bs2)
    print("  체결률 중앙 %.1f%% 기준 상위 %d개월 vs 하위 %d개월"
          % (med_r, len(hi_m), len(lo_m)), flush=True)
    print("  차이(고체결률 − 저체결률) **%+.2f%%p** · **달 블록 95%% %+.2f ~ %+.2f** · "
          "MDE %.2f%%p · 0 %s"
          % (obs, l2, h2, MDE_K * st.stdev(bs2),
             "제외" if (l2 > 0 or h2 < 0) else "**포함**"), flush=True)
    print("  ⚠️ 체결률은 후보 수의 역수에 가깝다(함정 ①). 이 줄은 **기술**이다.", flush=True)
    res["A_month"] = {"median_rate": med_r, "n_hi": len(hi_m), "n_lo": len(lo_m),
                      "diff": obs, "month_block_ci": [l2, h2],
                      "MDE": MDE_K * st.stdev(bs2),
                      "excludes_zero": bool(l2 > 0 or h2 < 0)}

    (OUT / "20-slot-full-vs-open.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/20-slot-full-vs-open.json")


if __name__ == "__main__":
    main()
