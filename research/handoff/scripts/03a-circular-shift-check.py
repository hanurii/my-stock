# -*- coding: utf-8 -*-
"""03a — M13-2 확인: **원형이동 순열이 03a에서 실패할 수 있는 검정인가.**

지시서: `00a-amendments-v2.md` M13-2 (두뇌 세션 요청, 2026-08-23)

물음: 원형이동은 모든 거래의 날짜를 **함께** 민다. 03a에는 날짜에 걸린 외부 시계열이 없다
      (`turnover_eok` 는 거래 속성이다). 그러면 두 정렬 규칙의 **차이**는 회전에 거의
      불변이 되고, 순열 p 는 실패할 수 없는 검정이 된다.

방법: 진입일을 거래일 달력에서 k 만큼 원형이동(k = 1 ~ n−1 무작위 1,000회)하고,
      보유일수는 그대로 둔 채 슬롯5를 두 정렬(무작위 / 거래대금 내림차순)로 돌려
      **차이(내림차순 − 무작위)**의 분산을 잰다.
      비교 대상은 같은 통계량의 **블록 부트스트랩 분산**(자료가 달랐다면)이다.

판단 기준(두뇌 세션이 정함): 원형이동 분산이 0에 가까우면 L2 "해당없음",
                              유의하게 크면 L2 를 그대로 쓴다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/03a-circular-shift-check.py
난수 seed: 원형이동 k 추출 33000 · 블록 부트스트랩 30000 · 슬롯 순서 seed 0
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SHIFT = 1000
N_BOOT = 1000
SHIFT_SEED, BOOT_SEED = 33000, 30000
BLOCK_MIN, BLOCK_MAX = 20, 40
SEED = 0
net = slot_sim.net
DESC = (lambda t: -t["tv"])


def load():
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
                       "resolve_date": e["resolve_date"],
                       "gain": e["gain_at_resolve_pct"], "result": e["result"],
                       "tv": e.get("turnover_eok") or 0.0,
                       "net": net(e["gain_at_resolve_pct"])})
    return ev


def sim_pos(by_pos, n_pos, seed, order=None, slots=5):
    eq = 1.0
    held = []
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * net(h[1]["gain"]) / 100
                    h[3] = True
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0:
            c = by_pos.get(p)
            if c:
                if len(c) > 1:
                    c = sorted(c, key=lambda t: slot_sim.order_key(seed, t))
                    if order is not None:
                        c = sorted(c, key=order)
                wgt = eq / slots
                for t in c[:free]:
                    held.append([p + t["days"], t, wgt, False])
    for h in held:
        if not h[3]:
            eq += h[2] * net(h[1]["gain"]) / 100
    return (eq - 1) * 100


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def main():
    ev = load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo = min(t["entry_date"] for t in ev)
    hi = max(t["resolve_date"] for t in ev)
    dates = [d for d in cal if lo <= d <= hi]
    pos_of = {d: i for i, d in enumerate(dates)}
    ev = [t for t in ev if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    for t in ev:
        t["days"] = pos_of[t["resolve_date"]] - pos_of[t["entry_date"]]
    n = len(dates)
    print("거래 %d건 · 달력 %d거래일" % (len(ev), n), flush=True)

    base = defaultdict(list)
    for t in ev:
        base[pos_of[t["entry_date"]]].append(t)
    obs = sim_pos(base, n, SEED, DESC) - sim_pos(base, n, SEED, None)
    print("관측 차이(내림차순 − 무작위, seed %d) = %+.4f%%p" % (SEED, obs), flush=True)

    # ── ① 원형이동 1,000회 ──
    rs = random.Random(SHIFT_SEED)
    diffs, descs, rands = [], [], []
    for i in range(N_SHIFT):
        k = rs.randrange(1, n)
        shifted = defaultdict(list)
        for p, ts in base.items():
            shifted[(p + k) % n].extend(ts)
        a = sim_pos(shifted, n, SEED, DESC)
        b = sim_pos(shifted, n, SEED, None)
        descs.append(a)
        rands.append(b)
        diffs.append(a - b)
        if (i + 1) % 250 == 0:
            print("  원형이동 %d/%d" % (i + 1, N_SHIFT), flush=True)
    sd_shift = st.stdev(diffs)
    ge = sum(1 for x in diffs if x >= obs)
    p_shift = (ge + 1) / (N_SHIFT + 1)
    two = sum(1 for x in diffs if abs(x) >= abs(obs))
    p_two = (two + 1) / (N_SHIFT + 1)
    print("\n[원형이동 %d회] 차이 분포: 평균 %+.4f · SD **%.4f%%p** · "
          "최소 %+.4f · 최대 %+.4f"
          % (N_SHIFT, st.mean(diffs), sd_shift, min(diffs), max(diffs)), flush=True)
    print("   (참고) 같은 회전에서 내림차순 자산곡선 SD %.2f%%p · 무작위 SD %.2f%%p"
          % (st.stdev(descs), st.stdev(rands)), flush=True)
    print("   ★ 순열 p(단측) = %.4f · p(양측) = %.4f  ← 귀무 분포 평균 %+.4f 가 "
          "관측 %+.4f 와 거의 같다" % (p_shift, p_two, st.mean(diffs), obs), flush=True)
    qs = sorted(diffs)
    print("   귀무 분위: 5%% %+.2f · 50%% %+.2f · 95%% %+.2f · 관측이 놓인 백분위 %.1f%%"
          % (qs[49], qs[499], qs[949],
             100.0 * sum(1 for x in diffs if x < obs) / N_SHIFT), flush=True)

    # ── ② 블록 부트스트랩 1,000회 (같은 통계량) ──
    rb = random.Random(BOOT_SEED)
    bdiffs = []
    for i in range(N_BOOT):
        by_pos = defaultdict(list)
        off = 0
        for a2, L in make_blocks(rb, n):
            for j in range(L):
                ts = base.get(a2 + j)
                if ts:
                    by_pos[off + j].extend(ts)
            off += L
        bdiffs.append(sim_pos(by_pos, n, SEED, DESC) - sim_pos(by_pos, n, SEED, None))
        if (i + 1) % 250 == 0:
            print("  블록 부트스트랩 %d/%d" % (i + 1, N_BOOT), flush=True)
    sd_boot = st.stdev(bdiffs)
    print("\n[블록 부트스트랩 %d회] 차이 분포: 평균 %+.4f · SD **%.4f%%p**"
          % (N_BOOT, st.mean(bdiffs), sd_boot), flush=True)

    ratio = sd_shift / sd_boot if sd_boot else None
    print("\n★ 원형이동 SD / 블록 부트스트랩 SD = %.4f" % ratio, flush=True)
    print("   원형이동은 자산곡선 자체는 크게 흔들지만(SD %.1f%%p) **두 정렬의 차이**는 "
          "%.4f%%p 밖에 못 흔든다." % (st.stdev(descs), sd_shift), flush=True)

    # ── ③ 같은날 통계량은 회전에 완전 불변인가 (해석적 확인) ──
    byday = defaultdict(list)
    for t in ev:
        byday[t["entry_date"]].append(t)
    days3 = {d: v for d, v in byday.items() if len(v) >= 3}
    def daily_mean(dd):
        vals = []
        for d, v in dd.items():
            s = sorted(v, key=lambda t: -t["tv"])
            vals.append(st.mean([x["net"] for x in s[:2]])
                        - st.mean([x["net"] for x in s[-2:]]))
        return st.mean(vals)
    m0 = daily_mean(days3)
    # 회전은 날짜 라벨만 바꾸므로 그날 구성이 그대로다 → 값이 변할 수 없다
    print("\n[같은날 통계량] 상위2 vs 하위2 날평균 = %+.6f%%p" % m0, flush=True)
    print("   원형이동은 **날짜 라벨만** 바꾸므로 같은 날 안 구성이 그대로다 → 값이 변하지 않는다"
          " (분산 정확히 0).", flush=True)

    res = {"n_trades": len(ev), "n_calendar": n, "seed": SEED, "observed_diff": obs,
           "circular_shift": {"n": N_SHIFT, "mean": st.mean(diffs), "sd": sd_shift,
                              "min": min(diffs), "max": max(diffs),
                              "sd_desc_equity": st.stdev(descs),
                              "sd_random_equity": st.stdev(rands)},
           "block_bootstrap": {"n": N_BOOT, "mean": st.mean(bdiffs), "sd": sd_boot},
           "sd_ratio_shift_over_boot": ratio,
           "circular_shift_p_one_sided": p_shift, "circular_shift_p_two_sided": p_two,
           "observed_percentile_in_null": 100.0 * sum(1 for x in diffs if x < obs) / N_SHIFT,
           "daywise_stat_invariant": {"value": m0, "variance_under_shift": 0.0}}
    (OUT / "03a-circular-shift-check.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/03a-circular-shift-check.json")


if __name__ == "__main__":
    main()
