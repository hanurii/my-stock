# -*- coding: utf-8 -*-
"""12 (0단계) — 슬롯5 정본 검증 관문 (개정 반영본).

사양: research/handoff/tasks/SLOT_SIM_SPEC.md · 개정 v2 M3
두뇌 세션 재개정(2026-08-23):
  · 정본은 **④ reuse='nextday'** (슬롯도 손익도 다음 거래일부터). ⑤는 민감도.
  · 후보 순서는 **거래별 정렬키** rng_mode='orderkey' (날짜 전체 셔플은 폐기).
  · 자산곡선 **수준**은 인용 금지 — 모든 값 옆에 **상위 5건 제거 시 값**을 함께 낸다.

이 파일은 격자 결과가 아니다. 시뮬레이터를 바꾼 것이 현행 +20/−10 값을 얼마나
움직이는지, 그 움직임이 무엇에서 오는지만 잰다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/12a-slot-sim-gate.py
난수 seed: 수준 추정 0~199 · 짝비교 0~399 (고정)
"""
from __future__ import annotations

import collections
import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_LEVEL = 200
N_PAIR = 400

FEE = lambda g: ((1 + g / 100) * (1 - 0.0034) / (1 + 0.0014) - 1) * 100  # noqa: E731


# ── 옛 정본 그대로 (cmp_exit.py 의 load() · sim() 복사, 경로 상수만 교정) ──

def old_load():
    ev = []
    for y in range(2021, 2027):
        f = BT / ("bt_%d.json" % y)
        ev += [e for e in json.loads(f.read_text(encoding="utf-8"))["events"]
               if e["result"] in ("win", "loss")]
    seen, U = set(), []
    for e in sorted(ev, key=lambda x: (x["entry_date"], x["code"])):
        k = (e["scan_date"], e["code"], e["pattern"])
        if k not in seen:
            seen.add(k)
            U.append(e)
    return U


def old_sim(events, slots=5, seed=0):
    byday = collections.defaultdict(list)
    for e in events:
        byday[e["entry_date"]].append(e)
    rnd = random.Random(seed)
    eq = 1.0
    held = []
    n = w = 0
    peak, mdd = 1.0, 0.0
    for d in sorted(set(list(byday) + [e["resolve_date"] for e in events])):
        for rd, e, wg in [h for h in held if h[0] <= d]:
            eq += wg * FEE(e["gain_at_resolve_pct"]) / 100
            n += 1
            w += e["result"] == "win"
        held = [h for h in held if h[0] > d]
        free = slots - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]
            rnd.shuffle(c)
            for e in c[:free]:
                held.append((e["resolve_date"], e, eq / slots))
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return (eq - 1) * 100, n, (w / n * 100 if n else 0), mdd * 100


# ── 체결 목록 · 같은날 재채움 횟수 (검증 세션 지적 확인용) ──────────────────

def filled_and_refills(trades, seed, rng_mode, reuse, slots=5):
    """그 seed 에서 체결된 키 목록과, '오늘 결착해 생긴 자리를 오늘 다시 채운' 진입 수."""
    byday = slot_sim._byday(trades)
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in trades]))
    rnd_stream = random.Random(seed)
    held, filled = [], []
    refills = 0
    for d in dates:
        if reuse == "sameday":
            freed_today = sum(1 for h in held if h[0] == d)
            held = [h for h in held if h[0] > d]
        else:
            freed_today = 0
            held = [h for h in held if h[0] >= d]
        free = slots - len(held)
        if d in byday and free > 0:
            c = byday[d][:]
            if rng_mode == "orderkey":
                c.sort(key=lambda t: slot_sim.order_key(seed, t))
            elif rng_mode == "perdate":
                random.Random("%d|%s" % (seed, d)).shuffle(c)
            else:
                rnd_stream.shuffle(c)
            take = c[:free]
            prev_free = free - freed_today          # 오늘 결착이 없었다면 있었을 빈자리
            refills += max(0, len(take) - max(0, prev_free))
            for t in take:
                held.append([t["resolve_date"], t])
                filled.append((t["scan_date"], t["code"], t["pattern"]))
    return filled, refills


def drop_top(trades, k=5):
    """순수익 상위 k건을 뺀 표본 (집중도 점검 — 개정 3-1)."""
    idx = set(sorted(range(len(trades)),
                     key=lambda i: -slot_sim.net(trades[i]["gain"]))[:k])
    return [t for i, t in enumerate(trades) if i not in idx]


def band2(trades, **kw):
    """수준 + 상위 5건 제거 시 수준."""
    b = slot_sim.band(trades, n_runs=N_LEVEL, **kw)
    b5 = slot_sim.band(drop_top(trades, 5), n_runs=N_LEVEL, **kw)
    b["median_drop5"] = b5["median"]
    b["p5_drop5"], b["p95_drop5"] = b5["p5"], b5["p95"]
    b["sign_flips_on_drop5"] = (b["median"] > 0) != (b5["median"] > 0)
    return b


def main():
    ev = old_load()
    trades = [{"code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
               "entry_date": e["entry_date"], "resolve_date": e["resolve_date"],
               "gain": e["gain_at_resolve_pct"], "result": e["result"]} for e in ev]
    print("확정 거래 %d건" % len(trades), flush=True)

    # ── A) 재구현 검증 ──
    diffs = []
    for s in range(50):
        o = old_sim(ev, seed=s)
        n = slot_sim.sim(trades, seed=s, rng_mode="stream", reuse="sameday",
                         base_order="input")
        diffs.append((abs(o[0] - n["equity_pct"]), abs(o[1] - n["n_filled"]),
                      abs(o[3] - n["mdd_pct"])))
    repro = {"seeds": 50, "max_equity_diff": max(d[0] for d in diffs),
             "max_nfill_diff": max(d[1] for d in diffs),
             "max_mdd_diff": max(d[2] for d in diffs)}
    print("[A] 옛 sim() 재현 최대차 — 자산곡선 %.10f · 체결수 %d · 낙폭 %.10f"
          % (repro["max_equity_diff"], repro["max_nfill_diff"], repro["max_mdd_diff"]),
          flush=True)

    # ── B) 조합 분해 ──
    COMBOS = [
        ("①옛 방식 (stream+sameday)", "stream", "sameday"),
        ("②난수만 고침 (orderkey+sameday)", "orderkey", "sameday"),
        ("③재진입만 고침 (stream+nextday)", "stream", "nextday"),
        ("④정본 (orderkey+nextday)", "orderkey", "nextday"),
        ("⑤민감도 (orderkey+nextday_cash_today)", "orderkey", "nextday_cash_today"),
    ]
    combos = []
    for label, rng_mode, reuse in COMBOS:
        b = band2(trades, rng_mode=rng_mode, reuse=reuse)
        b.update({"label": label, "rng_mode": rng_mode, "reuse": reuse})
        combos.append(b)
        print("[B] %-40s 중앙 %+8.1f%% (상위5제거 %+8.1f%%) 5~95%% %+7.1f~%+7.1f "
              "· 체결 %4.0f · 승률 %.1f%% · 낙폭 %.1f%% · 최장연패 %.0f%s"
              % (label, b["median"], b["median_drop5"], b["p5"], b["p95"],
                 b["n_filled"], b["win_rate"], b["mdd"], b["loss_streak"],
                 "  <= 5건에 부호 뒤집힘" if b["sign_flips_on_drop5"] else ""),
              flush=True)

    # ── C) 짝비교 (같은 seed) ──
    def pair(a, b):
        d = [slot_sim.sim(trades, seed=i, rng_mode=a[1], reuse=a[2])["equity_pct"]
             - slot_sim.sim(trades, seed=i, rng_mode=b[1], reuse=b[2])["equity_pct"]
             for i in range(N_PAIR)]
        ds = sorted(d)
        return {"win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
                "diff_median": st.median(d), "p5": ds[N_PAIR // 20 - 1],
                "p95": ds[N_PAIR - N_PAIR // 20]}

    pairs = {}
    for a, b, name in [(COMBOS[1], COMBOS[0], "②난수고침 vs ①옛방식"),
                       (COMBOS[2], COMBOS[0], "③재진입고침 vs ①옛방식"),
                       (COMBOS[3], COMBOS[0], "④정본 vs ①옛방식"),
                       (COMBOS[4], COMBOS[3], "⑤민감도 vs ④정본")]:
        r = pair(a, b)
        pairs[name] = r
        print("[C] %-22s 우세율 %5.1f%% · 차이중앙 %+7.1f%%p (5~95%% %+7.1f~%+7.1f)"
              % (name, r["win_pct"], r["diff_median"], r["p5"], r["p95"]), flush=True)

    # ── D) ①과 ③이 실제로 산 거래가 같은가 · 같은날 재채움 횟수 ──
    inter, na, nb, refills = [], [], [], []
    for s in range(N_LEVEL):
        fa, ra = filled_and_refills(trades, s, "stream", "sameday")
        fb, _ = filled_and_refills(trades, s, "stream", "nextday")
        sa, sb = set(fa), set(fb)
        na.append(len(sa))
        nb.append(len(sb))
        inter.append(len(sa & sb))
        refills.append(ra)
    overlap = {"n_fill_old": st.median(na), "n_fill_nextday": st.median(nb),
               "n_common": st.median(inter),
               "common_share_pct": st.median(inter) / st.median(na) * 100,
               "sameday_refills_old": st.median(refills),
               "refill_share_pct": st.median(refills) / st.median(na) * 100}
    print("[D] 같은 seed 에서 ①이 산 %.0f건 · ③이 산 %.0f건 · 공통 %.0f건 (%.0f%%)"
          % (overlap["n_fill_old"], overlap["n_fill_nextday"], overlap["n_common"],
             overlap["common_share_pct"]), flush=True)
    print("[D] 옛 방식에서 '오늘 결착해 생긴 자리를 오늘 다시 채운' 진입 %.0f회 = 체결의 %.0f%%"
          % (overlap["sameday_refills_old"], overlap["refill_share_pct"]), flush=True)

    # ── E) 구간별 체결 (M4) ──
    SEG = [("2021", "2021-01-01", "2021-12-31"), ("2022", "2022-01-01", "2022-12-31"),
           ("2023", "2023-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
           ("2025~26", "2025-01-01", "2026-12-31")]
    ed = {(t["scan_date"], t["code"], t["pattern"]): t["entry_date"] for t in trades}
    seg = {}
    for label, rng_mode, reuse in COMBOS:
        cnt = collections.defaultdict(list)
        for s in range(N_LEVEL):
            f, _ = filled_and_refills(trades, s, rng_mode, reuse)
            for nm, lo, hi in SEG:
                cnt[nm].append(sum(1 for k in f if lo <= ed[k] <= hi))
        seg[label] = {k: st.median(v) for k, v in cnt.items()}
        print("[E] %-40s 구간별 체결(중앙) %s"
              % (label, {k: round(v) for k, v in seg[label].items()}), flush=True)

    res = {"n_trades": len(trades), "n_level_runs": N_LEVEL, "n_pair_runs": N_PAIR,
           "canon": {"rng_mode": "orderkey", "reuse": "nextday"},
           "reproduction_check": repro, "combos": combos, "pairs": pairs,
           "fill_overlap": overlap, "segment_fills": seg}
    (OUT / "12a-slot-sim-gate.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/12a-slot-sim-gate.json")


if __name__ == "__main__":
    main()
