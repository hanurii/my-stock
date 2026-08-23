# -*- coding: utf-8 -*-
"""17e — 슬롯 수의 **"선택 효과"가 잡음인가 구조인가**.

17c 에서 분산 손실은 이론대로 **단조 감소**(−20.9 → −4.5%p)인데
자산곡선은 단조가 아니었다(−25.9 → −15.6 → −21.2 → −22.1 → −14.2 → −11.7%).
원인 후보가 **"선택 효과"**(슬롯이 어떤 거래를 채우는가)이고, 슬롯 간에 −12.7 ~ −39.6%p로 요동쳤다.

★ 가르는 방법 하나 — **같은 슬롯 수 안에서 seed만 바꿨을 때의 흔들림**과
  **슬롯 수를 바꿨을 때의 흔들림**을 견준다.
  · **seed 내 흔들림이 슬롯 간 흔들림과 같은 규모면 → 잡음.**
    "슬롯을 늘리면 자산곡선이 좋아진다/나빠진다"를 **어느 방향으로도 말할 수 없다.**
  · **seed 내 흔들림이 훨씬 작으면 → 구조.** 그때만 원인을 물을 값이 있다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/17e-selection-noise.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g17b", HERE / "17b-turnover-drag.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
spec2 = importlib.util.spec_from_file_location("g17c", HERE / "17c-slots-and-grid.py")

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
SLOT_LIST = [3, 5, 8, 10, 15, 20]
NETF = g.make_net(0.000034, 0.002034)
slot_sim.net = NETF


def occupancy(trades, dates, pos_of, seed, slots):
    from collections import defaultdict
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for d in byday:
        byday[d].sort(key=lambda t: (t["code"], t["pattern"], t["scan_date"]))
    order = {d: sorted(v, key=lambda t: slot_sim.order_key(seed, t))
             for d, v in byday.items()}
    held, filled = [], []
    for i, d in enumerate(dates):
        held = [h for h in held if h[0] >= i]
        free = slots - len(held)
        c = order.get(d)
        if c and free > 0:
            for t in c[:free]:
                held.append([pos_of[t["resolve_date"]], t])
                filled.append(t)
    return filled


def band(xs, lo=5, hi=95):
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
    m_all = st.mean(NETF(t["gain"]) for t in tr)
    print("전체 %d건 거래당 %+.4f%%p (우대 비용)" % (len(tr), m_all), flush=True)

    print("\n[선택 효과의 seed 내 흔들림] 슬롯마다 %d seed" % N_SEED, flush=True)
    print("  %-4s %10s %22s %8s %10s"
          % ("슬롯", "체결분 중앙", "5~95% 밴드", "폭", "총수익 환산 폭"), flush=True)
    res, mids, widths = {}, [], []
    for S in SLOT_LIST:
        pt, sel = [], []
        for s in range(N_SEED):
            fl = occupancy(tr, dates, pos_of, s, S)
            m = st.mean(NETF(t["gain"]) for t in fl)
            n = len(fl)
            pt.append(m)
            # 같은 건수에서 전체평균 기준과 체결분 기준의 총수익 차이(%p)
            sel.append((((1 + m / 100 / S) ** n - 1)
                        - ((1 + m_all / 100 / S) ** n - 1)) * 100)
        lo, hi = band(pt)
        slo, shi = band(sel)
        res[S] = {"per_trade_median": st.median(pt), "per_trade_band": [lo, hi],
                  "per_trade_width": hi - lo,
                  "sel_median": st.median(sel), "sel_band": [slo, shi],
                  "sel_width": shi - slo}
        mids.append(st.median(pt))
        widths.append(hi - lo)
        print("  %-4d %+9.4f%%p  %+8.4f ~ %+8.4f  %7.4f  %8.1f%%p"
              % (S, st.median(pt), lo, hi, hi - lo, shi - slo), flush=True)

    between = max(mids) - min(mids)
    within = st.median(widths)
    print("\n★ 갈림", flush=True)
    print("  슬롯 **간** 흔들림(체결분 거래당 중앙의 최대−최소) = **%.4f%%p**" % between,
          flush=True)
    print("  슬롯 **내** 흔들림(seed 5~95%% 폭의 중앙) = **%.4f%%p**" % within, flush=True)
    print("  → 비율 슬롯내 ÷ 슬롯간 = **%.2f배**" % (within / between), flush=True)
    verdict = ("**잡음** — 슬롯을 늘렸을 때 자산곡선이 좋아진다/나빠진다를 "
               "어느 방향으로도 말할 수 없다"
               if within >= between * 0.8 else
               "**구조** — 슬롯 간 차이가 seed 잡음보다 크다. 원인을 물을 값이 있다")
    print("  → 판정: %s" % verdict, flush=True)
    res["between_slot_spread"] = between
    res["within_slot_spread_median"] = within
    res["ratio"] = within / between
    res["verdict"] = verdict

    (OUT / "17e-selection-noise.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/17e-selection-noise.json")


if __name__ == "__main__":
    main()
