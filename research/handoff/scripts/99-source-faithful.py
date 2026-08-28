# -*- coding: utf-8 -*-
r"""99 — **원전 «절차»를 우리 자료에 돌린다.** 사전등록 `tasks/99-source-faithful.md`.

원전(사용자가 옮긴 1차 본문 · 검산 완료):
```
전체 포지션 25% · 손절 **−10%** · 익절 +20% (손익비 2:1)
사다리  ¼(6.25%) → ½(12.5%) → 전체(25%)   «두 배씩»
방아쇠  **직전 거래의 성공** — 성공하면 한 칸 올리고 실패하면 한 칸 내린다
개수    100% ÷ 비중 = **산출물**. 격자로 돌리지 않는다
```
🚨 **문턱은 ㉡ 에만 걸고, 주지표는 «수익÷낙폭»이다** — 사다리는 노출을 낮추므로
   자산으로만 재면 «정의상» 진다(사전등록 §5).
🚨 ㉠ 의 켈리는 **우리 실측 b 로** 푼다. b=2 를 가정하지 않는다(관문 ⑤).
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

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402
import _lean_load as LL                                        # noqa: E402

r91 = LL.r91
r41 = r91.r41

# ── 원전 값 ───────────────────────────────────────────────────────────────
STOP_SRC, TARGET_SRC = 10.0, 20.0      # 원전 −10% / +20%
CAP_SRC, RISK_SRC = 0.25, 0.025        # 전체 포지션 25% · 계좌 위험 최대 2.5%
# 🚨🚨 `cash_rule` 이 결정적이다 (첫 판에서 틀렸다):
#   "per_slot" = 현금을 «빈 칸 수»로 나눈다 → 슬롯 16 이면 포지션이 «자동으로» 1/16 = 6.25%
#                → **원전의 「전체 포지션 25%」가 «전혀» 안 나온다.** 첫 판이 그래서 무의미했다
#   "seq"      = 현금을 «순차»로 쓴다 → 각 포지션이 cap(25%) 씩, **개수는 «현금»이 정한다**
#                → 25% × 4 = 100% → 원전 그대로
CASH_RULE = "seq"
SLOTS_SRC = 12                         # ⚠️ 원전 «본문»엔 개수 상한이 없다. 정본/웹의 「최대 8~12」 상단.
                                       #    사다리가 작은 포지션을 여럿 들 수 있게 «묶지 않기 위한» 값이고
                                       #    실제 동시보유는 «산출물»로 찍는다(한계 §7-8)
MULT = (0.25, 0.50, 1.00)              # ¼ · ½ · 전체
N_SEED = 200
A_PASS = 55.0

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))


def ladder(recent):
    """원전 사다리 — 직전 청산들의 성패를 이어 «칸»을 만든다.

    「1/4 로 시작 · 성공 거래의 연속선상에서 «두 배씩» · 손실 나면 비중을 줄인다」
    🚨 `recent` 는 직전 청산 «최대 5건»이다. 그것만으로 칸을 다시 만든다 —
       sim 이 사다리 상태를 안 들고 있으므로 «과거로부터 다시 걸어» 온다.
    🚨 미래를 안 본다(청산된 것만 들어온다).
    """
    lvl = 0
    for w in recent:
        lvl = min(2, lvl + 1) if w else max(0, lvl - 1)
    return MULT[lvl]


def realized(t):
    """한 거래의 «실현» 손익(진입가 대비 %). 전체 크기 기준."""
    m = t["masks"][()]
    lots = m.get("lots") or []
    if not lots:
        return None
    epx = lots[0][1]
    g = 0.0
    for _d, sh, px in (m.get("exits") or []):
        g += sh * (px / epx - 1.0)
    return g * 100.0


def build(d0, d1, stop):
    """원전 손절폭으로 경로를 결착한다. 🚨 −8% 가 아니라 −10% 다."""
    by2, _cand, n_all = LL.load_combo(YEARS, d0, d1)
    ev, blocked = [], 0
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=stop,
                                 target=TARGET_SRC, shares=(1.0,), add_stop="floor_entry")
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            t["_hold"] = r91._ord(t["masks"][()]["resolve_date"] or p["entry_date"]) \
                - r91._ord(p["entry_date"])
            ev.append(t)
    return ev, n_all, blocked


def run(ev, size_fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=k, slots=SLOTS_SRC, risk=RISK_SRC, cap=CAP_SRC,
                            reserve=False, fill_rule="truncate", cash_rule=CASH_RULE,
                            size_fn=size_fn) for k in range(n_seed)]


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    print("=" * 106, flush=True)
    print("99 — 원전 «절차»를 우리 자료에 돌린다 · 사전등록 tasks/99", flush=True)
    print("=" * 106, flush=True)
    print("원전: 전체 25%% · 손절 **−10%%** · 익절 +20%% · 사다리 ¼→½→전체 · 방아쇠 «직전 거래 성공»",
          flush=True)
    print("🚨 예상(등록됨): ㉠ 켈리는 «작거나 음수» · ㉡ 자산은 낮아지고 낙폭은 얕아진다\n", flush=True)

    # ── 관문 ② — size_fn=None 이 옛 경로와 «같은가» ────────────────────
    ev8, _n, _b = build("2017-09-01", "2026-08-21", 8.0)
    a = run(ev8, None, 3)
    with r41.Cost(*r91.COST):
        b = [sl.sim_lots(ev8, seed=k, slots=SLOTS_SRC, risk=RISK_SRC, cap=CAP_SRC,
                         reserve=False, fill_rule="truncate", cash_rule=CASH_RULE)
             for k in range(3)]
    same = all(abs(x["equity_pct"] - y["equity_pct"]) < 1e-12 for x, y in zip(a, b))
    print("관문 ② size_fn=None 이 옛 경로와 같은가 → **%s**"
          % ("통과" if same else "🚨 미통과 — 멈춘다"), flush=True)
    if not same:
        return 2

    # ── 관문 ④ — 손절폭이 진입 수를 바꾼다 ──────────────────────────────
    ev10, n_all, blk10 = build(D0, D1, STOP_SRC)
    ev08, _n8, blk08 = build(D0, D1, 8.0)
    print("관문 ④ 손절폭이 진입 수를 바꾼다 — 전체 후보 %s"
          % "{:,}".format(n_all), flush=True)
    print("   −8%%  진입 %s (막힘 %s)  ·  **−10%% 진입 %s (막힘 %s)**  차 %+d"
          % ("{:,}".format(len(ev08)), "{:,}".format(blk08),
             "{:,}".format(len(ev10)), "{:,}".format(blk10),
             len(ev10) - len(ev08)), flush=True)

    # ── ㉠ 우리 실측 p·b → 켈리 (서술) ─────────────────────────────────
    print("\n" + "=" * 106, flush=True)
    print("㉠ 원전 절차로 «비중»을 풀면  (서술 · 문턱 없음 · 손절 −10%% 기준)", flush=True)
    print("  %-16s %8s %8s %10s %10s %8s %10s"
          % ("창", "거래", "승률 p", "평균이익", "평균손실", "손익비 b", "**켈리 f***"), flush=True)
    print("  " + "-" * 86, flush=True)
    kel = {}
    for lab, a_, b_ in BLOCKS + (("── 전체", D0, D1),):
        g = [realized(t) for t in ev10 if a_ <= t["entry_date"] <= b_]
        g = [x for x in g if x is not None]
        w = [x for x in g if x > 0]
        l = [-x for x in g if x <= 0]
        if not w or not l:
            continue
        p = len(w) / len(g)
        bb = st.mean(w) / st.mean(l)
        f = p - (1 - p) / bb
        kel[lab] = {"n": len(g), "p": p, "b": bb, "f": f,
                    "mw": st.mean(w), "ml": st.mean(l)}
        print("  %-16s %8s %7.1f%% %+9.2f%% %9.2f%% %8.2f %+9.2f%%"
              % (lab, "{:,}".format(len(g)), 100 * p, st.mean(w), st.mean(l), bb, 100 * f),
              flush=True)
    print("  " + "-" * 86, flush=True)
    print("  대조(원전)       p=50.0%% · b=2.00 → f* = **+25.00%%**", flush=True)
    print("  🚨 우리 b 는 2 가 «아니다» — 절반 익절 + 추격이라 실현 손익비가 다르다(관문 ⑤ 준수)",
          flush=True)

    # ── ㉡ 사다리 판정 ─────────────────────────────────────────────────
    print("\n" + "=" * 106, flush=True)
    print("㉡ 원전 사다리 판정 · seed %d · **세 창 «모두»** 넘어야 통과" % n_seed, flush=True)
    verd = {}
    for lab, a_, b_ in BLOCKS:
        ev = [t for t in ev10 if a_ <= t["entry_date"] <= b_]
        hold = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_hold"] for t in ev}
        c = run(ev, None, n_seed)
        x = run(ev, ladder, n_seed)

        def hm(res):
            ks = [k for k, kind, *_ in res["fill_log"] if kind == "pilot"]
            hs = [hold[k] for k in ks if k in hold]
            return st.mean(hs) if hs else float("nan")

        ce = [z["equity_pct"] for z in c]
        te = [z["equity_pct"] for z in x]
        dif = sorted(t - u for t, u in zip(te, ce))
        win = 100.0 * sum(1 for v in dif if v > 0) / n_seed
        marc = abs(st.median(ce) / st.median(z["mdd_pct"] for z in c))
        mart = abs(st.median(te) / st.median(z["mdd_pct"] for z in x))
        mde = 2.8 * st.pstdev(dif) / math.sqrt(n_seed)
        okA, okB = win > A_PASS, mart > marc
        verd[lab] = {"win": win, "med": st.median(dif), "mar_c": marc, "mar_t": mart,
                     "A": okA, "B": okB, "mde": mde}
        print("\n  ### %s   (거래 %s)" % (lab, "{:,}".format(len(ev))), flush=True)
        print("     자산 중앙   대조 %+10.2f%%  →  사다리 %+10.2f%%   (짝차 중앙 %+.2f%%p)"
              % (st.median(ce), st.median(te), st.median(dif)), flush=True)
        print("     **수익÷낙폭  대조 %6.2f  →  사다리 %6.2f**   (MDD %.1f%% → %.1f%%)"
              % (marc, mart, st.median(z["mdd_pct"] for z in c),
                 st.median(z["mdd_pct"] for z in x)), flush=True)
        print("     A★ 이기는 판 **%.1f%%**(문턱 %.0f) %s  ·  B★ 수익÷낙폭 %s  ·  D MDE %.2f%%p"
              % (win, A_PASS, "✅" if okA else "❌", "✅" if okB else "❌", mde), flush=True)
        print("     C  노출 %.1f%% → %.1f%%  ·  체결 %.0f → %.0f  ·  보유평균 %.1f → %.1f일  ·  동시보유 %.1f → %.1f"
              % (st.median(z["expo_mean"] for z in c), st.median(z["expo_mean"] for z in x),
                 st.median(z["n_filled"] for z in c), st.median(z["n_filled"] for z in x),
                 st.median(hm(z) for z in c), st.median(hm(z) for z in x),
                 st.median(z["conc_median"] for z in c),
                 st.median(z["conc_median"] for z in x)), flush=True)

    okA = all(v["A"] for v in verd.values())
    okB = all(v["B"] for v in verd.values())
    print("\n" + "=" * 106, flush=True)
    print("**판정: A★ %s · B★ %s (둘 다 · 세 창 모두) → %s**"
          % ("통과" if okA else "미통과", "통과" if okB else "미통과",
             "★ 통과" if (okA and okB) else "미통과"), flush=True)
    (r91.OUT / "99-source-faithful.json").write_text(json.dumps(
        {"kelly": kel, "verdict": verd, "n_seed": n_seed,
         "n_entry_10": len(ev10), "n_entry_08": len(ev08)},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("저장: 99-source-faithful.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
