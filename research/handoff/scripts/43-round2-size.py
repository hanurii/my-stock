# -*- coding: utf-8 -*-
"""43 — **2회차 · 포지션 크기**. 헤드라인 `2a` 는 결과를 보기 «전»에 고정됐다.

| | 청산 | 칸 크기 |
|---|---|---|
| **0회차** | −10% / +20% 전량 | 슬롯5 · `min(자산/5, 가용현금/빈칸)` |
| **1a** | −8% / +20% 절반 / 본전→25일추격 | 〃 |
| **2a (헤드라인)** | **1a 와 같다** | **`min(위험 1.25% ÷ 손절폭, 상한 25%, 가용현금)`** |

**2회차는 «1a 위에만» 얹는다** — 1b·1c 위에 얹으면 격자가 곱으로 커진다.
손절 −8% → 포지션 **15.6%** → 동시 보유 **~6.4개**(미너비니 「4~8종목」과 견준다).

내는 것
-------
분해 표 · **두 문턱(축 명시)** · 상한/자료끝 분리 · **0회차 대비 누적(주판정)** +
**직전 회차(1a) 대비 증분** · **동시 보유 수 «분포»** · **위험목표 초과분** ·
**양방향 관문** · **로그 축 「누적 ≈ 증분 합」 검산** · **종가판 / 실집행 근사판**

🚨 **자료 축을 함께 낸다.** `slot_sim*.band` 의 5~95%는 **seed 축**이고 **M10 상 판정에 못 쓴다.**
자료 축은 `dataaxis.py` — 일별 자산 계열을 블록(20/40/80) 재표집한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/43-round2-size.py
seed 0~199 · 부트스트랩 420824
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                    # noqa: E402
import slot_sim                                          # noqa: E402
import slot_sim_frac as sf                               # noqa: E402
import slot_sim_size as ss                               # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
RISK, CAP = 0.0125, 0.25
# 🚨 **사양 해석**: 「자본이 차면 새 진입 없음」 = **목표 크기를 못 채우면 안 잡는다**.
#    지시서가 「손절 −8% → 포지션 15.6% → 동시 보유 ~6.4개」를 «예측»했는데,
#    그 값은 «쪼갬 금지»에서만 나온다(실측 중앙 7 · 평균 6.8).
#    «쪼갬 허용»이면 작은 포지션이 쌓여 동시 보유 중앙 14 · 체결 601 이 된다.
#    **사양이 스스로 답을 준 자리다.**
PARTIAL = False
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


def build(by, fill_t, fill_s):
    """세 판의 거래 목록. **청산 규칙은 0회차·1a 둘뿐**(2a 는 1a 와 같다)."""
    r41.TARGET_FILL, r41.STOP_FILL = fill_t, fill_s
    r41.N_NO_OPEN[0] = 0
    ev0, _b0 = r41.replay(by, lambda p: r41.resolve_v0(p))
    ev1, _b1 = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    for e in ev0:
        e["stop_frac"] = 0.10
    for e in ev1:
        e["stop_frac"] = 0.08          # 🚨 2a 의 크기는 이 값으로 정해진다
    return ev0, ev1, r41.N_NO_OPEN[0]


def curves(fn, n=10, **kw):
    return [fn(seed=s, **kw)["curve"] for s in range(n)]


def logp(x):
    return math.log(1 + x / 100)


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2

    res = {}
    for fname, ft, fs in FILLS:
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s — 목표 %s · 손절·추격 %s"
              % (fname, "종가" if ft == "close" else "max(목표가,시가)",
                 "종가" if fs == "close" else "min(선,시가)"), flush=True)
        print("#" * 92, flush=True)
        ev0, ev1, n_noopen = build(by, ft, fs)
        if n_noopen:
            print("  ⚠️ 시가 결측으로 종가 되돌림 **%d회**" % n_noopen, flush=True)

        # ── 🚨 양방향 관문 ────────────────────────────────────────────────
        if ft == "close":
            bad, worst = ss.gate_vs_slot5(ev0, n_seed=20)
            print("  🚨 **양방향 관문**(위험/손절 20%%·상한 20%% · 현금규칙 per_slot → "
                  "현금제약 슬롯5): %s · 최대 상대 편차 %.3e"
                  % ("**통과**" if not bad else "**미통과 %d곳** %s" % (len(bad), bad[:2]),
                     worst), flush=True)
            print("     ⚠️ 비트 단위 동일은 불가능하다 — 칸 크기를 `eq/5` vs `eq*0.02/0.10` 로"
                  " 만들어 **부동소수점 경로가 다르다.** 문턱 1e-9 는 잡음(1e-14)보다 5자리 위다.",
                  flush=True)
            if bad:
                print("  → 크기 시뮬을 쓸 수 없다. 중단한다.", flush=True)
                return 1

        row = {}
        for rname, fb, fs_ in REGIMES:
            with Cost(fb, fs_):
                b0 = sf.band(ev0, n_runs=N_SEED, sizing="cash")
                b1 = sf.band(ev1, n_runs=N_SEED, sizing="cash")
                b2 = ss.band(ev1, n_runs=N_SEED, risk=RISK, cap=CAP, partial=PARTIAL)
                c0 = curves(lambda seed: sf.sim_frac(ev0, seed=seed, sizing="cash"))
                c1 = curves(lambda seed: sf.sim_frac(ev1, seed=seed, sizing="cash"))
                c2 = curves(lambda seed: ss.sim_size(ev1, seed=seed, risk=RISK, cap=CAP,
                                                    partial=PARTIAL))
                pt0 = st.mean(r41.per_trade(ev0))
                pt1 = st.mean(r41.per_trade(ev1))
            row[rname] = {
                "0회차": {"band": b0, "per_trade": pt0},
                "1a": {"band": b1, "per_trade": pt1},
                "2a": {"band": b2, "per_trade": pt1},   # 청산이 같으니 거래당도 같다
                "da": {"0회차": da.sweep(c0), "1a": da.sweep(c1), "2a": da.sweep(c2),
                       "2a-0회차": da.sweep(c2, c0), "2a-1a": da.sweep(c2, c1),
                       "1a-0회차": da.sweep(c1, c0)},
            }
            print("", flush=True)
            print("  [%s]" % rname, flush=True)
            print("    %-6s %10s %12s %22s %10s %10s"
                  % ("판", "체결", "자산 중앙", "자산 5~95%(seed축)", "MDD", "거래당"), flush=True)
            for k, bb, pt in (("0회차", b0, pt0), ("1a", b1, pt1), ("2a", b2, pt1)):
                print("    %-6s %10.0f %+11.2f%% %10.2f ~ %+8.2f %9.2f%% %+9.4f%%"
                      % (k, bb["n_filled"], bb["median"], bb["p5"], bb["p95"],
                         bb["mdd"], pt), flush=True)
            print("    자료 축(블록 20/40/80 · 가장 넓은 판이 헤드라인)", flush=True)
            for k in ("0회차", "1a", "2a"):
                print(da.fmt(row[rname]["da"][k], "%s 총수익" % k), flush=True)
            print("    🚨 **주판정 — 짝비교(자료 축)**", flush=True)
            for k in ("2a-0회차", "2a-1a", "1a-0회차"):
                print(da.fmt(row[rname]["da"][k], "%s" % k), flush=True)

            # ── 동시 보유 수 · 위험 초과 ──────────────────────────────────
            print("    동시 보유 수 — 평균 %.2f · P10 %.0f · 중앙 %.0f · P90 %.0f · 최대 %d"
                  % (b2["conc_mean"], b2["conc_p10"], b2["conc_median"],
                     b2["conc_p90"], b2["conc_max"]), flush=True)
            print("      미너비니 「4~8종목」 대비: 중앙 %.0f · **평균만 보면 안 된다**"
                  % b2["conc_median"], flush=True)
            print("    위험목표 초과 — 평균 %+.4f%%p · 건수 %.0f · 현금 부족 진입 차단 %.0f회"
                  % (b2["risk_overrun_mean"], b2["risk_overrun_n"], b2["blocked_cash"]),
                  flush=True)
            print("      ⚠️ **1.25%%는 «계획된» 위험이다.** 갭다운이면 손절선보다 아래에서"
                  " 나가므로 실제 손실이 더 크다.", flush=True)
            print("    자유 현금 최솟값 %+.6f (음수면 초과 투자)" % b2["cash_floor"], flush=True)

            # ── 로그 축 검산 ──────────────────────────────────────────────
            L = {k: logp(row[rname][k]["band"]["median"]) for k in ("0회차", "1a", "2a")}
            lhs = L["2a"] - L["0회차"]
            rhs = (L["1a"] - L["0회차"]) + (L["2a"] - L["1a"])
            print("    🚨 로그 축 검산: 누적 %.6f vs 증분 합 %.6f · 차 %.2e  %s"
                  % (lhs, rhs, abs(lhs - rhs), "**일치**" if abs(lhs - rhs) < 1e-9 else "🚨불일치"),
                  flush=True)
        res[fname] = row

    if da.ALIGN_STATS:
        s0 = da.ALIGN_STATS[0]
        n_pair = len(da.ALIGN_STATS)
        print("", flush=True)
        print("  🚨 짝비교 **날짜 축 정렬** — %d회 정렬 · 첫 건: 합집합 %d일 · "
              "양쪽 공통 %d일(%.1f%%) · 변형에만 %d일 · 0회차에만 %d일"
              % (n_pair, s0["days"], s0["both"], 100 * s0["both"] / s0["days"],
                 s0["only_v"], s0["only_0"]), flush=True)
        print("     ⚠️ 버려진 날은 없다(합집합). 한쪽에만 있는 날은 **직전 값을 끌어온다**"
              "(그날 손익이 없다는 뜻). 끌어온 비율이 크면 그 자체가 한계다.", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "43-round2.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/43-round2.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
