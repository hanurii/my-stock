# -*- coding: utf-8 -*-
"""74 — **피라미딩 도구를 새로 만든다**. 사전등록: `tasks/74-pyramid-rebuilt.md`
(개정 1·2 포함 — 커밋 `47637eb7`)

🚨 **파라미터를 결과 보고 바꾸지 않는다.** 헤드라인은 §4 에 미리 고정돼 있다.
🚨 **모든 숫자는 커밋된 파일에서만 나온다** — 73b 가 재현 불가가 된 이유다(개정 2).

실행:
  BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
    python research/handoff/scripts/74-pyramid-rebuilt.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                         # noqa: E402
import pyr_trigger as pt                                      # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s)
_s.loader.exec_module(r61b)
r41, r61 = r61b.r41, r61b.r61

OUT = ROOT / ".cache" / "bt5y" / "out"
COST = (0.0, 0.002)          # 우대수수료 — 세금만
RISK, CAP, SLOTS = 0.02, 0.20, 5          # = 5칸 20%
STOP, TARGET = 8.0, 20.0
LO, HI = 0.10, 0.30          # 그룹 «내» 2·3등급
N_SEED = 200

HALF = (0.5, 0.5)
THIRD = (1 / 3, 1 / 3, 1 / 3)

# ── §4 변형 — 헤드라인 한 칸(★)은 값 보기 «전»에 고정됐다 ─────────────────
#    §개정 3 — H′(고친 방아쇠)는 **돌리기 «전»에** 등록한 두 번째 칸(★′). 합격선은 §5 그대로.
FIX = dict(h_lag=True, stay_on="close")     # 고친 방아쇠
VARIANTS = (
    ("P0 한 번에",    (1.0,), False, "floor_entry", {}, "대조"),
    ("★ H 헤드라인",  HALF,   True,  "floor_entry", {}, "1/2→1/2 · 예약 · 원가 아래 금지"),
    ("H-noreserve",   HALF,   False, "floor_entry", {}, "예약 안 함"),
    ("H-avgstop",     HALF,   True,  "avg",         {}, "손절 = 평균단가 −8%"),
    ("T 세 번",       THIRD,  True,  "floor_entry", {}, "1/3씩 · 예약"),
    ("T-noreserve",   THIRD,  False, "floor_entry", {}, "1/3씩 · 예약 안 함"),
    ("★′ H′ 고친방아쇠", HALF, True,  "floor_entry", FIX, "개정 3 — 등록된 둘째 칸"),
    ("H′-avgstop",    HALF,   True,  "avg",         FIX, "부수 — H-avgstop 의 짝"),
)


# ═════════════════════════════════════════════════════════════════════════
# 1. 경로 적재 + «경로 단계» 조합 필터
# ═════════════════════════════════════════════════════════════════════════
def load_filtered():
    """조합(주도 업종 ∧ 그룹 내 2·3등급)을 **경로 단계**에서 건다.

    🚨 진입 «뒤»에 거르면 안 산 종목이 `open_until` 을 잡아 나중 진입을 막는다
       (73b §3 에서 찾은 것 — 값이 +263% → +295% 로 바뀐다).
    """
    ext_idx, n_ext = pt._load_ext()
    by = {}
    for y in pt.YEARS:
        ps = pt._load_year(y, ext_idx)
        if ps is None:
            raise SystemExit("🚨 uspath_%d.json 이 없다" % y)
        by[y] = ps
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({m for d in monthly.values() for m in d if m >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r61b.make_flags(mret, sector)

    def keep(p):
        s = sector.get(p["code"])
        if not s:
            return True                       # 제3군 = 통과 (61번과 같다)
        ym = r61.prev_ym(p["scan_date"][:7], 1)
        top = sec_top.get(ym)
        if top is None:
            return True
        if s not in top:
            return False
        v = in_pct.get(ym, {}).get(p["code"])
        return (v is None) or (LO <= v < HI)

    by2 = {y: [p for p in ps if keep(p)] for y, ps in by.items()}
    n_all = sum(len(v) for v in by.values())
    n_sel = sum(len(v) for v in by2.values())
    return by2, n_all, n_sel, n_ext


def replay_masks(by, shares, add_stop, tkw=None):
    """`open_until` 재현 — 39·41번과 같은 규약.

    🚨 **사양이 안 정한 곳**: 조합마다 결착일이 다르다. `open_until` 은
       **「전부 산다」 조합의 결착일**을 쓴다(시뮬이 아무것도 안 막았을 때의 값).
       변형마다 자기 결착일을 쓰므로 진입 수가 변형마다 다를 수 있다 —
       그건 규칙의 «진짜» 결과이므로 표에 그대로 찍는다.
    """
    ev, blocked, spread = [], 0, 0
    allT = (True,) * (len(shares) - 1)
    for y in sorted(by):
        open_until = {}
        for p in by[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP,
                                 target=TARGET, shares=shares, add_stop=add_stop,
                                 **(tkw or {}))
            rds = {m["resolve_date"] for m in t["masks"].values()}
            if len(rds) > 1:
                spread += 1
            open_until[c] = t["masks"][allT]["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blocked, spread


# ═════════════════════════════════════════════════════════════════════════
# 2. 관문
# ═════════════════════════════════════════════════════════════════════════
def gate_1(by2, n_seed=30):
    """트랜치 하나 → 새 시뮬 = `sim_frac(slots=5, sizing="cash")`."""
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, STOP, TARGET))
    ev_new, _b2, _sp = replay_masks(by2, (1.0,), "floor_entry")
    worst, bad = 0.0, 0
    with r41.Cost(*COST):
        for s in range(n_seed):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_new, seed=s, slots=SLOTS, risk=RISK, cap=CAP)["equity_pct"]
            rel = abs(a - b) / max(1e-12, abs(a))
            worst = max(worst, rel)
            bad += rel > 1e-9
    print("관문 ①  트랜치 하나 = sim_frac(5칸·현금제약)  %d판 · 최대 상대오차 %.3e → **%s**"
          % (n_seed, worst, "통과" if not bad else "🚨 미통과 %d판" % bad), flush=True)
    print("        (옛 판 진입 %d · 새 판 진입 %d — 같아야 한다)"
          % (len(ev_ref), len(ev_new)), flush=True)
    return not bad and len(ev_ref) == len(ev_new)


# ═════════════════════════════════════════════════════════════════════════
# 3. 본체
# ═════════════════════════════════════════════════════════════════════════
def run(ev, reserve, n_seed):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP,
                            reserve=reserve, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2

    print("=" * 96, flush=True)
    print("74 — 피라미딩 도구를 새로 만든다 (사전등록 tasks/74 · 개정 1·2)", flush=True)
    print("=" * 96, flush=True)
    by2, n_all, n_sel, n_ext = load_filtered()
    print("경로 %d → **조합 %d (%.1f%%)**  · 250봉 연장 %d개 갈아끼움 · 우대수수료 %s"
          % (n_all, n_sel, 100.0 * n_sel / n_all, n_ext, COST), flush=True)
    print("seed %d · 5칸 %.0f%% · 청산 −%.0f%% / +%.0f%% 절반 → 본전 → 25일 추격\n"
          % (n_seed, CAP * 100, STOP, TARGET), flush=True)

    ok1 = gate_1(by2, n_seed=min(30, n_seed))
    print("", flush=True)

    print("  %-17s %6s %5s %11s %11s %8s %6s %8s %6s %6s %7s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률",
             "거래당", "증액", "막힘", "묶인돈"), flush=True)
    print("  " + "─" * 98, flush=True)
    res, curves, evs = {}, {}, {}
    for nm, shares, reserve, add_stop, tkw, _note in VARIANTS:
        ev, blk, spread = replay_masks(by2, shares, add_stop, tkw)
        evs[nm] = ev
        rs = run(ev, reserve, n_seed)
        eq = sorted(x["equity_pct"] for x in rs)
        res[nm] = {
            "n_entry": len(ev), "open_until_blocked": blk, "mask_spread": spread,
            "equity": st.median(eq), "p5": eq[int(n_seed * .05)],
            "mdd": st.median(x["mdd_pct"] for x in rs),
            "n_filled": st.median(x["n_filled"] for x in rs),
            "conc_median": st.median(x["conc_median"] for x in rs),
            "n_added": st.median(x["n_added"] for x in rs),
            "n_add_blocked": st.median(x["n_add_blocked"] for x in rs),
            "resv": st.median(x["resv_frac_mean"] for x in rs),
            "expo": st.median(x["expo_mean"] for x in rs),
            "per_trade": st.median(x["filled_per_trade"] for x in rs),
            "win": st.median(x["win_rate"] for x in rs),
            "truncated": st.median(x["truncated"] for x in rs)}
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-17s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %+7.3f%% %6d %6d %6.2f%%"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["per_trade"], r["n_added"], r["n_add_blocked"],
                 r["resv"]), flush=True)

    P0 = res["P0 한 번에"]
    H = res["★ H 헤드라인"]

    # ── 관문 ④⑤ ────────────────────────────────────────────────────────
    print("\n관문 ④  예약함 판에서 «현금 부족 증액 막힘» = 0 건", flush=True)
    for nm in ("★ H 헤드라인", "H-avgstop", "T 세 번"):
        print("        %-17s 막힘 %d → **%s**"
              % (nm, res[nm]["n_add_blocked"],
                 "통과" if res[nm]["n_add_blocked"] == 0 else "🚨 미통과"), flush=True)
    print("관문 ⑤  조용한 절단 금지 — 위 표에 진입·체결·증액·막힘·묶인돈 전부 찍었다.", flush=True)
    print("        `open_until` 로 막힌 경로: " + " · ".join(
        "%s %d" % (k, v["open_until_blocked"]) for k, v in res.items()), flush=True)
    print("        조합에 따라 결착일이 «달라지는» 경로: " + " · ".join(
        "%s %d" % (k, v["mask_spread"]) for k, v in res.items()), flush=True)

    # ── §5 합격선 ───────────────────────────────────────────────────────
    print("\n" + "─" * 96, flush=True)
    print("§5 합격선 — 값 보기 «전»에 적힌 것 (대조는 «같은 실행 안의» P0)", flush=True)
    JUDGED = ("★ H 헤드라인", "★′ H′ 고친방아쇠")
    verdict, sws = {}, {}
    for nm in JUDGED:
        V = res[nm]
        A = V["equity"] > P0["equity"]
        B = V["p5"] > P0["p5"]
        C = V["mdd"] > P0["mdd"]          # MDD 는 음수 — 클수록 얕다
        verdict[nm] = {"A": A, "B": B, "C": C}
        print("\n  【%s】" % nm, flush=True)
        print("  A  자산     %+9.2f%%  vs  P0 %+9.2f%%   (차 %+9.2f%%p)  → **%s**"
              % (V["equity"], P0["equity"], V["equity"] - P0["equity"],
                 "통과" if A else "미통과"), flush=True)
        print("  B★ 운나쁠때 %+9.2f%%  vs  P0 %+9.2f%%   (차 %+9.2f%%p)  → **%s**"
              % (V["p5"], P0["p5"], V["p5"] - P0["p5"], "통과" if B else "미통과"),
              flush=True)
        print("  C★ MDD      %8.1f%%   vs  P0 %8.1f%%    (차 %+8.1f%%p)  → **%s**"
              % (V["mdd"], P0["mdd"], V["mdd"] - P0["mdd"], "통과" if C else "미통과"),
              flush=True)
        sws[nm] = da.sweep(curves[nm], curves["P0 한 번에"])
        print("  D  자료 축 짝비교 (블록 20/40/80 · **헤드라인은 가장 넓은 구간**)", flush=True)
        print(da.fmt(sws[nm], "%s − P0" % nm), flush=True)
    print("\n  🚨 A 는 사전등록에 «장식일 수 있다»고 미리 적었다 "
          "— 73번 관측 최대 차이 +25.3%p", flush=True)

    # ── 부수 — 손절 축을 뺀 판. **판정 아님**(§4: 합격선은 ★·★′ 에만) ────
    print("\n  (부수 · 판정 아님) 손절 축을 뺀 판 — 「피라미딩만」 남긴다", flush=True)
    for nm in ("H-avgstop", "H′-avgstop"):
        sws[nm] = da.sweep(curves[nm], curves["P0 한 번에"])
        print(da.fmt(sws[nm], "%s − P0" % nm), flush=True)
    # ── ⭐ 「손절 바닥 축」 짝비교 — «같은 방아쇠끼리» 손절만 다르다 ──────────
    #    §4 가 «미리 기대를 낮춰 적어 둔» 축이고, 두 방아쇠에서 «같은 방향»이면
    #    「여덟 칸 중 최선」보다 다중비교에 훨씬 덜 취약하다(검증 세션 6d41912e).
    print("\n  ⭐ 손절 바닥 축 (같은 방아쇠끼리 · 손절만 다르다) — 자료 축", flush=True)
    for a, b in (("H-avgstop", "★ H 헤드라인"), ("H′-avgstop", "★′ H′ 고친방아쇠")):
        k = "%s − %s" % (a, b)
        sws[k] = da.sweep(curves[a], curves[b])
        print(da.fmt(sws[k], k), flush=True)
    sw, sw2 = sws["★ H 헤드라인"], sws["H-avgstop"]

    # ── ★ 진짜 질문: 예약이 무엇을 했나 ─────────────────────────────────
    print("\n" + "─" * 96, flush=True)
    print("★ 분해 — 73번의 「덜 무섭다」는 피라미딩 덕인가, 분산 덕인가", flush=True)
    NR = res["H-noreserve"]
    print("  예약함     자산 %+9.2f%% · 운나쁠때 %+9.2f%% · MDD %.1f%% · 동시보유 %d · 체결 %d"
          % (H["equity"], H["p5"], H["mdd"], H["conc_median"], H["n_filled"]), flush=True)
    print("  예약 안 함 자산 %+9.2f%% · 운나쁠때 %+9.2f%% · MDD %.1f%% · 동시보유 %d · 체결 %d"
          % (NR["equity"], NR["p5"], NR["mdd"], NR["conc_median"], NR["n_filled"]),
          flush=True)
    print("  → 예약을 풀면 동시보유가 %+d 늘고 체결이 %+d 늘어난다. "
          "MDD 차이 %+.1f%%p 가 «그것» 때문인지가 이 줄이 답하는 것."
          % (NR["conc_median"] - H["conc_median"], NR["n_filled"] - H["n_filled"],
             NR["mdd"] - H["mdd"]), flush=True)
    AV = res["H-avgstop"]
    print("\n  손절 축   원가 아래 금지 %+9.2f%%  vs  평균단가 −8%% %+9.2f%%  (차 %+.2f%%p)"
          % (H["equity"], AV["equity"], H["equity"] - AV["equity"]), flush=True)
    print("  🚨 증액은 정의상 진입가 «위»에서만 난다 → 트랜치 하나만 들어가도 손절선이 "
          "본전으로 점프한다. 이 칸은 «피라미딩»이 아니라 «손절선 점프»를 재고 있을 수 있다.",
          flush=True)

    # ── ★ 노출 맞춘 대조 — 「낙폭이 얕다」 vs 「그냥 덜 샀다」 ────────────────
    #    검증 세션 지적(2026-08-25): H′ 는 자본의 24% 를 묶어 두고 파일럿은 목표의
    #    절반이다. **덜 넣으면 낙폭은 기계적으로 얕아진다.** 그러면 C 통과는
    #    「피라미딩이 위험을 줄인다」와 구분되지 않는다.
    #    🚨 «딱 맞는 한 칸»을 찾아 보고하면 그 칸을 고른 셈이 되므로 **곡선**으로 낸다.
    print("\n" + "─" * 96, flush=True)
    print("★ 노출 맞춘 대조 — P0 를 «작게» 사게 만들어 노출을 맞춘다 (부수 · 판정 아님)",
          flush=True)
    print("  %-18s %8s %11s %11s %8s" % ("판", "노출", "자산중앙", "운나쁠때", "MDD"),
          flush=True)
    small = {}
    for c in (0.20, 0.16, 0.13, 0.10, 0.08):
        with r41.Cost(*COST):
            rs = [sl.sim_lots(evs["P0 한 번에"], seed=s, slots=SLOTS, risk=RISK,
                              cap=c, reserve=False, fill_rule="truncate",
                              cash_rule="per_slot") for s in range(n_seed)]
        eq = sorted(x["equity_pct"] for x in rs)
        small["P0 cap %.2f" % c] = {
            "expo": st.median(x["expo_mean"] for x in rs), "equity": st.median(eq),
            "p5": eq[int(n_seed * .05)], "mdd": st.median(x["mdd_pct"] for x in rs)}
        v = small["P0 cap %.2f" % c]
        print("  P0 · 크기 %.2f    %7.2f%% %+10.2f%% %+10.2f%% %7.1f%%"
              % (c, v["expo"], v["equity"], v["p5"], v["mdd"]), flush=True)
    for nm in ("★ H 헤드라인", "★′ H′ 고친방아쇠", "H′-avgstop"):
        print("  %-16s %7.2f%% %+10.2f%% %+10.2f%% %7.1f%%   ← 이 곡선 «어디»에 놓이나"
              % (nm, res[nm]["expo"], res[nm]["equity"], res[nm]["p5"],
                 res[nm]["mdd"]), flush=True)

    (OUT / "74-pyramid-rebuilt.json").write_text(
        json.dumps({"res": res, "gate1": ok1, "n_seed": n_seed,
                    "n_paths": n_all, "n_combo": n_sel,
                    "verdict": verdict,
                    "dataaxis": {k: v for k, v in sws.items()}},
                   ensure_ascii=False, indent=1,
                   default=str), encoding="utf-8")
    print("\n저장: 74-pyramid-rebuilt.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
