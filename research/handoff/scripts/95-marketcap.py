# -*- coding: utf-8 -*-
r"""95 — **「작은 회사라서 크게 오른다」가 «돈»이 되는가.** 사전등록 `tasks/95-marketcap.md`.

🚨 **문턱은 «실현 수익»에만 건다. MFE 는 «서술»로만 찍는다**(92→94 의 교훈을 «먼저» 박은 것).
🚨 **신선한 표본 밖이 없다**(사전등록 §1). 통과해도 「재현」이지 「새 확인」이 아니다.

절차
  고르기 1999-04~2011-12  →  5분위 «경계»를 만들고, **실현 수익이 가장 좋은 분위**를 고른다
  판정①  2012-01~2017-08  }  그 분위를 «우선순위»로 넣고 대조(무작위)와 **짝비교**
  판정②  2017-09~2026-08  }  **둘 «다»** A★·B★ 를 넘어야 통과

★ 고르기 단계 자체가 **사용자 가설의 «방향»을 시험한다** —
  가설이 옳다면 고르기 창이 **«낮은» 분위(작은 회사)**를 골라야 한다.
  **높은 분위를 고르면 그 자리에서 가설이 반증된다.**
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402
from slot_sim import order_key                                 # noqa: E402

_s = _u.spec_from_file_location("m92", HERE / "92-us-fundamentals.py")
m92 = _u.module_from_spec(_s)
_s.loader.exec_module(m92)
r91 = m92.r91
r41 = r91.r41

CAP = Path(r"D:\stock-data\derived\95-cap-pit.json")
PICK = ("1999-04-01", "2011-12-31")
TEST1 = ("2012-01-01", "2017-08-31")
TEST2 = ("2017-09-01", "2026-08-21")
NQ = 5
CAP_BACK = 14
TOV_DAYS = 20
N_SEED = 200
N_SEL = 100              # 고르기 단계 판수 — «판정»이 아니라 «고르기»라 적게 쓴다(그 사실을 적는다)
A_PASS = 60.0


def asof(pairs, day):
    """`date < day` 인 것 중 가장 늦은 것. 관문 ① — 당일 값을 쓰면 룩어헤드."""
    ds = [d for d, _v in pairs]
    i = bisect.bisect_left(ds, day) - 1
    return pairs[i] if i >= 0 else None


def build(years, d0, d1, capdb, funddb, roef):
    """거래를 만들고 시총·거래대금·(94 겹침용) roe 딱지를 붙인다."""
    ev, miss = [], Counter()
    for y in years:
        f = m92.SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        ps = [p for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
              if d0 <= p["entry_date"] <= d1]
        open_until = {}
        for p in ps:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                miss["같은 종목 겹침"] += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                                 target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
            mk = t["masks"][()]
            open_until[c] = mk["resolve_date"] or p["entry_date"]

            rec = capdb.get(c)
            if not rec or not rec["cap"]:
                miss["시총 자료 없음"] += 1
                continue
            a = asof(rec["cap"], p["entry_date"])
            if a is None:
                miss["진입 전 시총 없음"] += 1
                continue
            if m92._ord(p["entry_date"]) - m92._ord(a[0]) > CAP_BACK:
                miss["시총이 %d일 넘게 묵음" % CAP_BACK] += 1
                continue
            t["_cap"] = a[1]
            t["_logcap"] = math.log(a[1])

            # 관문 ⑤ — 20 거래일 평균 거래대금 (진입 «전»)
            tv = [v for d, v in rec["tov"] if d < p["entry_date"]][-TOV_DAYS:]
            t["_adv"] = (st.mean(tv) if tv else None)

            # 관문 ④ — 94 의 `roe 1분위` 와 겹치는가
            t["_roe1"] = roef(c, p["entry_date"], funddb)
            epx = p.get("entry_price")
            hs = p.get("h") or []
            t["_mfe"] = ((max(hs) / epx - 1) * 100) if (epx and hs) else float("nan")
            t["_at_end"] = bool(mk.get("at_end"))
            t["_hold"] = m92._ord(mk["resolve_date"] or p["entry_date"]) \
                - m92._ord(p["entry_date"])
            ev.append(t)
    return ev, miss


def make_roef(fq):
    def f(code, day, funddb):
        rec = funddb.get(code)
        if not rec:
            return False
        art = rec.get("ART") or []
        k = m92.asof_idx(art, day) if art else -1
        if k < 0 or m92._ord(day) - m92._ord(art[k][0]) > m92.STALE_MAX:
            return False
        v = art[k][m92.IX["roe"]]
        return (not m92._nan(v)) and fq(v) == 0
    return f


def quintile_fn(ev):
    """5분위 «경계»는 고르기 창에서만(관문 ②)."""
    xs = sorted(t["_logcap"] for t in ev)
    cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
    return cuts, (lambda v: bisect.bisect_right(cuts, v))


def run(ev, order_fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            order_fn=order_fn) for s in range(n_seed)]


def prio_for(q):
    def f(seed, t):
        return (0 if t["_q"] == q else 1, order_key(seed, t))
    return f


def report_arm(lab, ctl, trt, n_seed):
    ce = [x["equity_pct"] for x in ctl]
    te = [x["equity_pct"] for x in trt]
    dif = sorted(t - c for t, c in zip(te, ce))
    win = 100.0 * sum(1 for d in dif if d > 0) / n_seed
    med = st.median(dif)
    p25 = dif[int(n_seed * .25)]
    ptc = st.median(x["filled_per_trade"] for x in ctl)
    ptt = st.median(x["filled_per_trade"] for x in trt)
    sd = st.pstdev(dif)
    mde = 2.8 * sd / math.sqrt(n_seed)
    okA, okB, okC = win > A_PASS, (med > 0 and p25 > 0), ptt > ptc
    print("   %-8s 자산 대조 %+9.2f%% → 처리 %+9.2f%%  ·  짝차 중앙 %+8.2f%%p · 하위25%% %+8.2f%%p"
          % (lab, st.median(ce), st.median(te), med, p25), flush=True)
    print("            A★ 이기는 판 **%.1f%%**(문턱 60) %s · B★ %s · C★ 거래당 %+.4f→%+.4f %s"
          % (win, "✅" if okA else "❌", "✅" if okB else "❌", ptc, ptt,
             "✅" if okC else "❌"), flush=True)
    print("            D  MDE %.2f%%p · 체결 %.0f→%.0f · 보유평균 %.1f→%.1f일 · MDD %.1f→%.1f%%"
          % (mde, st.median(x["n_filled"] for x in ctl), st.median(x["n_filled"] for x in trt),
             st.median(x["_hold_mean"] for x in ctl) if "_hold_mean" in ctl[0] else float("nan"),
             st.median(x["_hold_mean"] for x in trt) if "_hold_mean" in trt[0] else float("nan"),
             st.median(x["mdd_pct"] for x in ctl), st.median(x["mdd_pct"] for x in trt)),
          flush=True)
    return {"win": win, "med": med, "p25": p25, "A": okA, "B": okB, "C": okC,
            "mde": mde, "eq_c": st.median(ce), "eq_t": st.median(te),
            "pt_c": ptc, "pt_t": ptt}


def attach_hold(res, hold):
    for r in res:
        ks = [k for k, kind, *_ in r["fill_log"] if kind == "pilot"]
        hs = [hold[k] for k in ks if k in hold]
        r["_hold_mean"] = st.mean(hs) if hs else float("nan")


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    n_sel = 12 if quick else N_SEL
    print("=" * 108, flush=True)
    print("95 — 「작은 회사라서 크게 오른다」가 «돈»이 되는가 · 사전등록 tasks/95", flush=True)
    print("=" * 108, flush=True)
    print("🚨 문턱은 «실현 수익»에만. MFE 는 서술만. · 🚨 신선한 표본 밖 «없음»(§1)", flush=True)
    print("🚨 예상(값 보기 «전»에 등록): MFE 는 오르고 **실현 수익은 못 가릴 것**."
          " 단 94 보다 자신 없다.\n", flush=True)

    capdb = json.loads(CAP.read_text(encoding="utf-8"))
    funddb = json.loads(m92.FUND.read_text(encoding="utf-8"))["by"]
    rowsP, _a, _b = m92.build(tuple(range(1999, 2013)), *m92.PICK, funddb)
    _c, _n, fq_roe = m92.cells_for(rowsP, "roe")
    roef = make_roef(fq_roe)

    packs = {}
    for lab, (d0, d1), yrs in (("고르기", PICK, range(1999, 2013)),
                               ("판정①", TEST1, range(2012, 2018)),
                               ("판정②", TEST2, range(2017, 2027))):
        ev, miss = build(tuple(yrs), d0, d1, capdb, funddb, roef)
        packs[lab] = ev
        print("  %-6s 거래 %s   (제외: %s)"
              % (lab, "{:,}".format(len(ev)),
                 " · ".join("%s %s" % (k, "{:,}".format(v)) for k, v in miss.most_common())),
              flush=True)

    cuts, fq = quintile_fn(packs["고르기"])
    print("\n관문 ② 5분위 «경계»는 고르기 창에서만 — 시총(백만$): %s"
          % " · ".join("%.0f" % (math.exp(c) / 1e6) for c in cuts), flush=True)
    for lab, ev in packs.items():
        for t in ev:
            t["_q"] = fq(t["_logcap"])

    # ── 서술: 분위별 시총·유동성부담·MFE·roe겹침 (관문 ④⑤ · 판정에 안 씀) ──
    print("\n[서술] 분위별 — 판정에 «안» 쓴다", flush=True)
    print("   %-6s %-4s %8s %14s %12s %10s %10s"
          % ("창", "분위", "n", "시총중앙(백만$)", "포지션÷ADV20", "MFE≥20%", "roe1분위 겹침"),
          flush=True)
    # 🚨 포지션은 원화(계좌 1,000만원 × 20%)이고 ADV 는 «달러»다. 환산 방향을 틀리면
    #    1,690배가 어긋난다([[us-control-study]] 의 G2 가 잡았던 바로 그 자리).
    POS_KRW = 0.20 * 1e7          # 계좌 1,000만원 기준 한 종목 금액(원)
    USD_KRW = 1300.0
    for lab, ev in packs.items():
        for q in range(NQ):
            g = [t for t in ev if t["_q"] == q]
            if not g:
                continue
            advs = [t["_adv"] for t in g if t["_adv"]]
            pos_usd = POS_KRW / USD_KRW          # ≈ $1,538
            burden = (st.median(pos_usd / a for a in advs) if advs else float("nan"))
            print("   %-6s %-4d %8s %14s %11.3f%% %9.1f%% %9.1f%%"
                  % (lab, q + 1, "{:,}".format(len(g)),
                     "{:,.0f}".format(st.median(t["_cap"] for t in g)), 100 * burden,
                     100 * st.mean(1.0 if t["_mfe"] >= 20 else 0.0 for t in g),
                     100 * st.mean(1.0 if t["_roe1"] else 0.0 for t in g)), flush=True)
        print("", flush=True)

    # ── 고르기 창에서 «실현 수익»이 가장 좋은 분위를 고른다 ──────────────
    print("[고르기] 실현 수익으로 분위를 고른다 (seed %d · «판정»이 아니라 «고르기»)" % n_sel,
          flush=True)
    evP = packs["고르기"]
    holdP = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_hold"] for t in evP}
    ctlP = run(evP, None, n_sel)
    attach_hold(ctlP, holdP)
    best, bestv = None, -1e18
    for q in range(NQ):
        trtP = run(evP, prio_for(q), n_sel)
        attach_hold(trtP, holdP)
        r = report_arm("%d분위" % (q + 1), ctlP, trtP, n_sel)
        if r["med"] > bestv:
            bestv, best = r["med"], q
    print("\n   -> **고른 분위: %d분위** (짝차 중앙 %+.2f%%p)" % (best + 1, bestv), flush=True)
    print("   ★ 사용자 가설이 옳다면 «낮은» 분위여야 한다. %s"
          % ("**가설과 같은 방향**" if best <= 1 else
             ("중간" if best == 2 else "🚨 **가설과 «반대» 방향 — 그 자리에서 반증**")), flush=True)

    # ── 판정 두 창 ──────────────────────────────────────────────────────
    print("\n" + "=" * 108, flush=True)
    print("[판정] %d분위를 우선 담는다 · seed %d · **두 창 «모두»** 넘어야 통과"
          % (best + 1, n_seed), flush=True)
    out = {}
    for lab in ("판정①", "판정②"):
        ev = packs[lab]
        hold = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_hold"] for t in ev}
        c = run(ev, None, n_seed)
        t_ = run(ev, prio_for(best), n_seed)
        attach_hold(c, hold)
        attach_hold(t_, hold)
        ae_c = st.median(_ae(x, ev) for x in c)
        ae_t = st.median(_ae(x, ev) for x in t_)
        out[lab] = report_arm(lab, c, t_, n_seed)
        print("            관문④ at_end 대조 %.2f%% → 처리 %.2f%% (차 %+.2f%%p)"
              % (ae_c, ae_t, ae_t - ae_c), flush=True)
        print("", flush=True)

    okA = all(out[l]["A"] for l in out)
    okB = all(out[l]["B"] for l in out)
    print("=" * 108, flush=True)
    print("**판정: A★ %s · B★ %s (둘 다 · 두 창 모두) → %s**"
          % ("통과" if okA else "미통과", "통과" if okB else "미통과",
             "★ 통과" if (okA and okB) else "미통과"), flush=True)
    (r91.OUT / "95-marketcap.json").write_text(
        json.dumps({"best_q": best + 1, "cuts_musd": [math.exp(c) / 1e6 for c in cuts],
                    "windows": out, "n_seed": n_seed, "pass": bool(okA and okB)},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("저장: 95-marketcap.json", flush=True)
    return 0


def _ae(res, ev):
    endm = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_at_end"] for t in ev}
    ks = [k for k, kind, *_ in res["fill_log"] if kind == "pilot"]
    if not ks:
        return float("nan")
    return 100.0 * sum(1 for k in ks if endm.get(k)) / len(ks)


if __name__ == "__main__":
    raise SystemExit(main())
