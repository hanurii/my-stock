# -*- coding: utf-8 -*-
r"""94 — **「높이 갔다」가 «벌었다»로 바뀌는가.** 사전등록 `tasks/94-roe-realized.md`.

🚨 **방향을 «먼저» 적어 두었다**(사전등록 §1):
   85 선례 — `atr_band ④` 는 더블 3.7배인데 **거래당 +1.184% = 전체 꼴찌**.
   → **예상: `roe 1분위` 도 MFE 는 높지만 실현 수익은 «비슷하거나 낮을» 것.**
   예상대로면 「92 는 참이나 매매 규칙으로는 못 쓴다」 · **반대면 그게 «진짜 놀라움»**.

설계: **필터가 아니라 «우선순위»** — 같은 날 후보가 여럿이면 `roe 1분위` 를 먼저 담는다.
      필터는 진입을 1/5 로 줄여 **노출이 달라진다**(86 에서 겪음). 우선순위는 «선택»만 바꾼다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/94-roe-realized.py [--quick]
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
from slot_sim import order_key                                 # noqa: E402

_s = _u.spec_from_file_location("m92", HERE / "92-us-fundamentals.py")
m92 = _u.module_from_spec(_s)
_s.loader.exec_module(m92)
r91 = m92.r91
r41 = r91.r41

D0, D1 = "2012-01-01", "2026-08-21"
YEARS = tuple(range(2012, 2027))
N_SEED = 200
A_PASS = 60.0            # A★ 짝비교 이기는 판 비율 문턱 (우연 50%)
AT_END_GAP = 2.0         # 관문 ④ — 처리의 at_end 가 대조보다 이만큼 높으면 «그대로 못 읽는다»


def build_events(fund, cuts_f, want):
    """91·74 와 «같은» 규약으로 거래를 만들고 `roe 1분위` 딱지를 붙인다."""
    ev, tagged, miss = [], 0, {"실적없음": 0, "묶음": 0}
    for y in YEARS:
        f = m92.SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        ps = [p for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
              if D0 <= p["entry_date"] <= D1]
        open_until = {}
        for p in ps:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                miss["묶음"] += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                                 target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
            mk = t["masks"][()]
            open_until[c] = mk["resolve_date"] or p["entry_date"]

            # ── `roe 1분위` 인가 — 92 의 «고르기 창 경계»를 그대로 쓴다(관문 ①) ──
            flag = False
            rec = fund.get(c)
            if rec:
                arq = rec["ARQ"]
                j = m92.asof_idx(arq, p["entry_date"])
                art = rec.get("ART") or []
                k = m92.asof_idx(art, p["entry_date"]) if art else -1
                if j >= 5 and m92._ord(p["entry_date"]) - m92._ord(arq[j][0]) <= m92.STALE_MAX \
                        and k >= 0 \
                        and m92._ord(p["entry_date"]) - m92._ord(art[k][0]) <= m92.STALE_MAX:
                    v = art[k][m92.IX["roe"]]
                    if not m92._nan(v):
                        flag = (cuts_f(v) == want)
            else:
                miss["실적없음"] += 1
            t["_roe1"] = flag
            t["_at_end"] = bool(mk.get("at_end"))
            tagged += flag
            ev.append(t)
    return ev, tagged, miss


def prio(seed, t):
    """처리 — `roe 1분위` 를 먼저, 그 «안»에서는 대조와 «같은» 난수."""
    return (0 if t["_roe1"] else 1, order_key(seed, t))


def run(ev, order_fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            order_fn=order_fn) for s in range(n_seed)]


def at_end_rate(res, tag, endm):
    """체결된 거래 중 «경로 끝 정산» 비율 — 관문 ④."""
    keys = [k for k, kind, *_ in res["fill_log"] if kind == "pilot"]
    if not keys:
        return float("nan"), float("nan"), 0
    n1 = sum(1 for k in keys if tag.get(k))
    ae = sum(1 for k in keys if endm.get(k))
    return 100.0 * ae / len(keys), 100.0 * n1 / len(keys), len(keys)


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    print("=" * 104, flush=True)
    print("94 — 「높이 갔다」가 «벌었다»로 바뀌는가 · 사전등록 tasks/94", flush=True)
    print("=" * 104, flush=True)
    print("🚨 예상(값 보기 «전»에 등록): **안 될 것이다** — 85 의 atr_band ④ 가 그랬다"
          "(더블 3.7배 · 거래당 꼴찌)\n", flush=True)

    fund = json.loads(m92.FUND.read_text(encoding="utf-8"))["by"]
    # 관문 ① — 분위 «경계»는 92 의 고르기 창(1999~2011)에서. 판정 자료로 다시 안 만든다.
    rowsP, _mi, _np = m92.build(tuple(range(1999, 2013)), *m92.PICK, fund)
    cuts, nc, fq = m92.cells_for(rowsP, "roe")
    print("관문 ① 분위 경계는 «고르기 창»의 것: %s"
          % " · ".join("%.4f" % c for c in cuts), flush=True)

    ev, tagged, miss = build_events(fund, fq, 0)
    print("판정 창 %s ~ %s · 거래 %s · 그중 **roe 1분위 %s (%.1f%%)**"
          % (D0, D1, "{:,}".format(len(ev)), "{:,}".format(tagged),
             100.0 * tagged / len(ev)), flush=True)
    print("   (같은 종목 겹침으로 뺀 것 %s · 실적표에 없는 종목 %s)"
          % ("{:,}".format(miss["묶음"]), "{:,}".format(miss["실적없음"])), flush=True)

    tag = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_roe1"] for t in ev}
    endm = {(t["scan_date"], t["code"], t.get("pattern", "")): t["_at_end"] for t in ev}

    print("\n돌리는 중 (seed %d × 2) …" % n_seed, flush=True)
    ctl = run(ev, None, n_seed)
    trt = run(ev, prio, n_seed)

    ce = [x["equity_pct"] for x in ctl]
    te = [x["equity_pct"] for x in trt]
    dif = [t - c for t, c in zip(te, ce)]

    # ── 관문 ③ 노출 ────────────────────────────────────────────────────
    print("\n관문 ③ 노출이 안 바뀌는가 (처리 vs 대조 · 중앙)", flush=True)
    for k, nm in (("n_filled", "체결 수"), ("expo_mean", "평균 노출%"),
                  ("conc_median", "동시보유 중앙")):
        a, b = st.median(x[k] for x in trt), st.median(x[k] for x in ctl)
        print("   %-14s 처리 %10.2f · 대조 %10.2f · 차 %+.2f"
              % (nm, a, b, a - b), flush=True)

    # ── 관문 ④ 상폐 ────────────────────────────────────────────────────
    print("\n관문 ④ 상폐 — 체결된 거래 중 «경로 끝 정산(at_end)» 비율", flush=True)
    ae_t = st.median(at_end_rate(x, tag, endm)[0] for x in trt)
    ae_c = st.median(at_end_rate(x, tag, endm)[0] for x in ctl)
    r1_t = st.median(at_end_rate(x, tag, endm)[1] for x in trt)
    r1_c = st.median(at_end_rate(x, tag, endm)[1] for x in ctl)
    print("   at_end     처리 %.2f%% · 대조 %.2f%% · 차 **%+.2f%%p** (문턱 +%.1f%%p)"
          % (ae_t, ae_c, ae_t - ae_c, AT_END_GAP), flush=True)
    print("   체결 중 roe1분위 비율  처리 %.1f%% · 대조 %.1f%%  ← 우선순위가 «실제로» 먹었는가"
          % (r1_t, r1_c), flush=True)
    gate4 = (ae_t - ae_c) <= AT_END_GAP
    print("   -> **%s**" % ("통과" if gate4 else "🚨 미통과 — 결과를 «그대로 못 읽는다»"), flush=True)

    # ── D · MDE 를 «먼저» ──────────────────────────────────────────────
    sd = st.pstdev(dif)
    mde = 2.8 * sd / math.sqrt(n_seed)
    print("\n   D  MDE(짝차의 «평균» 기준) = 2.8·sd/√n = %.3f%%p · 짝차 sd %.2f%%p"
          % (mde, sd), flush=True)

    # ── §4 합격선 ──────────────────────────────────────────────────────
    win = 100.0 * sum(1 for d in dif if d > 0) / n_seed
    ds = sorted(dif)
    med_c, med_t = st.median(ce), st.median(te)
    print("\n" + "─" * 104, flush=True)
    print("§4 합격선 — 값 보기 «전»에 적힌 것", flush=True)
    print("   자산 중앙   대조 %+.2f%% → 처리 %+.2f%%  (차 %+.2f%%p)"
          % (med_c, med_t, med_t - med_c), flush=True)
    okA = win > A_PASS
    print("   A★ 짝비교 이기는 판 **%.1f%%** (우연 50%% · 문턱 %.0f%%) -> **%s**"
          % (win, A_PASS, "통과" if okA else "미통과"), flush=True)
    p25 = ds[int(n_seed * .25)]
    okB = (st.median(dif) > 0) and (p25 > 0)
    print("   B★ 짝차 중앙 %+.2f%%p · 하위25%% %+.2f%%p · 하위5%% %+.2f%%p -> **%s**"
          % (st.median(dif), p25, ds[int(n_seed * .05)], "통과" if okB else "미통과"), flush=True)
    pt_t = st.median(x["filled_per_trade"] for x in trt)
    pt_c = st.median(x["filled_per_trade"] for x in ctl)
    okC = pt_t > pt_c
    print("   C★ 거래당 순수익  처리 %+.4f%% · 대조 %+.4f%% · 차 **%+.4f%%p** -> **%s**"
          % (pt_t, pt_c, pt_t - pt_c, "통과" if okC else "미통과"), flush=True)
    print("      (기전 — 꼬리를 넓혔나 기대값을 올렸나. 승률 처리 %.1f%% · 대조 %.1f%% · MDD %.1f / %.1f)"
          % (st.median(x["win_rate"] for x in trt), st.median(x["win_rate"] for x in ctl),
             st.median(x["mdd_pct"] for x in trt), st.median(x["mdd_pct"] for x in ctl)),
          flush=True)

    print("\n   **판정: A★ %s · B★ %s (둘 다 넘어야 통과) · C★ %s · 관문④ %s**"
          % tuple("통과" if x else "미통과" for x in (okA, okB, okC, gate4)), flush=True)
    verdict = okA and okB and gate4
    print("   => **%s**" % ("★ 통과 — 「높이 갔다」가 «벌었다»로 바뀐다"
                            if verdict else
                            "미통과 — 등록한 예상대로다. 92 는 참이나 매매 규칙으론 못 쓴다"),
          flush=True)

    (r91.OUT / "94-roe-realized.json").write_text(json.dumps(
        {"n_seed": n_seed, "n_ev": len(ev), "tagged": tagged,
         "win_pct": win, "dif_med": st.median(dif), "dif_p25": p25,
         "eq_ctl": med_c, "eq_trt": med_t, "pt_ctl": pt_c, "pt_trt": pt_t,
         "at_end_ctl": ae_c, "at_end_trt": ae_t, "mde": mde,
         "verdict": {"A": okA, "B": okB, "C": okC, "gate4": gate4, "pass": verdict}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 94-roe-realized.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
