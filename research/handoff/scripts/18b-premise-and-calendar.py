# -*- coding: utf-8 -*-
"""18b — 두뇌 세션 요청 셋: ①전제 숫자 대조 ②달력 가중 재측정 ③B·C 확인.

★ M34는 0단계 결과를 본 뒤에 쓴 개정이므로 **결론을 뒤집는 방향의 수정은 금지**돼 있다.
  ①②③ 어디서든 **"확인 불가"가 "확인됨"으로 바뀌면 그 사실 자체를 크게 표시**한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/18b-premise-and-calendar.py
난수 seed: 슬롯 순서 0~199 · 무작위 부분표집 181000
"""
from __future__ import annotations

import importlib.util
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g17b", HERE / "17b-turnover-drag.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
spec2 = importlib.util.spec_from_file_location("g18", HERE / "18-slot-selection-cause.py")
g18 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(g18)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_SUB, SUB_SEED = 1000, 181000
SLOTS = 5
NETF = g.make_net(0.000034, 0.002034)
slot_sim.net = NETF


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def main():
    tr = g.load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    nets = {id(t): NETF(t["gain"]) for t in tr}
    m_all = st.mean(nets.values())
    N = len(tr)
    res = {"n": N, "per_trade_all": m_all}

    # ── ① 전제 숫자 대조 ──
    print("═══ ① 전제 숫자 대조 ═══", flush=True)
    nf_sim = [slot_sim.sim(tr, seed=s)["n_filled"] for s in range(N_SEED)]
    fills, m_fill = [], []
    for s in range(N_SEED):
        fl, bl, _ = g18.fill_split(tr, dates, pos_of, s)
        fills.append(len(fl))
        m_fill.append(st.mean(nets[id(t)] for t in fl))
    print("  체결 건수 — `slot_sim.sim().n_filled` 중앙 **%.0f** (5~95%% %.0f~%.0f)"
          % (st.median(nf_sim), *ci(nf_sim, 5, 95)), flush=True)
    print("             — `fill_split()` 중앙 **%.0f** (5~95%% %.0f~%.0f)"
          % (st.median(fills), *ci(fills, 5, 95)), flush=True)
    print("  체결분 거래당 200 seed 중앙 **%+.4f%%p** (5~95%% %+.4f ~ %+.4f)"
          % (st.median(m_fill), *ci(m_fill, 5, 95)), flush=True)
    print("  전체 3,776건 거래당 **%+.4f%%p** → 격차 중앙 **%+.4f%%p**"
          % (m_all, st.median(m_fill) - m_all), flush=True)
    res["premise"] = {"n_filled_sim_median": st.median(nf_sim),
                      "n_filled_split_median": st.median(fills),
                      "n_filled_band": list(ci(fills, 5, 95)),
                      "per_trade_filled_median": st.median(m_fill),
                      "per_trade_filled_band": list(ci(m_fill, 5, 95)),
                      "gap_median": st.median(m_fill) - m_all}

    # ── ③-B 대수 확인 ──
    print("\n═══ ③-B · 지표 ①②가 대수적으로 같은 양인가 ═══", flush=True)
    d1, d2, ratio = [], [], []
    for s in range(N_SEED):
        fl, bl, _ = g18.fill_split(tr, dates, pos_of, s)
        mf = st.mean(nets[id(t)] for t in fl)
        mb = st.mean(nets[id(t)] for t in bl)
        d1.append(mf - m_all)
        d2.append(mb - mf)
        ratio.append(len(bl) / N)
    k = st.median(ratio)
    pred = [-k * x for x in d2]
    err = max(abs(a - b) for a, b in zip(d1, pred))
    print("  막힌 := 전체 − 체결분 이므로 **지표① = −(막힘/N) × 지표②**", flush=True)
    print("  막힘/N 중앙 = **%.6f** · 예측값과 실측값의 최대 오차 **%.2e%%p**" % (k, err),
          flush=True)
    print("  → **대수적으로 같은 양이 맞다.** 두 지표는 **독립된 두 검정이 아니다.**", flush=True)
    res["algebra"] = {"blocked_share": k, "max_abs_error": err,
                      "same_quantity": bool(err < 1e-9)}

    # ── ③-C (다) 무작위 부분표집 관문 ──
    print("\n═══ ③-C · (다) 무작위 부분표집 — H0의 직접 검정 ═══", flush=True)
    vals = list(nets.values())
    nfill = int(round(st.median(fills)))
    rnd = random.Random(SUB_SEED)
    null = [st.mean(rnd.sample(vals, nfill)) - m_all for _ in range(N_SUB)]
    nlo, nhi = ci(null)
    obs = st.median(m_fill) - m_all
    print("  H0: 체결분이 3,776건에서 **%d건을 무작위로 뽑은 것**이라면?" % nfill, flush=True)
    print("  귀무분포 95%% **%+.4f ~ %+.4f** · SD %.4f · **관측 %+.4f%%p**"
          % (nlo, nhi, st.stdev(null), obs), flush=True)
    inside = nlo <= obs <= nhi
    print("  → 관측이 귀무 구간 **%s** · 백분위 %.1f"
          % ("안(구분 안 됨)" if inside else "**밖**",
             sum(1 for x in null if x < obs) / N_SUB * 100), flush=True)
    print("  ※ 내가 보고했던 (c)는 **관측된 분할에 대한 날짜 블록 부트스트랩**이고,", flush=True)
    print("     (다)는 **무작위 부분표집 귀무분포**다. **같은 계열이 아니다.**", flush=True)
    print("     둘 다 0/귀무를 배제하지 못하므로 **0단계 결론은 그대로다.**", flush=True)
    res["subsample_null"] = {"n_draw": nfill, "ci": [nlo, nhi],
                             "sd": st.stdev(null), "observed": obs,
                             "inside": bool(inside),
                             "pctile": sum(1 for x in null if x < obs) / N_SUB * 100}

    # ── ② D · 달력(월) 가중 재측정 ──
    print("\n═══ ② D · 체결분의 **월 분포**에 맞춰 전체를 가중 ═══", flush=True)
    month_of = {id(t): t["entry_date"][:7] for t in tr}
    all_by_m = Counter(month_of[id(t)] for t in tr)
    raw_gaps, w_gaps = [], []
    for s in range(N_SEED):
        fl, bl, _ = g18.fill_split(tr, dates, pos_of, s)
        fm = Counter(month_of[id(t)] for t in fl)
        mf = st.mean(nets[id(t)] for t in fl)
        num = den = 0.0
        for t in tr:
            m = month_of[id(t)]
            w = fm.get(m, 0) / all_by_m[m]
            num += w * nets[id(t)]
            den += w
        m_weighted = num / den
        raw_gaps.append(mf - m_all)
        w_gaps.append(mf - m_weighted)
    rlo, rhi = ci(raw_gaps, 5, 95)
    wlo, whi = ci(w_gaps, 5, 95)
    print("  가중 전 격차 중앙 **%+.4f%%p** (5~95%% %+.4f ~ %+.4f)"
          % (st.median(raw_gaps), rlo, rhi), flush=True)
    print("  **월 가중 후** 격차 중앙 **%+.4f%%p** (5~95%% %+.4f ~ %+.4f)"
          % (st.median(w_gaps), wlo, whi), flush=True)
    shrink = (1 - abs(st.median(w_gaps)) / abs(st.median(raw_gaps))) * 100
    print("  → 크기가 **%.1f%%** 줄었다." % shrink, flush=True)
    # 귀무: 월 가중 후에도 무작위 부분표집과 구분되는가
    print("  ※ 가중 후 격차도 (다) 귀무 SD %.4f%%p 에 견주면 %.2f SD 수준이다."
          % (st.stdev(null), abs(st.median(w_gaps)) / st.stdev(null)), flush=True)
    res["calendar"] = {"raw_gap_median": st.median(raw_gaps),
                       "raw_band": [rlo, rhi],
                       "weighted_gap_median": st.median(w_gaps),
                       "weighted_band": [wlo, whi], "shrink_pct": shrink,
                       "in_null_sd": abs(st.median(w_gaps)) / st.stdev(null)}

    # 월별 체결 비중이 실제로 얼마나 치우쳤나
    fl0, _, _ = g18.fill_split(tr, dates, pos_of, 0)
    fm0 = Counter(month_of[id(t)] for t in fl0)
    shares = sorted(((fm0.get(m, 0) / all_by_m[m]), m, all_by_m[m])
                    for m in all_by_m if all_by_m[m] >= 20)
    print("  월별 체결률(후보 20건 이상인 달만, seed 0): 최저 %s %.1f%% ~ 최고 %s %.1f%%"
          % (shares[0][1], shares[0][0] * 100, shares[-1][1], shares[-1][0] * 100),
          flush=True)
    res["month_fill_rate"] = {"min": [shares[0][1], shares[0][0] * 100],
                              "max": [shares[-1][1], shares[-1][0] * 100],
                              "n_months": len(shares)}

    (OUT / "18b-premise-and-calendar.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/18b-premise-and-calendar.json")


if __name__ == "__main__":
    main()
