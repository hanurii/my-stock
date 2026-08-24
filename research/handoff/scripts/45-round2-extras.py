# -*- coding: utf-8 -*-
"""45 — 2회차 보강 둘. **판정 아님. 숫자만.**

① **분해 표** — 이 회차가 겨냥한 축이다.
   1회차의 진짜 결과가 「거래당」이 아니라 **「격차」**에서 나왔다:
   `0회차 산술 +17.58% · 관측 −16.11% · 격차 −33.69%p` → `1a 격차 +2.21%p`.
   **2a 의 격차가 1a 보다 더 좁아졌는지가 이 회차의 답이다.**
   🚨 **산술 예측을 「체결 × 0.20 × 거래당」으로 못 쓴다** — 2a 는 칸 크기가 20%가 아니다.
      대신 시뮬 안에서 **곱하지 않은 합** `Σ (비중 × 몫 × 순수익)` 을 그대로 모은다.
      **슬롯5에서는 그 값이 「체결 × 0.20 × 거래당」과 같다**(비중이 늘 0.20이므로).

② **체결분 거래당 vs 방아쇠 전수 거래당**
   자본 제약이 커지면 **「어느 거래가 들어가는가」를 «신호»가 아니라 «순서»가 정한다.**
   - 체결분이 **더 나쁘면** → 자본 제약이 나쁜 거래를 고른다(**선택 손실**)
   - **비슷하면** → 순서가 무작위에 가깝고 손실은 **분산에서만** 온다
   0회차·1a·2a 를 나란히 두면 **회차가 갈수록 선택 손실이 커지는지**가 보인다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/45-round2-extras.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402
import slot_sim_frac as sf                               # noqa: E402
import slot_sim_size as ss                               # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)
OUT = ROOT / ".cache" / "bt5y" / "out"

N = 60                    # seed 수 (중앙값이 안정되는 선)
RISK, CAP, PARTIAL = 0.0125, 0.25, False
REGIMES = (("무비용", 0.0, 0.0), ("한국-미래에셋", 0.0014, 0.0034))
FILLS = (("종가판", "close", "close"), ("실집행 근사판", "limit", "market"))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def agg(fn, n=N):
    rs = [fn(seed=s) for s in range(n)]
    return {"equity": st.median([r["equity_pct"] for r in rs]),
            "arith": st.median([r["arith_pct"] for r in rs]),
            "n_filled": st.median([r["n_filled"] for r in rs]),
            "filled_pt": st.median([r["filled_per_trade"] for r in rs])}


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    res = {}
    for fname, ft, fs in FILLS:
        r41.TARGET_FILL, r41.STOP_FILL = ft, fs
        ev0, _ = r41.replay(by, lambda p: r41.resolve_v0(p))
        ev1, _ = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
        for e in ev0:
            e["stop_frac"] = 0.10
        for e in ev1:
            e["stop_frac"] = 0.08
        for rname, fb, fs_ in REGIMES:
            with Cost(fb, fs_):
                a0 = agg(lambda seed: sf.sim_frac(ev0, seed=seed, sizing="cash"))
                a1 = agg(lambda seed: sf.sim_frac(ev1, seed=seed, sizing="cash"))
                a2 = agg(lambda seed: ss.sim_size(ev1, seed=seed, risk=RISK, cap=CAP,
                                                  partial=PARTIAL))
                all0 = st.mean(r41.per_trade(ev0))
                all1 = st.mean(r41.per_trade(ev1))
            k = "%s|%s" % (fname, rname)
            res[k] = {"0회차": {**a0, "all_pt": all0, "n_all": len(ev0)},
                      "1a": {**a1, "all_pt": all1, "n_all": len(ev1)},
                      "2a": {**a2, "all_pt": all1, "n_all": len(ev1)}}
            print("", flush=True)
            print("=" * 96, flush=True)
            print("%s · %s" % (fname, rname), flush=True)
            print("=" * 96, flush=True)
            print("① 분해 — 산술 예측(곱하지 않은 합) vs 관측", flush=True)
            print("  %-6s %8s %12s %12s %12s %13s"
                  % ("판", "체결", "체결분거래당", "산술 예측", "관측", "**격차**"), flush=True)
            for name in ("0회차", "1a", "2a"):
                d = res[k][name]
                print("  %-6s %8.0f %11.4f%% %11.2f%% %11.2f%% %12.2f%%p"
                      % (name, d["n_filled"], d["filled_pt"], d["arith"], d["equity"],
                         d["equity"] - d["arith"]), flush=True)
            g1 = res[k]["1a"]["equity"] - res[k]["1a"]["arith"]
            g2 = res[k]["2a"]["equity"] - res[k]["2a"]["arith"]
            print("  → 2a 격차가 1a 보다 **%s** (%.2f%%p → %.2f%%p · 차 %+.2f%%p)"
                  % ("좁다" if g2 > g1 else "넓다", g1, g2, g2 - g1), flush=True)
            print("", flush=True)
            print("② 체결분 거래당 vs 방아쇠 전수 거래당 — **선택 손실이 있나**", flush=True)
            print("  %-6s %14s %14s %12s %10s"
                  % ("판", "체결분", "방아쇠 전수", "차이", "체결/전수"), flush=True)
            for name in ("0회차", "1a", "2a"):
                d = res[k][name]
                print("  %-6s %13.4f%% %13.4f%% %11.4f%%p %9.1f%%"
                      % (name, d["filled_pt"], d["all_pt"], d["filled_pt"] - d["all_pt"],
                         100 * d["n_filled"] / d["n_all"]), flush=True)
            print("  → %s" % ("차이가 음수면 **자본 제약이 나쁜 거래를 고른다**(선택 손실), "
                              "0 근처면 **순서가 무작위에 가깝고 손실은 분산에서만** 온다.",),
                  flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "45-round2-extras.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/45-round2-extras.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
