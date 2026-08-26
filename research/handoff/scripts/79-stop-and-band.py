# -*- coding: utf-8 -*-
"""79 — **손절폭과 「얼마나 오른 자리에서 더 사나」**. 사전등록 `tasks/79-stop-and-band.md`

🚨 손절폭은 «탐색»이 아니라 **68번 재현**이다 — 「넓을수록 좋다」가 지금 조합에서도 나오는가.
🚨 어느 쪽이든 **「최적 손절폭은 X%」라고 쓰지 않는다.** 모양만 적는다(78b 규약).
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import dataaxis as da                                         # noqa: E402
import pyr_trigger as pt                                      # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r78", HERE / "78-source-quotes.py")
r78 = _u.module_from_spec(_s)
_s.loader.exec_module(r78)
r77, r76, r75a, r74, r41 = r78.r77, r78.r76, r78.r75a, r78.r74, r78.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS, BASE_CAP = r78.COST, r78.SLOTS, r78.BASE_CAP
STOPS = (6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0)
BANDS = ((0.0, None), (0.0, 10.0), (0.0, 20.0),
         (2.0, None), (2.0, 10.0), (2.0, 20.0),
         (5.0, None), (5.0, 10.0), (5.0, 20.0))
HALF = (0.5, 0.5)


def replay(by2, shares, stop, tkw):
    ev, blk = [], 0
    allT = (True,) * (len(shares) - 1)
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blk += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=stop, target=20.0,
                                 shares=shares, add_stop="avg", **tkw)
            open_until[c] = t["masks"][allT]["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blk


def run(ev, n_seed, cap=BASE_CAP):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=1.0, cap=cap,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def addrate(ev, shares):
    allT = (True,) * (len(shares) - 1)
    return 100.0 * sum(1 for t in ev if len(t["masks"][allT]["lots"]) > 1) / max(1, len(ev))


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    n_seed = 20 if "--quick" in sys.argv else 200
    print("=" * 100, flush=True)
    print("79 — 손절폭 · 증액 문턱의 위아래 (사전등록 tasks/79)", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d\n" % (n_all, n_sel, n_seed), flush=True)

    # ── 관문 ① ─────────────────────────────────────────────────────────
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    ev_n, _b2 = replay(by2, (1.0,), 8.0, dict(h_lag=True, stay_on="close"))
    worst = 0.0
    with r41.Cost(*COST):
        for s in range(min(20, n_seed)):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            worst = max(worst, abs(a - b) / max(1e-12, abs(a)))
    print("관문 ①  한 트랜치·1a·반올림 끈 판 = sim_frac  %.3e → **%s**\n"
          % (worst, "통과" if worst < 1e-9 else "🚨 미통과"), flush=True)

    # ══ ㉯ 손절폭 ═══════════════════════════════════════════════════════
    print("㉯ 손절폭 — 68번(옛 기준선)의 「넓을수록 좋다」가 지금 조합에서도 나오는가", flush=True)
    print("  %6s %11s %11s %8s %6s %6s %8s"
          % ("손절폭", "자산중앙", "운나쁠때", "MDD", "승률", "노출", "증액률"), flush=True)
    print("  " + "-" * 66, flush=True)
    S, curvesS = {}, {}
    for sp in STOPS:
        ev, _b = replay(by2, HALF, sp, r78.TR(3))
        rs = run(ev, n_seed)
        s2 = r76.summ(rs, n_seed)
        s2["rate"] = addrate(ev, HALF)
        s2["n_entry"] = len(ev)
        S[sp] = s2
        curvesS[sp] = [x["curve"] for x in rs]
        print("  %5.0f%% %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%% %7.1f%%"
              % (sp, s2["equity"], s2["p5"], s2["mdd"], s2["win"], s2["expo"], s2["rate"]),
              flush=True)
    eqs = [S[x]["equity"] for x in STOPS]
    mono = all(eqs[i] < eqs[i + 1] for i in range(len(eqs) - 1))
    im = eqs.index(max(eqs))
    uni = (all(eqs[i] < eqs[i + 1] for i in range(im))
           and all(eqs[i] > eqs[i + 1] for i in range(im, len(eqs) - 1)))
    p_mono = 2.0 / math.factorial(len(eqs))
    print("\n  **S 판정** — 단조 증가(넓을수록 좋다): **%s** · 단봉(산 모양): **%s**"
          % ("예" if mono else "아니오", "예" if uni else "아니오"), flush=True)
    print("     무작위 순열이 «단조»일 확률 %.4f%% · 최고 %.0f%% · 최저 %.0f%% · 폭 %.1f%%p"
          % (p_mono * 100, STOPS[im], STOPS[eqs.index(min(eqs))], max(eqs) - min(eqs)),
          flush=True)
    print("     → %s"
          % ("**68번 방향이 지금 조합에서도 재현된다**" if mono
             else ("**단조는 아니지만 매끄러운 산 모양** — 68번의 «끝까지 넓게»는 재현 안 됨"
                   if uni else "**들쭉날쭉 — 68번 방향이 지금 조합에서 재현되지 않는다**")),
          flush=True)
    print("  🚨 어느 쪽이든 «최적 손절폭은 X%%» 라고 쓰지 않는다.\n", flush=True)

    # ══ ㉮ 증액 문턱의 위아래 ═══════════════════════════════════════════
    print("㉮ 증액 문턱 — 「+1% 오른 자리」와 「+30% 오른 자리」를 가른다", flush=True)
    print("  %8s %8s %11s %11s %8s %6s %8s"
          % ("아래문턱", "위문턱", "자산중앙", "운나쁠때", "MDD", "노출", "증액률"), flush=True)
    print("  " + "-" * 66, flush=True)
    G, curvesG = {}, {}
    for lo, hi in BANDS:
        tkw = dict(r78.TR(3, lo), trac_gain_hi=hi)
        ev, _b = replay(by2, HALF, 8.0, tkw)
        rs = run(ev, n_seed)
        g = r76.summ(rs, n_seed)
        g["rate"] = addrate(ev, HALF)
        G[(lo, hi)] = g
        curvesG[(lo, hi)] = [x["curve"] for x in rs]
        print("  %+7.0f%% %8s %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %7.1f%%"
              % (lo, ("없음" if hi is None else "+%.0f%%" % hi), g["equity"], g["p5"],
                 g["mdd"], g["expo"], g["rate"]), flush=True)

    base, head = G[(0.0, None)], G[(0.0, 20.0)]
    print("\n  관문 ③ (양성 대조) — 위 문턱을 걸면 증액률이 «실제로» 주는가", flush=True)
    print("     없음 %.1f%%  →  +20%% %.1f%%  →  **%s**"
          % (base["rate"], head["rate"],
             "통과" if head["rate"] < base["rate"] - 0.5 else
             "🚨 미통과 — 걸었는데 아무 일도 안 일어났다"), flush=True)
    print("  **G 판정** — 위 문턱 +20%% %+.2f%% vs 없음 %+.2f%%  (차 %+.2f%%p) → **%s**"
          % (head["equity"], base["equity"], head["equity"] - base["equity"],
             "통과" if head["equity"] > base["equity"] else "미통과"), flush=True)

    with r41.Cost(*COST):
        eqH = [x["equity_pct"] for x in run(
            replay(by2, HALF, 8.0, dict(r78.TR(3, 0.0), trac_gain_hi=20.0))[0], n_seed)]
        eqB = [x["equity_pct"] for x in run(
            replay(by2, HALF, 8.0, r78.TR(3))[0], n_seed)]
    pr = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqH, eqB))
    pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
    print("  **P 판정** — 짝지은 %d판 중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · "
          "**이기는 판 %.1f%%** → **%s**"
          % (n_seed, pr[len(pr) // 2], pr[int(len(pr) * .05)], pw,
             "통과" if pr[len(pr) // 2] > 0 and pw > 50 else "미통과"), flush=True)

    print("\n🚨 C 판정 «전» — 답할 수 있는 질문인가 (스트림 %d × 재표집 %d)"
          % (n_seed, max(1, 1000 // n_seed)), flush=True)
    sw = da.sweep(curvesG[(0.0, 20.0)], curvesG[(0.0, None)],
                  n_stream=n_seed, n_rep=max(1, 1000 // n_seed))
    mm = r75a.mde(sw)
    for b in da.BLOCKS:
        v = mm[b]
        if v:
            print("  블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (b, v["median"], v["T"], v["years"], "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)

    (OUT / "79-stop-and-band.json").write_text(json.dumps(
        {"stops": {str(k): v for k, v in S.items()},
         "bands": {"%s/%s" % k: v for k, v in G.items()},
         "mono": mono, "uni": uni, "pair_median": pr[len(pr) // 2], "pair_win": pw,
         "n_seed": n_seed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 79-stop-and-band.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
