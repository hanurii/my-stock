# -*- coding: utf-8 -*-
"""78b — **「3일」이 우연인가**. 사용자 질문(2026-08-26).

🚨 **묻는 것은 «최적값»이 아니라 «모양»이다.**
   격자를 훑어 «가장 좋은 칸»을 고르면 그건 사후 고르기다(유형 20).
   여기서 답하려는 것은 하나뿐이다:
```
   기다리는 날이 늘수록 «매끄럽게» 좋아지는가?   →  기전이 있다(확인이 값을 한다)
   3 만 «뾰족하게» 솟아 있는가?                 →  우연이다
```
   **어느 쪽이 나와도 「3 이 최적」이라고 쓰지 않는다.** 모양만 적는다.

⚠️ `trac_days` 0 과 1 은 **같은 규칙**이다(`last_add = −1` 이라 둘 다 첫 봉부터).
   그래서 0 은 안 넣고 1 부터 훑는다 — 78번에서 이미 확인된 사실이다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/78b-tracdays-shape.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

_s = _u.spec_from_file_location("r78", HERE / "78-source-quotes.py")
r78 = _u.module_from_spec(_s)
_s.loader.exec_module(r78)
r77, r76, r74, r41 = r78.r77, r78.r76, r78.r74, r78.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
DAYS = (1, 2, 3, 4, 5, 8, 13, 21)
HALF = (0.5, 0.5)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    n_seed = 20 if "--quick" in sys.argv else 200
    print("=" * 100, flush=True)
    print("78b — 「3일」이 우연인가 (모양을 본다 · 최적값을 고르지 않는다)", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d\n" % (n_all, n_sel, n_seed), flush=True)

    ev0, _b = r77.replay(by2, (1.0,), "avg", r78.B)
    with r41.Cost(*r78.COST):
        eqP = [x["equity_pct"] for x in r76.sim(ev0, r78.BASE_CAP, n_seed)]
    base = r76.summ(r76.sim(ev0, r78.BASE_CAP, n_seed), n_seed)
    print("  대조 P0 한 번에  자산 %+.2f%% · 노출 %.1f%%\n" % (base["equity"], base["expo"]),
          flush=True)

    print("  %6s %11s %11s %8s %6s %6s %8s %9s"
          % ("기다림", "자산중앙", "운나쁠때", "MDD", "승률", "노출", "증액률", "P0 이김"),
          flush=True)
    print("  " + "-" * 78, flush=True)
    RES = {}
    for dd in DAYS:
        ev, _blk = r77.replay(by2, HALF, "avg", r78.TR(dd))
        allT = (True,)
        rate = 100.0 * sum(1 for t in ev if len(t["masks"][allT]["lots"]) > 1) / max(1, len(ev))
        with r41.Cost(*r78.COST):
            rs = r76.sim(ev, r78.BASE_CAP, n_seed)
        s = r76.summ(rs, n_seed)
        eqA = [x["equity_pct"] for x in rs]
        pair = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqA, eqP))
        win = 100.0 * sum(1 for x in pair if x > 0) / len(pair)
        RES[dd] = {**s, "rate": rate, "pair_median": pair[len(pair) // 2], "pair_win": win}
        print("  %5d일 %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%% %7.1f%% %8.1f%%"
              % (dd, s["equity"], s["p5"], s["mdd"], s["win"], s["expo"], rate, win),
              flush=True)

    # ── 모양 판정 ────────────────────────────────────────────────────────
    eqs = [RES[d]["equity"] for d in DAYS]
    best = DAYS[eqs.index(max(eqs))]
    rises = sum(1 for i in range(len(DAYS) - 1) if eqs[i + 1] > eqs[i])
    # 「3 만 뾰족한가」 — 3 을 빼고 그린 곡선에서 3 이 얼마나 튀나
    i3 = DAYS.index(3)
    neigh = (eqs[i3 - 1] + eqs[i3 + 1]) / 2
    spike = eqs[i3] - neigh
    span = max(eqs) - min(eqs)
    print("\n" + "-" * 100, flush=True)
    print("모양 판정 (🚨 「최적값」이 아니라 «모양»을 적는다)", flush=True)
    print("  최고 칸: %d일 (%+.2f%%) · 최저: %d일 (%+.2f%%) · 폭 %.1f%%p"
          % (best, max(eqs), DAYS[eqs.index(min(eqs))], min(eqs), span), flush=True)
    print("  이웃 대비 오른 구간: **%d / %d**  → %s"
          % (rises, len(DAYS) - 1,
             "**대체로 단조** — 기다릴수록 좋아진다(기전 있음)" if rises >= len(DAYS) - 2
             else ("**대체로 단조 감소**" if rises <= 1 else "들쭉날쭉 — 단조가 아니다")),
          flush=True)
    print("  3일이 이웃 평균(%d일·%d일)보다 **%+.2f%%p** (전체 폭의 %.1f%%)  → %s"
          % (DAYS[i3 - 1], DAYS[i3 + 1], spike, 100.0 * abs(spike) / max(1e-9, span),
             "**뾰족하지 않다 — 3 은 특별한 값이 아니다**" if abs(spike) < 0.15 * span
             else "🚨 **3 이 튄다 — 우연일 수 있다**"), flush=True)
    print("\n  ★ 읽는 법 — **「3 이 최적」이라고 쓰지 않는다.**", flush=True)
    print("     모양이 매끄러우면 「기다림이 값을 한다」가 기전이고 3 은 그 위의 한 점일 뿐이다.",
          flush=True)
    print("     3 만 튀면 우연이고, 그때는 3 을 쓸 근거가 없다.", flush=True)
    (OUT / "78b-tracdays-shape.json").write_text(
        json.dumps({"days": list(DAYS), "res": {str(k): v for k, v in RES.items()},
                    "base": base, "n_seed": n_seed, "best": best, "rises": rises,
                    "spike": spike, "span": span}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: 78b-tracdays-shape.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
