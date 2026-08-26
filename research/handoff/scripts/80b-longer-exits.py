# -*- coding: utf-8 -*-
"""80b — **늘린 경로(3년) 위에서 「끝까지 들고 가기」를 다시**
사전등록 `tasks/80-longer-paths.md` (`b287cff9`)

🚨 **두 자료를 안 섞는다** — 관문 ①(하네스 재현)은 «원본 경로»로, 나머지는 «연장본»으로.
🚨 관문 ④ 가 핵심: 보유 중앙이 19일에서 «실제로» 움직였나. 안 움직이면 헛수고였다.
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
SUB = ROOT / ".cache" / "bt5y" / "sub"

import dataaxis as da                                         # noqa: E402
import pyr_trigger as pt                                      # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r79", HERE / "79-stop-and-band.py")
r79 = _u.module_from_spec(_s)
_s.loader.exec_module(r79)
r78, r76, r75a, r74, r41 = r79.r78, r79.r76, r79.r75a, r79.r74, r79.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, SLOTS, BASE_CAP = r78.COST, r78.SLOTS, r78.BASE_CAP
HALF = (0.5, 0.5)
HALF_EXIT = dict(exit_mode="half_trail")
RUN_EXIT = dict(exit_mode="runner", run_trail=25.0)
CAPS = (0.12, 0.14, 0.16, 0.18, 0.20, 0.24)


def load_ext3y():
    """조합 필터를 «연장본»에 걸어 낸다. `r74.load_filtered` 와 같은 필터, 다른 경로."""
    f = SUB / "uspath_ext3y2017.json"
    if not f.exists():
        raise SystemExit("🚨 uspath_ext3y2017.json 이 없다 — 80a 를 먼저 돌린다")
    ext = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    idx = {(q["scan_date"], q["code"], q["pattern"]): q for q in ext}
    by, n_sub = {}, 0
    for y in pt.YEARS:
        ps = pt._load_year(y, {})          # 🚨 «날것» — 옛 연장본을 안 섞는다
        if ps is None:
            raise SystemExit("🚨 uspath_%d.json 없음" % y)
        out = []
        for p in ps:
            q = idx.get((p["scan_date"], p["code"], p["pattern"]))
            if q is not None:
                n_sub += 1
                out.append(q)
            else:
                out.append(p)
        by[y] = out
    return by, n_sub, len(ext)


def hold_stats(by2, shares, ekw):
    ev, _b = r79.replay(by2, shares, 8.0, dict(r78.TR(3), **ekw)
                        if len(shares) > 1 else dict(r78.B, **ekw))
    allT = (True,) * (len(shares) - 1)
    hold, atend = [], 0
    for t in ev:
        m = t["masks"][allT]
        hold.append(0)
        atend += bool(m.get("at_end"))
    return ev, atend, len(ev)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    n_seed = 20 if "--quick" in sys.argv else 200
    print("=" * 100, flush=True)
    print("80b — 늘린 경로(3년) 위에서 「끝까지 들고 가기」 (사전등록 tasks/80)", flush=True)
    print("=" * 100, flush=True)

    # ── 관문 ① — «원본» 경로로만 ────────────────────────────────────────
    by_o, n_all, n_sel, _x = r74.load_filtered()
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by_o, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    ev_n, _b2 = r79.replay(by_o, (1.0,), 8.0, dict(h_lag=True, stay_on="close"))
    worst = 0.0
    with r41.Cost(*COST):
        for s in range(min(20, n_seed)):
            a = sf.sim_frac(ev_ref, slots=SLOTS, seed=s, sizing="cash")["equity_pct"]
            b = sl.sim_lots(ev_n, seed=s, slots=SLOTS, risk=1.0, cap=BASE_CAP)["equity_pct"]
            worst = max(worst, abs(a - b) / max(1e-12, abs(a)))
    print("관문 ①  «원본» 경로로 한 트랜치·1a = sim_frac  %.3e → **%s**"
          % (worst, "통과" if worst < 1e-9 else "🚨 미통과"), flush=True)

    # ── 연장본 적재 ─────────────────────────────────────────────────────
    by_raw, n_sub, n_ext = load_ext3y()
    # 조합 필터를 «같은 방식»으로 다시 건다
    import json as _j
    pack = _j.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({m for d in monthly.values() for m in d if m >= "2016-12"})
    mret = r74.r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r74.r61b.make_flags(mret, sector)

    def keep(p):
        s2 = sector.get(p["code"])
        if not s2:
            return True
        ym = r74.r61.prev_ym(p["scan_date"][:7], 1)
        top = sec_top.get(ym)
        if top is None:
            return True
        if s2 not in top:
            return False
        v = in_pct.get(ym, {}).get(p["code"])
        return (v is None) or (r74.LO <= v < r74.HI)

    by2 = {y: [p for p in ps if keep(p)] for y, ps in by_raw.items()}
    n_c = sum(len(v) for v in by2.values())
    print("연장본 %d개 중 조합에 들어온 것 포함 · 조합 %d (원본 조합 %d)\n"
          % (n_ext, n_c, n_sel), flush=True)

    # ── 관문 ④ (양성 대조) — 보유 중앙이 «실제로» 바뀌었나 ─────────────
    print("관문 ④ (양성 대조) — 상한이 풀렸나", flush=True)
    print("  %-22s %10s %10s %12s" % ("판", "보유중앙", "보유P90", "강제종료"), flush=True)
    for lbl, src in (("원본(1년)", by_o), ("연장본(3년)", by2)):
        pidx = {(p["scan_date"], p["code"], p["pattern"]): p
                for ps in src.values() for p in ps}
        for enm, ekw in (("지금 청산", HALF_EXIT), ("끝까지", RUN_EXIT)):
            ev, _b3 = r79.replay(src, (1.0,), 8.0, dict(r78.B, **ekw))
            hold, atend = [], 0
            for t in ev:
                m = t["masks"][()]
                p = pidx[(t["scan_date"], t["code"], t["pattern"])]
                try:
                    hold.append(p["d"].index(m["resolve_date"]))
                except ValueError:
                    hold.append(len(p["d"]) - 1)
                atend += bool(m.get("at_end"))
            hold.sort()
            n = len(hold)
            print("  %-22s %9d일 %9d일 %11d건 (%.1f%%)"
                  % ("%s · %s" % (lbl, enm), hold[n // 2], hold[9 * n // 10], atend,
                     100.0 * atend / max(1, n)), flush=True)

    # ── 본체 ────────────────────────────────────────────────────────────
    print("\n  %-20s %6s %5s %11s %11s %8s %6s %6s"
          % ("변형", "진입", "체결", "자산중앙", "운나쁠때", "MDD", "승률", "노출"), flush=True)
    print("  " + "-" * 80, flush=True)
    V = (("A0 지금청산·한번에", (1.0,), HALF_EXIT),
         ("B0 끝까지·한번에", (1.0,), RUN_EXIT),
         ("★ L 끝까지·분할", HALF, RUN_EXIT),
         ("M 지금청산·분할", HALF, HALF_EXIT))
    res, curves, evs = {}, {}, {}
    for nm, shares, ekw in V:
        tk = dict(r78.TR(3), **ekw) if len(shares) > 1 else dict(r78.B, **ekw)
        ev, _b4 = r79.replay(by2, shares, 8.0, tk)
        evs[nm] = ev
        rs = r79.run(ev, n_seed)
        res[nm] = r76.summ(rs, n_seed)
        res[nm]["n_entry"] = len(ev)
        curves[nm] = [x["curve"] for x in rs]
        r = res[nm]
        print("  %-20s %6d %5d %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %5.1f%%"
              % (nm, r["n_entry"], r["n_filled"], r["equity"], r["p5"], r["mdd"],
                 r["win"], r["expo"]), flush=True)

    # ── 노출 곡선 + 판정 ────────────────────────────────────────────────
    print("\n★ 노출 곡선 (A0 를 작게/크게)", flush=True)
    big, bigc = {}, {}
    for c in CAPS:
        rs = r79.run(evs["A0 지금청산·한번에"], n_seed, cap=c)
        big["A0 %.2f" % c] = r76.summ(rs, n_seed)
        bigc["A0 %.2f" % c] = [x["curve"] for x in rs]
        v = big["A0 %.2f" % c]
        print("  A0 크기 %.2f  노출 %5.1f%%  자산 %+9.2f%%" % (c, v["expo"], v["equity"]),
              flush=True)

    L, B0 = res["★ L 끝까지·분할"], res["B0 끝까지·한번에"]
    mL = r76.match_on(big, L["expo"])
    mB = r76.match_on(big, B0["expo"])
    print("\n" + "-" * 100, flush=True)
    print("§2 합격선", flush=True)
    print("  L★ 끝까지·분할 %+.2f%% vs 노출맞춘 지금청산 %s %+.2f%% (노출 %.1f vs %.1f) "
          "→ **%s**"
          % (L["equity"], mL, big[mL]["equity"], L["expo"], big[mL]["expo"],
             "통과" if L["equity"] > big[mL]["equity"] else "미통과"), flush=True)
    print("     (76번은 원본 경로에서 청산 축 단독 −115.90%p 였다)", flush=True)
    print("  B0 끝까지·한번에 %+.2f%% vs %s %+.2f%%  → **%s**"
          % (B0["equity"], mB, big[mB]["equity"],
             "통과" if B0["equity"] > big[mB]["equity"] else "미통과"), flush=True)

    with r41.Cost(*COST):
        eqL = [x["equity_pct"] for x in r79.run(evs["★ L 끝까지·분할"], n_seed)]
        eqM = [x["equity_pct"] for x in r79.run(evs["A0 지금청산·한번에"], n_seed,
                                                cap=float(mL.split()[-1]))]
    pr = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100 for a, b in zip(eqL, eqM))
    pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
    print("  P  짝지은 %d판 중앙 **%+.2f%%** · 5%% 하단 %+.2f%% · **이기는 판 %.1f%%** → **%s**"
          % (n_seed, pr[len(pr) // 2], pr[int(len(pr) * .05)], pw,
             "통과" if pr[len(pr) // 2] > 0 and pw > 50 else "미통과"), flush=True)

    print("\n🚨 C 판정 «전» — 답할 수 있는 질문인가 (스트림 %d × 재표집 %d)"
          % (n_seed, max(1, 1000 // n_seed)), flush=True)
    sw = da.sweep(curves["★ L 끝까지·분할"], bigc[mL], n_stream=n_seed,
                  n_rep=max(1, 1000 // n_seed))
    mm = r75a.mde(sw)
    for b in da.BLOCKS:
        v = mm[b]
        if v:
            print("  블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (b, v["median"], v["T"], v["years"], "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)

    (OUT / "80b-longer-exits.json").write_text(json.dumps(
        {"res": res, "big": big, "matchL": mL, "pair_median": pr[len(pr) // 2],
         "pair_win": pw, "n_seed": n_seed, "n_ext": n_ext, "n_combo": n_c},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 80b-longer-exits.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
