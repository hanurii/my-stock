# -*- coding: utf-8 -*-
"""78 — **원문 인용에서 나온 네 가지**. 사전등록 `tasks/78-source-quotes.md` (`f66bfd70`)

★ 헤드라인 A = **조건부 분할매수** — 「최근 청산 5건 중 3건 이상 손실이면 파일럿, 아니면 전액」.
  원문 「are your last 4 or 5 stocks profitable on balance」에서 나온 자다.
🚨 주지표 = 노출 맞춘 짝비교 + **200판 짝지은 상대차**. 자료 축은 «스트림 200 × 재표집 5».
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

import dataaxis as da                                         # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r77", HERE / "77-minervini.py")
r77 = _u.module_from_spec(_s)
_s.loader.exec_module(r77)
r76, r75a, r74, r41, pt = r77.r76, r77.r75a, r77.r74, r77.r41, r77.pt

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS, BASE_CAP = r77.COST, r77.SLOTS, r77.BASE_CAP
N_SEED = 200
B = dict(px_round=2)
TR = lambda days=3, gain=0.0: dict(B, trig_mode="traction",          # noqa: E731
                                   trac_days=days, trac_gain=gain)
HYB = dict(B, trig_mode="hybrid", trac_days=3, trac_gain=0.0,
           h_lag=True, stay_on="close")
HALF, QUAD = (0.5, 0.5), (0.25, 0.25, 0.25, 0.25)
THIRD = (1 / 3, 1 / 3, 1 / 3)   # D 는 «1차·2차»가 있어야 결합이 뜻을 갖는다
CAPS = (0.14, 0.16, 0.18, 0.20, 0.24, 0.28)

# ── §1 변형 ──────────────────────────────────────────────────────────────
VARIANTS = (
    ("P0 한 번에",    (1.0,), B,            "대조"),
    ("M1 (77번)",     HALF,   TR(3),        "파일럿½·견인력 3일"),
    ("B0 견인력 0일", HALF,   TR(0),        "부수 · 「바로 채운다」"),
    ("B1 견인력 1일", HALF,   TR(1),        "부수"),
    ("C ¼×4단",       QUAD,   TR(1),        "부수 · 「아주 조금씩」"),
    # 🚨 D 는 «두 단»이면 증액이 한 번뿐이라 결합이 성립하지 않는다(hybrid ≡ traction).
    #    예비 실행에서 D 가 M1 과 «소수점까지 같은 값»으로 나와 잡혔다.
    #    사전등록이 「1차 견인력 · 2차 이후 재돌파」였으므로 **세 단**이 등록된 뜻이다.
    ("D 결합(3단)",   THIRD,  HYB,          "부수 · 1차 견인력·2차 재돌파"),
)


def loss_heavy(recent):
    """원문 「last 4 or 5 stocks profitable on balance」의 조작적 정의.

    직전 청산 **5건** 중 **3건 이상 손실**이면 「확신 없음」 → 파일럿(=`alt` 안 씀).
    🚨 5건이 안 쌓였으면 **「확신 있음」(전액)** 으로 본다 — 사전등록 §2-2.
       반대로 잡으면 초반이 통째로 파일럿이 된다.
    `pick(recent) -> True` 면 `alt`(전액)를 쓴다. 그래서 **부정**해서 돌려준다.
    """
    if len(recent) < 5:
        return True                       # 자료 없음 → 전액
    return sum(1 for x in recent if not x) < 3


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    n_seed = 20 if "--quick" in sys.argv else N_SEED
    print("=" * 104, flush=True)
    print("78 — 원문 인용에서 나온 네 가지 (사전등록 tasks/78)", flush=True)
    print("=" * 104, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d\n" % (n_all, n_sel, n_seed), flush=True)

    # ── 관문 ① ─────────────────────────────────────────────────────────
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    ev_n, _b2 = r76.replay(by2, (1.0,), r76.HALF_EXIT, dict(h_lag=True, stay_on="close"))
    worst = 0.0
    with r41.Cost(*COST):
        for s in range(min(20, n_seed)):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            worst = max(worst, abs(a - b) / max(1e-12, abs(a)))
    print("관문 ①  한 트랜치·1a·반올림 끈 판 = sim_frac  %.3e → **%s**\n"
          % (worst, "통과" if worst < 1e-9 else "🚨 미통과"), flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    res, curves, evs = {}, {}, {}
    print("  %-16s %6s %5s %11s %11s %8s %6s %6s %6s %7s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률", "노출", "증액", "증액률"),
          flush=True)
    print("  " + "-" * 92, flush=True)
    for nm, shares, tkw, _note in VARIANTS:
        ev, _blk = r77.replay(by2, shares, "avg", tkw)
        evs[nm] = ev
        allT = (True,) * (len(shares) - 1)
        rate = (100.0 * sum(1 for t in ev if len(t["masks"][allT]["lots"]) > 1)
                / max(1, len(ev)) if len(shares) > 1 else 0.0)
        rs = r76.sim(ev, BASE_CAP, n_seed)
        res[nm] = r76.summ(rs, n_seed)
        res[nm]["n_entry"] = len(ev)
        res[nm]["rate"] = rate
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-16s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%% %6d %6.1f%%"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["expo"], r["added"], rate), flush=True)

    # ── ★ A 조건부 — 파일럿 판에 «전액» 대안을 붙인다 ───────────────────
    #    🚨 사전등록 §2-1: `open_until` 은 «분할 판»의 결착일로 통일한다.
    #       그래서 후보 목록은 M1 의 것을 그대로 쓰고, 거래마다 spec 만 갈아 끼운다.
    full_by_key = {(t["scan_date"], t["code"], t["pattern"]): t
                   for t in evs["P0 한 번에"]}
    ev_a, n_missing = [], 0
    for t in evs["M1 (77번)"]:
        k = (t["scan_date"], t["code"], t["pattern"])
        f = full_by_key.get(k)
        if f is None:
            n_missing += 1
        t2 = dict(t)
        t2["alt"] = None if f is None else {"shares": f["shares"], "masks": f["masks"]}
        ev_a.append(t2)
    print("\n★ A 조건부 — 「최근 5건 중 3건 이상 손실이면 파일럿, 아니면 전액」", flush=True)
    print("  후보 %d건 · 전액 대안을 못 찾은 건 %d건 («분할 판» 결착일로 통일 — 사전등록 §2-1)"
          % (len(ev_a), n_missing), flush=True)
    with r41.Cost(*COST):
        rs_a = [sl.sim_lots(ev_a, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot", pick=loss_heavy)
                for s in range(n_seed)]
    res["★ A 조건부"] = r76.summ(rs_a, n_seed)
    res["★ A 조건부"]["n_entry"] = len(ev_a)
    curves["★ A 조건부"] = [x["curve"] for x in rs_a]
    ra = res["★ A 조건부"]
    n_full = st.median(x["n_alt"] for x in rs_a)
    n_pil = st.median(x["n_base"] for x in rs_a)
    print("  %-16s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%%"
          % ("★ A 조건부", ra["n_entry"], ra["n_filled"], ra["equity"], ra["p5"],
             ra["mdd"], ra["win"], ra["expo"]), flush=True)
    print("  관문 ③ (양성 대조) — **전액 %d건 · 파일럿 %d건**  → **%s**"
          % (n_full, n_pil,
             "통과 — 조건이 실제로 갈렸다" if n_full and n_pil
             else "🚨 미통과 — 한쪽이 0. 조건이 «한 번도» 안 갈렸다"), flush=True)

    # ── 노출 곡선 ───────────────────────────────────────────────────────
    print("\n★ 노출 곡선 (P0 를 작게/크게)", flush=True)
    big, bigc = {}, {}
    for c in CAPS:
        rs = r76.sim(evs["P0 한 번에"], c, n_seed)
        big["P0 %.2f" % c] = r76.summ(rs, n_seed)
        bigc["P0 %.2f" % c] = [x["curve"] for x in rs]
        v = big["P0 %.2f" % c]
        print("  P0 크기 %.2f  노출 %5.1f%%  자산 %+9.2f%%  하단 %+9.2f%%"
              % (c, v["expo"], v["equity"], v["p5"]), flush=True)

    # ── §3 합격선 ───────────────────────────────────────────────────────
    A, M1 = res["★ A 조건부"], res["M1 (77번)"]
    m = r76.match_on(big, A["expo"])
    with r41.Cost(*COST):
        eqA = [x["equity_pct"] for x in rs_a]
        eqP = [x["equity_pct"] for x in r76.sim(evs["P0 한 번에"],
                                                float(m.split()[-1]), n_seed)]
        eqM = [x["equity_pct"] for x in r76.sim(evs["M1 (77번)"], BASE_CAP, n_seed)]
    pair = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqA, eqP))
    pos = 100.0 * sum(1 for x in pair if x > 0) / len(pair)
    pairM = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqA, eqM))
    posM = 100.0 * sum(1 for x in pairM if x > 0) / len(pairM)

    print("\n" + "-" * 104, flush=True)
    print("§3 합격선 (대조 = 노출 맞춘 %s · 노출 %.1f vs %.1f)"
          % (m, A["expo"], big[m]["expo"]), flush=True)
    print("  A1★ 조건부 > 항상분할   A %+.2f%% vs M1 %+.2f%%  (차 %+.2f%%p) → **%s**"
          % (A["equity"], M1["equity"], A["equity"] - M1["equity"],
             "통과" if A["equity"] > M1["equity"] else "미통과"), flush=True)
    print("      짝지은 200판 — 중앙 %+.2f%% · **이기는 판 %.1f%%**"
          % (pairM[len(pairM) // 2], posM), flush=True)
    print("  A2★ 조건부 > 노출맞춘 P0   %+.2f%% vs %+.2f%%  (차 %+.2f%%p) → **%s**"
          % (A["equity"], big[m]["equity"], A["equity"] - big[m]["equity"],
             "통과" if A["equity"] > big[m]["equity"] else "미통과"), flush=True)
    print("  B   짝지은 200판 (vs 노출맞춘 P0) — 중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · "
          "**이기는 판 %.1f%%** → **%s**"
          % (pair[len(pair) // 2], pair[int(len(pair) * .05)], pos,
             "통과" if pair[len(pair) // 2] > 0 and pos > 50 else "미통과"), flush=True)

    print("\n🚨 C 판정 «전» — 답할 수 있는 질문인가 "
          "(구성: **스트림 %d × 재표집 %d**)" % (n_seed, max(1, 1000 // n_seed)), flush=True)
    sw = da.sweep(curves["★ A 조건부"], bigc[m],
                  n_stream=n_seed, n_rep=max(1, 1000 // n_seed))
    mm = r75a.mde(sw)
    for b in da.BLOCKS:
        v = mm[b]
        if v:
            print("  블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (b, v["median"], v["T"], v["years"], "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)
    print(da.fmt(sw, "A − %s" % m), flush=True)

    (OUT / "78-source-quotes.json").write_text(json.dumps(
        {"res": res, "big": big, "match": m, "n_full": n_full, "n_pilot": n_pil,
         "pair_median": pair[len(pair) // 2], "pair_win": pos,
         "pairM_median": pairM[len(pairM) // 2], "pairM_win": posM,
         "n_seed": n_seed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 78-source-quotes.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
