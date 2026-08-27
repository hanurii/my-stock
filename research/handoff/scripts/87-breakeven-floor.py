# -*- coding: utf-8 -*-
"""87 — **「+20% 뒤 본전 바닥」이 «단독 매수»에서도 나쁜가**. 사전등록 `tasks/87` (`e404863c`)

🚨 74·75·77 의 −160.87%p 는 `add_stop="floor_entry"`(**증액 «뒤»** 손절)이고
   **우리 정본은 «한 번에 사기»라 그게 발동을 안 한다.** 87번은 «다른 것»을 잰다:
   `_phase2` 의 `s2 = max(a, min(seg))` — **+20%에 절반 판 뒤 추격선의 본전 바닥**.
🚨 비대칭 규약(77번): **우리가 «붙인» 것을 빼는 근거는 «넣는» 근거보다 적어도 된다.**
   → **A(짝비교)만 넘으면 뺀다.** 미통과면 **현행 유지**.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/87-breakeven-floor.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import pyr_trigger as pt                                      # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r84", HERE / "84-case-studies.py")
r84 = _u.module_from_spec(_s)
_s.loader.exec_module(r84)
r74, r41 = r84.r74, r84.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS, RISK, CAP = r74.COST, r74.SLOTS, r74.RISK, r74.CAP
N_SEED = 200


def build(by2):
    """FLOOR_BE 를 «지금 값»으로 경로를 다시 푼다."""
    ev, blk, _sp = r74.replay_masks(by2, (1.0,), "floor_entry")
    return ev, blk


def run(ev, n_seed):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def summ(rs, n):
    eq = sorted(r["equity_pct"] for r in rs)
    return {"med": st.median(eq), "p5": eq[int(n * .05)], "p95": eq[int(n * .95)],
            "mdd": st.median(r["mdd_pct"] for r in rs),
            "filled": st.median(r["n_filled"] for r in rs),
            "win": st.median(r["win_rate"] for r in rs),
            "eq": eq}


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 20 if quick else N_SEED
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 98, flush=True)
    print("87 — 「+20% 뒤 본전 바닥」이 «단독 매수»에서도 나쁜가 (사전등록 tasks/87)", flush=True)
    print("=" * 98, flush=True)
    by2, _a, _b, _c = r74.load_filtered()

    try:
        # ── 현행 (본전 바닥 «있음») ───────────────────────────────────────
        pt.FLOOR_BE = True
        ev_f, blk_f = build(by2)
        rs_f = run(ev_f, n_seed)
        s_f = summ(rs_f, n_seed)

        # ── 관문 ① — 옛 값 재현 ─────────────────────────────────────────
        print("\n관문 ①  현행(FLOOR_BE=True)이 74번 정본을 재현하는가 — "
              "진입 **%d** (기대 3019) · 자산 중앙 **%+.2f%%** (기대 +298.44%%) → **%s**"
              % (len(ev_f), s_f["med"],
                 "통과" if len(ev_f) == 3019 and abs(s_f["med"] - 298.44) < 0.01
                 else "🚨 미통과"), flush=True)

        # ── 비교 (본전 바닥 «없음») ──────────────────────────────────────
        pt.FLOOR_BE = False
        ev_n, blk_n = build(by2)
        rs_n = run(ev_n, n_seed)
        s_n = summ(rs_n, n_seed)
    finally:
        pt.FLOOR_BE = True          # 🚨 반드시 되돌린다

    # ── 관문 ③ — 진입 목록이 같은가 ─────────────────────────────────────
    kf = [(t["scan_date"], t["code"], t["pattern"]) for t in ev_f]
    kn = [(t["scan_date"], t["code"], t["pattern"]) for t in ev_n]
    same_entry = kf == kn
    print("관문 ③  두 판의 «진입 목록»이 같은가 — %d vs %d · 동일 **%s** → **%s**"
          % (len(kf), len(kn), same_entry, "통과" if same_entry else "🚨 미통과 (비교가 깨진다)"),
          flush=True)

    # ── 관문 ①b·② — 1차 매도는 같고, 2차만 달라야 ──────────────────────
    mf = {k: t["masks"][()] for k, t in zip(kf, ev_f)}
    mn = {k: t["masks"][()] for k, t in zip(kn, ev_n)}
    n_same1 = n_diff2 = n_only1 = 0
    for k in mf:
        a_, b_ = mf[k]["exits"], mn.get(k, {}).get("exits", [])
        if not b_:
            continue
        if a_[0][:2] == b_[0][:2] and abs(a_[0][2] - b_[0][2]) < 1e-9:
            n_same1 += 1
        if len(a_) == 1:
            n_only1 += 1
        elif len(b_) > 1 and (a_[-1][0] != b_[-1][0] or abs(a_[-1][2] - b_[-1][2]) > 1e-9):
            n_diff2 += 1
    print("관문 ①b «1차 매도»가 전부 같은가 — 같은 것 %d / %d → **%s**"
          % (n_same1, len(mf), "통과" if n_same1 == len(mf) else "🚨 미통과"), flush=True)
    print("관문 ②  양성 대조 — «2차 매도»가 실제로 달라진 거래 **%d건** "
          "(목표를 못 간 거래 %d건은 애초에 안 바뀐다) → **%s**"
          % (n_diff2, n_only1, "통과" if n_diff2 > 0 else "🚨 미통과 — 아무 일도 안 일어났다"),
          flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    print("\n" + "─" * 98, flush=True)
    print("본체 (seed %d)" % n_seed, flush=True)
    print("   %-26s %12s %12s %12s %9s %8s"
          % ("판", "자산중앙", "운나쁠때", "95% 상단", "MDD", "승률"), flush=True)
    print("   " + "-" * 84, flush=True)
    for nm, s in (("현행 — 본전 바닥 «있음»", s_f), ("비교 — 본전 바닥 «없음»", s_n)):
        print("   %-26s %+11.2f%% %+11.2f%% %+11.2f%% %8.1f%% %7.1f%%"
              % (nm, s["med"], s["p5"], s["p95"], s["mdd"], s["win"]), flush=True)

    # 🚨 `summ` 의 `eq` 는 «정렬된» 리스트라 짝이 아니다 — **seed 별로** 짝짓는다
    pr = sorted(((1 + a["equity_pct"] / 100) / (1 + b["equity_pct"] / 100) - 1) * 100
                for a, b in zip(rs_n, rs_f))
    pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
    okA = pr[len(pr) // 2] > 0 and pw > 50
    print("\n**A★** 「본전 바닥을 «뺀» 판」 vs 「현행」 — 같은 seed 안에서 짝지은 %d판"
          % n_seed, flush=True)
    print("   중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · 95%% 상단 %+.2f%% · **이기는 판 %.1f%%** → **%s**"
          % (pr[len(pr) // 2], pr[int(len(pr) * .05)], pr[int(len(pr) * .95)], pw,
             "통과" if okA else "미통과"), flush=True)

    print("\n" + "=" * 98, flush=True)
    if okA:
        print("판정 — **본전 바닥을 «뺀다».**  (비대칭 규약: 우리가 붙인 것을 빼는 근거는 적어도 된다)",
              flush=True)
        print("🚨 치트시트 원칙 7번을 «즉시» 고친다.", flush=True)
    else:
        print("판정 — **A 미통과 → 현행(본전 바닥 «있음»)을 그대로 둔다.**", flush=True)
        print("   🚨 「본전 바닥이 좋다」는 «주장이 아니다» — «바꿀 근거가 없다»일 뿐이다.",
              flush=True)
    print("   ⚠️ 74·75·77 의 −160.87%p 는 «증액 뒤 손절»이고 이 판과 «다른 것»이다.", flush=True)

    (OUT / "87-breakeven-floor.json").write_text(json.dumps(
        {"floor": {k: v for k, v in s_f.items() if k != "eq"},
         "nofloor": {k: v for k, v in s_n.items() if k != "eq"},
         "pair_median": pr[len(pr) // 2], "pair_win": pw, "okA": okA,
         "n_entry": len(ev_f), "same_entry": same_entry,
         "n_diff2": n_diff2, "n_seed": n_seed}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: 87-breakeven-floor.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
