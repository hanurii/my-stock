# -*- coding: utf-8 -*-
"""18 · 0단계 — 슬롯 선택 열화가 **관측 가능한 크기인가**.

지시서: research/handoff/tasks/18-slot-selection-cause.md (사전등록)

★ 사전등록이 정한 지표 둘
  ① (체결분 거래당) − (전체 3,776건 거래당)
  ② (막힌 후보 거래당) − (체결분 거래당)      ← 12ii 의 +0.53%p 에 대응
  **판정: 두 구간이 모두 0을 포함하면 1~3단계를 하지 않는다.**

★ 불확실성을 **세 형태로 함께** 낸다 — 사전등록이 정한 것은 (a) 하나뿐인데,
  (a)만으로는 물음이 달라진다. 어느 것을 관문으로 쓸지는 두뇌·검증 세션이 정한다.
  (a) **seed 값들의 2.5/97.5 분위** — "한 번 돌리면 어디쯤 나오나"(사전등록 문언)
  (b) **seed 평균의 표준오차** (SD/√200) — "그 치우침이 계통적인가"
  (c) **날짜 블록 부트스트랩** (M10·M32-2) — "자료에서 실재하는가"
  ※ M10 은 **"seed 짝비교를 검정으로 쓰지 않는다. 불확실성은 블록 부트스트랩으로 낸다"**이므로
     (c)가 상위 규약과 맞는 형태다. 셋을 모두 적고 판정은 넘긴다.

MDE = 2.80 × (짝지은 차이 표준편차) 도 함께 보고(게이트 아님, M12-3).
주지표에 **leave-one-year 여섯 번**.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/18-slot-selection-cause.py
난수 seed: 슬롯 순서 0~199 · 블록 부트스트랩 180000
"""
from __future__ import annotations

import importlib.util
import json
import random
import statistics as st
import sys
from collections import defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g17b", HERE / "17b-turnover-drag.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT, BOOT_SEED = 1000, 180000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
SLOTS = 5
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
NETF = g.make_net(0.000034, 0.002034)          # 17번 정본 비용(우대)
slot_sim.net = NETF


def fill_split(trades, dates, pos_of, seed):
    """정본 ④ 규칙으로 체결분과 막힌 후보를 가른다."""
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for d in byday:
        byday[d].sort(key=lambda t: (t["code"], t["pattern"], t["scan_date"]))
    order = {d: sorted(v, key=lambda t: slot_sim.order_key(seed, t))
             for d, v in byday.items()}
    held, filled, blocked = [], [], []
    free_hist = {}
    for i, d in enumerate(dates):
        held = [h for h in held if h[0] >= i]
        free = SLOTS - len(held)
        free_hist[d] = free
        c = order.get(d)
        if c:
            for j, t in enumerate(c):
                if j < free:
                    held.append([pos_of[t["resolve_date"]], t])
                    filled.append(t)
                else:
                    blocked.append(t)
    return filled, blocked, free_hist


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    out, tot = [], 0
    while tot < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - tot)
        out.append((a, LL))
        tot += LL
    return out


def report(name, vals, boot_pairs, dates, seedwise=True):
    """(a) 값들의 분위 · (b) 평균의 표준오차 · (c) 블록 부트스트랩."""
    med, mean = st.median(vals), st.mean(vals)
    sd = st.stdev(vals)
    a_lo, a_hi = ci(vals)
    se = sd / sqrt(len(vals))
    b_lo, b_hi = mean - 1.96 * se, mean + 1.96 * se
    out = {"n_seed": len(vals), "median": med, "mean": mean, "sd": sd,
           "a_spread": [a_lo, a_hi], "a_excludes_zero": bool(a_lo > 0 or a_hi < 0),
           "b_se": se, "b_ci": [b_lo, b_hi],
           "b_excludes_zero": bool(b_lo > 0 or b_hi < 0),
           "MDE": MDE_K * sd}
    print("  %s" % name, flush=True)
    print("     중앙 **%+.4f%%p** · 평균 %+.4f · SD %.4f · **MDE %.4f%%p**"
          % (med, mean, sd, MDE_K * sd), flush=True)
    print("     (a) seed 값 2.5/97.5 분위  **%+.4f ~ %+.4f**  → 0 %s"
          % (a_lo, a_hi, "제외" if out["a_excludes_zero"] else "**포함**"), flush=True)
    print("     (b) seed 평균의 95%% (SD/√%d) **%+.4f ~ %+.4f** → 0 %s"
          % (len(vals), b_lo, b_hi, "**제외**" if out["b_excludes_zero"] else "포함"),
          flush=True)
    if boot_pairs is not None:
        rnd = random.Random(BOOT_SEED)
        n_pos = len(dates)
        bs = []
        for _ in range(N_BOOT):
            f, o = [], []
            for a, L in make_blocks(rnd, n_pos):
                for j in range(L):
                    d = dates[a + j]
                    f.extend(boot_pairs[0].get(d, ()))
                    o.extend(boot_pairs[1].get(d, ()))
            if f and o:
                bs.append(st.mean(f) - st.mean(o))
        c_lo, c_hi = ci(bs)
        out["c_ci"] = [c_lo, c_hi]
        out["c_excludes_zero"] = bool(c_lo > 0 or c_hi < 0)
        out["c_sd"] = st.stdev(bs)
        out["c_MDE"] = MDE_K * st.stdev(bs)
        print("     (c) 날짜 블록 부트스트랩 95%% **%+.4f ~ %+.4f** → 0 %s "
              "· MDE %.4f%%p"
              % (c_lo, c_hi, "제외" if out["c_excludes_zero"] else "**포함**",
                 MDE_K * st.stdev(bs)), flush=True)
    return out


def main():
    tr = g.load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    m_all = st.mean(NETF(t["gain"]) for t in tr)
    print("전체 %d건 거래당 **%+.4f%%p** (17번 정본 비용) · 거래일 %d"
          % (len(tr), m_all, len(dates)), flush=True)

    d1, d2 = [], []
    n_fill, n_block = [], []
    fill_by_date_0, block_by_date_0 = defaultdict(list), defaultdict(list)
    for s in range(N_SEED):
        fl, bl, _ = fill_split(tr, dates, pos_of, s)
        mf = st.mean(NETF(t["gain"]) for t in fl)
        mb = st.mean(NETF(t["gain"]) for t in bl)
        d1.append(mf - m_all)
        d2.append(mb - mf)
        n_fill.append(len(fl))
        n_block.append(len(bl))
        if s == 0:
            for t in fl:
                fill_by_date_0[t["entry_date"]].append(NETF(t["gain"]))
            for t in bl:
                block_by_date_0[t["entry_date"]].append(NETF(t["gain"]))
    print("체결 중앙 %.0f건 · 막힘 중앙 %.0f건\n" % (st.median(n_fill), st.median(n_block)),
          flush=True)

    print("═══ 0단계 · 지표 둘 ═══", flush=True)
    all_by_date = defaultdict(list)
    for t in tr:
        all_by_date[t["entry_date"]].append(NETF(t["gain"]))
    r1 = report("① (체결분 거래당) − (전체 3,776건 거래당)", d1,
                (fill_by_date_0, all_by_date), dates)
    r2 = report("② (막힌 후보 거래당) − (체결분 거래당)", d2,
                (block_by_date_0, fill_by_date_0), dates)

    print("\n═══ leave-one-year (지표 ②, seed 200) ═══", flush=True)
    yr = {}
    for y in YS:
        sub = [t for t in tr if t["year"] != y]
        v = []
        for s in range(N_SEED):
            fl, bl, _ = fill_split(sub, dates, pos_of, s)
            if fl and bl:
                v.append(st.mean(NETF(t["gain"]) for t in bl)
                         - st.mean(NETF(t["gain"]) for t in fl))
        lo, hi = ci(v)
        se = st.stdev(v) / sqrt(len(v))
        yr[y] = {"median": st.median(v), "a_spread": [lo, hi],
                 "b_ci": [st.mean(v) - 1.96 * se, st.mean(v) + 1.96 * se]}
        print("  %s 제거 → 중앙 %+.4f%%p · (a) %+.4f ~ %+.4f · (b) %+.4f ~ %+.4f"
              % (y, st.median(v), lo, hi, yr[y]["b_ci"][0], yr[y]["b_ci"][1]), flush=True)
    flips = [y for y in YS if (yr[y]["median"] > 0) != (r2["median"] > 0)]
    print("  → 부호 반전: %s" % (", ".join(flips) if flips else "없음 (6/6 유지)"),
          flush=True)

    res = {"n": len(tr), "per_trade_all": m_all, "n_filled": st.median(n_fill),
           "n_blocked": st.median(n_block), "metric1": r1, "metric2": r2,
           "leave_one_year_metric2": yr, "flip_years": flips,
           "note": "판정은 두뇌·검증 세션의 몫이다. 여기서는 숫자만 낸다."}
    (OUT / "18-slot-selection-cause.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/18-slot-selection-cause.json")


if __name__ == "__main__":
    main()
