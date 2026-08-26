# -*- coding: utf-8 -*-
"""75a — **「이 질문이 이 자료로 답할 수 있는 질문인가」를 «계산»한다**

사용자 요청(2026-08-26). [[minervini-fidelity-2026-08]] 에서 한 번 쓴 방법 —
거기서는 **필요 +51.3%p > 최대 관측 +40.1%p** 라 「구할 수 있는 자료로는 답할 수
없는 질문」이 계산으로 나왔다. 같은 것을 피라미딩에 한다.

## 산수 (짝비교 자료 축 위에서)

`band_paired` 는 `Δ = exp(Σ 재표집된 일별 로그차) − 1` 을 낸다. **로그 축에서 재면 선형**이다.
```
L  = ln(1 + 중앙/100)                      관측된 효과 (로그)
hw = [ln(1+상단/100) − ln(1+하단/100)] / 2   95% 반폭 (로그)
```
자료가 **T 배**로 늘면 (같은 성질의 자료가 T 배 더 있다면):
```
L  → T · L                    효과는 «누적»이라 길이에 비례해 는다
hw → √T · hw                  블록 수가 T 배가 되므로 √T 로만 는다
0 을 배제하려면  T·L > √T·hw   →   **T > (hw / |L|)²**
```
🚨 **가정 둘을 먼저 적는다**
1. **효과의 «하루당 크기»가 유지된다** — 다른 구간에서 더 작으면 T 는 더 커진다.
2. **블록 구조가 그대로 늘어난다** — 자기상관이 더 강하면 T 는 더 커진다.
**즉 여기서 나오는 T 는 «가장 낙관적인 하한»이다.**

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/75a-mde.py
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

import dataaxis as da                                         # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r74", HERE / "74-pyramid-rebuilt.py")
r74 = _u.module_from_spec(_s)
_s.loader.exec_module(r74)
r41 = r74.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
YEARS_WINDOW = 9.0           # 2017-09 ~ 2026-08


def curves_for(by2, shares, reserve, add_stop, tkw, n_seed, cap=None):
    ev, _b, _s2 = r74.replay_masks(by2, shares, add_stop, tkw)
    with r41.Cost(*r74.COST):
        rs = [sl.sim_lots(ev, seed=s, slots=r74.SLOTS, risk=r74.RISK,
                          cap=(cap if cap is not None else r74.CAP),
                          reserve=reserve, fill_rule="truncate",
                          cash_rule="per_slot") for s in range(n_seed)]
    eq = sorted(x["equity_pct"] for x in rs)
    return [x["curve"] for x in rs], st.median(eq)


def mde(sw):
    """블록별 (관측 로그효과 L · 95% 반폭 hw · 필요 배수 T · 필요 연수)."""
    out = {}
    for b in da.BLOCKS:
        v = sw[b]
        lo, hi, md = v["lo"], v["hi"], v["median"]
        # 🚨 −100% 이하는 로그가 안 된다 — 그런 칸은 표시하고 건너뛴다
        if min(1 + lo / 100, 1 + hi / 100, 1 + md / 100) <= 0:
            out[b] = None
            continue
        L = math.log(1 + md / 100)
        lg, hg = math.log(1 + lo / 100), math.log(1 + hi / 100)
        # 🚨 **0 을 향한 쪽까지의 거리**를 쓴다. 구간이 로그 축에서도 «비대칭»이라
        #    (상단−하단)/2 로 쓰면 틀린다. 효과가 음수면 «위쪽» 끝이 0 을 향한다.
        #    2026-08-26 정정 — 처음엔 평균 반폭을 썼고, 그 결과
        #    「필요 0.9배(=지금 자료로 충분)인데 0 배제 ❌」라는 모순이 나왔다.
        d = (hg - L) if L < 0 else (L - lg)
        T = (d / abs(L)) ** 2 if L else float("inf")
        out[b] = {"median": md, "lo": lo, "hi": hi, "L": L, "d": d,
                  "T": T, "years": T * YEARS_WINDOW,
                  "need_pct": (math.exp(d) - 1) * 100, "excl0": v["excl0"],
                  # ★ 자기 점검: T < 1 이면 «지금 자료로 이미 0 배제»여야 한다.
                  #   둘이 어긋나면 식이 틀린 것이다 — 값을 쓰지 말고 멈춘다.
                  "consistent": (T < 1.0) == bool(v["excl0"])}
    return out


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2
    n_seed = 60 if "--quick" in sys.argv else r74.N_SEED
    print("=" * 100, flush=True)
    print("75a — 이 질문이 이 자료로 답할 수 있는 질문인가 (사용자 요청 26-08-26)", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d · 창 %.0f년\n" % (n_all, n_sel, n_seed, YEARS_WINDOW),
          flush=True)

    HALF, FIX = r74.HALF, r74.FIX
    made = {}
    made["P0"], e0 = curves_for(by2, (1.0,), False, "floor_entry", {}, n_seed)
    made["P0(0.16)"], e016 = curves_for(by2, (1.0,), False, "floor_entry", {}, n_seed,
                                        cap=0.16)
    made["H"], eH = curves_for(by2, HALF, True, "floor_entry", {}, n_seed)
    made["H-avgstop"], eHa = curves_for(by2, HALF, True, "avg", {}, n_seed)
    made["H′"], eHp = curves_for(by2, HALF, True, "floor_entry", FIX, n_seed)
    made["H′-avgstop"], eHpa = curves_for(by2, HALF, True, "avg", FIX, n_seed)
    print("자산 중앙 — P0 %+.2f%% · P0(0.16) %+.2f%% · H %+.2f%% · H-avg %+.2f%% · "
          "H′ %+.2f%% · H′-avg %+.2f%%\n" % (e0, e016, eH, eHa, eHp, eHpa), flush=True)

    PAIRS = (("H − P0", "H", "P0"),
             ("H′ − P0", "H′", "P0"),
             ("H-avgstop − P0", "H-avgstop", "P0"),
             ("H′-avgstop − P0", "H′-avgstop", "P0"),
             ("H′-avgstop − P0(0.16) ★노출맞춤", "H′-avgstop", "P0(0.16)"),
             ("H-avgstop − H ★손절축", "H-avgstop", "H"),
             ("H′-avgstop − H′ ★손절축", "H′-avgstop", "H′"))

    print("  %-32s %5s %10s %10s %9s %11s %8s"
          % ("비교", "블록", "관측 효과", "필요 효과", "필요 배수", "필요 연수", "0배제"),
          flush=True)
    print("  " + "─" * 96, flush=True)
    RES = {}
    # 🚨 **`L` 과 `hw` 를 «같은 구성»에서 낸다** (검증 세션 2026-08-26):
    #    기본 sweep 은 스트림 10 × 재표집 100 이라 중앙이 관측 짝 성과와 어긋날 수 있다.
    #    같은 예산(1,000값)을 «스트림 200 × 재표집 5» 로 재배치해 다시 돌린다.
    NS = None if "--old-streams" in sys.argv else min(n_seed, 200)
    NR = None if NS is None else max(1, 1000 // NS)
    print("자료 축 구성 — 스트림 %s × 재표집 %s (기본값은 10 × 100)"
          % (NS or 10, NR or 100), flush=True)
    print("", flush=True)
    for lbl, a, b in PAIRS:
        sw = da.sweep(made[a], made[b], n_stream=NS, n_rep=NR)
        m = mde(sw)
        RES[lbl] = {str(k): v for k, v in m.items()}
        for blk in da.BLOCKS:
            v = m[blk]
            if v is None:
                print("  %-32s %5d   (로그 불가 — 하단이 −100%% 이하)"
                      % (lbl if blk == da.BLOCKS[0] else "", blk), flush=True)
                continue
            print("  %-32s %5d %+9.2f%% %+9.2f%% %8.2f배 %9.0f년 %8s%s"
                  % (lbl if blk == da.BLOCKS[0] else "", blk,
                     v["median"], v["need_pct"], v["T"], v["years"],
                     "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)
        print("", flush=True)

    print("─" * 100, flush=True)
    print("읽는 법", flush=True)
    print("  **관측 효과** = 지금 자료가 낸 차이(누적·로그 중앙)", flush=True)
    print("  **필요 효과** = 이 자료 크기에서 0 을 배제하려면 필요한 차이", flush=True)
    print("  **필요 배수** = 지금 효과 그대로일 때 0 을 배제하는 데 필요한 «자료 배수»",
          flush=True)
    print("  🚨 **가장 낙관적인 하한이다** — 효과의 하루당 크기가 유지되고 자기상관이 "
          "안 세진다는 가정 둘이 들어 있다.", flush=True)
    bad = [(k, b) for k, m in RES.items() for b, v in m.items()
           if v and not v["consistent"]]
    print("  ★ 자기 점검 (T<1 ⟺ 0배제): **%s**"
          % ("전부 일치" if not bad else "🚨 어긋난 칸 %d — 값을 쓰지 말 것 %s"
             % (len(bad), bad)), flush=True)
    print("  ⚠️ `dataaxis` 기본값은 «스트림 10 × 재표집 100» 이라 자료 축이 **앞 10판만** 쓴다. "
          "여기서는 «전 판 × 재표집 %s» 로 재배치해 **`L` 과 `hw` 를 같은 구성에서** 냈다."
          % (NR or 100), flush=True)
    print("     (옛 구성으로 보려면 `--old-streams`. 77번에서 짝200 +21.49% vs "
          "band_paired(10) +3.2% 로 크게 어긋난 것이 계기다.)", flush=True)
    (OUT / "75a-mde.json").write_text(
        json.dumps({"n_seed": n_seed, "equity": {"P0": e0, "P0_016": e016, "H": eH,
                                                 "H_avg": eHa, "Hp": eHp, "Hp_avg": eHpa},
                    "mde": RES}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 75a-mde.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
