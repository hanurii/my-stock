# -*- coding: utf-8 -*-
"""77 — **미너비니 규약 그대로의 피라미딩**. 사전등록 `tasks/77-minervini-pyramid.md`

🚨 핵심 차이는 «방아쇠»다 — 「견인력」은 빨리·자주 나고 진입가에 가까이서 난다.
🚨 주지표 = 노출 맞춘 짝비교. A 판정 «전»에 필요 T 를 찍는다.
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

_s = _u.spec_from_file_location("r76", HERE / "76-exit-x-pyramid.py")
r76 = _u.module_from_spec(_s)
_s.loader.exec_module(r76)
r75a, r74, r41, pt = r76.r75a, r76.r74, r76.r41, r76.pt

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS, BASE_CAP = r76.COST, r76.SLOTS, r76.BASE_CAP
N_SEED = 200
BASE = dict(px_round=2)                       # 청산은 1a 기본값
TRAC = dict(BASE, trig_mode="traction", trac_days=3, trac_gain=0.0)
REBRK = dict(BASE, h_lag=True, stay_on="close")

VARIANTS = (
    ("P0 한 번에",      (1.0,),        "avg",         BASE,  "대조"),
    ("★ M1 미너비니",   (0.5, 0.5),    "avg",         TRAC,  "헤드라인"),
    ("M1-floor",        (0.5, 0.5),    "floor_entry", TRAC,  "부수 · 우리 손절"),
    ("M2 파일럿 1/4",   (0.25, 0.75),  "avg",         TRAC,  "부수"),
    ("M3 문턱 +2%",     (0.5, 0.5),    "avg",         dict(TRAC, trac_gain=2.0), "부수"),
    ("M0 재돌파",       (0.5, 0.5),    "avg",         REBRK, "대조 · 방아쇠만 다름"),
)
CAPS = (0.14, 0.16, 0.18, 0.20, 0.24, 0.28)


def replay(by2, shares, astop, tkw):
    """🚨 76번 `replay` 는 `add_stop="floor_entry"` 를 **박아 놨다**. 77번은 손절 방식이
       변형 축이므로 여기서 따로 재생한다. (M1 과 M1-floor 가 «정확히 같은 값»으로
       나온 것이 그 신호였다 — 2026-08-26 자기 정정.)"""
    ev, blk = [], 0
    allT = (True,) * (len(shares) - 1)
    kw = dict(tkw, exit_mode="half_trail")
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blk += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=8.0, target=20.0,
                                 shares=shares, add_stop=astop, **kw)
            open_until[c] = t["masks"][allT]["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blk


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요"); return 2
    n_seed = 20 if "--quick" in sys.argv else N_SEED
    print("=" * 100, flush=True)
    print("77 — 미너비니 규약 그대로의 피라미딩 (사전등록 tasks/77)", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d\n" % (n_all, n_sel, n_seed), flush=True)

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

    res, curves, evs = {}, {}, {}
    print("  %-18s %6s %5s %11s %11s %8s %6s %6s %6s %8s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률", "노출", "증액", "증액률"),
          flush=True)
    print("  " + "-" * 92, flush=True)
    for nm, shares, astop, tkw, _note in VARIANTS:
        ev, _blk = replay(by2, shares, astop, tkw)
        for t in ev:
            t.pop("_path", None)
        evs[nm] = ev
        allT = (True,) * (len(shares) - 1)
        rate = (100.0 * sum(1 for t in ev if len(t["masks"][allT]["lots"]) > 1) / max(1, len(ev))
                if len(shares) > 1 else 0.0)
        rs = [x for x in r76.sim(ev, BASE_CAP, n_seed)]
        res[nm] = r76.summ(rs, n_seed); res[nm]["n_entry"] = len(ev); res[nm]["rate"] = rate
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-18s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%% %6d %7.1f%%"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["expo"], r["added"], rate), flush=True)

    print("\n★ 노출 곡선 (P0 를 작게/크게)", flush=True)
    big, bigc = {}, {}
    for c in CAPS:
        rs = r76.sim(evs["P0 한 번에"], c, n_seed)
        big["P0 %.2f" % c] = r76.summ(rs, n_seed); bigc["P0 %.2f" % c] = [x["curve"] for x in rs]
        v = big["P0 %.2f" % c]
        print("  P0 크기 %.2f  노출 %5.1f%%  자산 %+9.2f%%  하단 %+9.2f%%"
              % (c, v["expo"], v["equity"], v["p5"]), flush=True)

    M1, M0, P0 = res["★ M1 미너비니"], res["M0 재돌파"], res["P0 한 번에"]
    m = r76.match_on(big, M1["expo"])
    print("\n" + "-" * 100, flush=True)
    print("§3 합격선 (대조 = 노출 맞춘 %s · 노출 %.1f vs %.1f)"
          % (m, M1["expo"], big[m]["expo"]), flush=True)
    print("\n🚨 A 판정 «전» — 답할 수 있는 질문인가", flush=True)
    sw = da.sweep(curves["★ M1 미너비니"], bigc[m])
    mm = r75a.mde(sw)
    for b in da.BLOCKS:
        v = mm[b]
        if v:
            print("  블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (b, v["median"], v["T"], v["years"], "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)
    print(da.fmt(sw, "M1 − %s" % m), flush=True)
    # 🚨 **200판 «짝지은» 상대차** — 검증 세션 지적(2026-08-26, `730a3a6e`):
    #    `dataaxis.N_STREAM = 10` 이라 자료 축은 «앞 10 seed»만 쓴다. 자산 표는 200판이다.
    #    검증 세션 자료에서 10판 짝비교 중앙 +11.45% vs 200판 −2.25% — **부호가 반대**였다.
    #    → 유형 23 이 «우리 도구 안»에 있었다. 빠진 숫자를 여기서 낸다.
    import statistics as _st
    eqA = [x["equity_pct"] for x in r76.sim(evs["★ M1 미너비니"], BASE_CAP, n_seed)]
    capm = float(m.split()[-1])
    eqB = [x["equity_pct"] for x in r76.sim(evs["P0 한 번에"], capm, n_seed)]
    pair = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqA, eqB))
    pos = 100.0 * sum(1 for x in pair if x > 0) / len(pair)
    print(chr(10) + "🚨 **짝지은 상대차 — 200판** (자료 축은 앞 10판만 쓴다)", flush=True)
    print("  중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · 95%% 상단 %+.2f%% · **이기는 판 %.1f%%**"
          % (pair[len(pair) // 2], pair[int(len(pair) * .05)],
             pair[int(len(pair) * .95)], pos), flush=True)
    print("  (참고) 짝 «안» 지은 중앙끼리 차를 상대로 환산: %+.2f%%"
          % (((1 + M1["equity"] / 100) / (1 + big[m]["equity"] / 100) - 1) * 100), flush=True)
    dB = M1["equity"] - big[m]["equity"]
    dC = M1["equity"] - M0["equity"]
    print("  A★ 자료 축 0 배제      → **%s**"
          % ("통과" if (sw[sw["_widest"]]["excl0"] and sw[sw["_widest"]]["median"] > 0)
             else "미통과"), flush=True)
    print("  B  자산  M1 %+.2f%% vs %+.2f%%  (차 %+.2f%%p) → **%s**"
          % (M1["equity"], big[m]["equity"], dB, "통과" if dB > 0 else "미통과"), flush=True)
    print("  C  방아쇠 M1 %+.2f%% vs M0 재돌파 %+.2f%%  (차 %+.2f%%p) → **%s**"
          % (M1["equity"], M0["equity"], dC, "통과" if dC > 0 else "미통과"), flush=True)
    print("\n  참고 · 증액률  M1 %.1f%% vs M0 %.1f%%  (「견인력」이 얼마나 자주 나나)"
          % (M1["rate"], M0["rate"]), flush=True)
    (OUT / "77-minervini.json").write_text(json.dumps(
        {"res": res, "big": big, "match": m, "dB": dB, "dC": dC, "n_seed": n_seed},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 77-minervini.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
