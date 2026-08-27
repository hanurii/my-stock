# -*- coding: utf-8 -*-
"""91 — **표본 밖 18.4년**. 사전등록 `tasks/91-us-out-of-sample.md`.

🚨🚨 **아무것도 안 고친다.** 파라미터는 81번 정본 그대로이고, 이 창은 «한 번만» 쓴다.
🚨 74번과 «같은 부품»을 쓴다(경로단계 필터 · `resolve_trade` · `sim_lots`).
   달라지는 것은 **연도 범위**와 **월말 패널(전체이력판)** 둘뿐이다.

실행:
  PYTHONIOENCODING=utf-8 python research/handoff/scripts/91-us-out-of-sample.py [--quick]
"""
from __future__ import annotations

import datetime as _dt
import importlib.util as _u
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402


def _load(name, path):
    s = _u.spec_from_file_location(name, HERE / path)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r61b = _load("r61b", "61b-matched-null.py")
r41, r61 = r61b.r41, r61b.r61

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"

# ── 81번 정본 파라미터 — **한 글자도 안 바꾼다** ──────────────────────────
COST = (0.0, 0.002)
RISK, CAP, SLOTS = 0.02, 0.20, 5
STOP, TARGET = 8.0, 20.0
LO, HI = 0.10, 0.30
N_SEED = 200

# ── 창 (사전등록 §1) ──────────────────────────────────────────────────────
WINDOWS = (
    ("표본밖A정본", tuple(range(2002, 2018)), "2002-01-01", "2017-08-31"),
    ("표본밖B닷컴", (1999, 2000, 2001), "1999-04-01", "2001-12-31"),
    ("이미본구간대조", tuple(range(2017, 2027)), "2017-09-06", "2026-08-21"),
)


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def cagr(total_pct, years):
    if years <= 0:
        return float("nan")
    base = 1 + total_pct / 100.0
    if base <= 0:
        return float("nan")
    return (base ** (1 / years) - 1) * 100


# ═════════════════════════════════════════════════════════════════════════
# 1. 경로 적재 + 사다리 세 칸
# ═════════════════════════════════════════════════════════════════════════
def load_ladder(years, d0, d1, monthly_file):
    """사다리 0 / ① / ② 를 **경로 단계**에서 만든다 (74 §1 과 같은 규약).

    🚨 진입 «뒤»에 거르면 안 산 종목이 `open_until` 을 잡아 나중 진입을 막는다.
    """
    pack = json.loads((OUT / monthly_file).read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    lo_ym = r61.prev_ym(d0[:7], 8)                # 6개월 수익률 + 여유
    months = sorted({m for d in monthly.values() for m in d if m >= lo_ym})
    mret = r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r61b.make_flags(mret, sector)

    by0, missing = {}, []
    for y in years:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            missing.append(y)
            continue
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        by0[y] = [p for p in ps if d0 <= p["entry_date"] <= d1]

    def lvl1(p):
        s = sector.get(p["code"])
        if not s:
            return True                                # 제3군 통과 (61번 규약)
        top = sec_top.get(r61.prev_ym(p["scan_date"][:7], 1))
        return True if top is None else (s in top)

    def lvl2(p):
        if not lvl1(p):
            return False
        s = sector.get(p["code"])
        if not s:
            return True
        ym = r61.prev_ym(p["scan_date"][:7], 1)
        if sec_top.get(ym) is None:
            return True
        v = in_pct.get(ym, {}).get(p["code"])
        return (v is None) or (LO <= v < HI)

    by1 = {y: [p for p in ps if lvl1(p)] for y, ps in by0.items()}
    by2 = {y: [p for p in ps if lvl2(p)] for y, ps in by0.items()}
    return (by0, by1, by2), missing


def replay(by):
    """74 §replay_masks 의 «한 번에 사기»(shares=(1.0,)) 판."""
    ev, blocked, trunc = [], 0, 0
    allT = ()
    for y in sorted(by):
        open_until = {}
        for p in by[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP,
                                 target=TARGET, shares=(1.0,), add_stop="floor_entry")
            m = t["masks"][allT]
            if m.get("truncated"):
                trunc += 1
            open_until[c] = m["resolve_date"] or p["entry_date"]
            ev.append(t)
    return ev, blocked, trunc


def sim(ev, n_seed):
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot") for s in range(n_seed)]


# ═════════════════════════════════════════════════════════════════════════
# 2. 벤치마크
# ═════════════════════════════════════════════════════════════════════════
_BM = None


def bench(tk, d0, d1):
    global _BM
    if _BM is None:
        _BM = json.loads((OUT / "91-benchmarks.json").read_text(encoding="utf-8"))
    if tk not in _BM:
        return None
    ser = _BM[tk]["series"]
    ds = sorted(d for d in ser if d0 <= d <= d1)
    if len(ds) < 2:
        return None
    v = [ser[d][0] for d in ds]
    tot = v[-1] / v[0] - 1.0
    yrs = (_ord(ds[-1]) - _ord(ds[0])) / 365.25
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)
    return {"total": tot * 100, "years": yrs, "cagr": cagr(tot * 100, yrs),
            "mdd": mdd * 100, "d0": ds[0], "d1": ds[-1]}


# ═════════════════════════════════════════════════════════════════════════
# 3. 본실행
# ═════════════════════════════════════════════════════════════════════════
def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    only = [a for a in sys.argv[1:] if not a.startswith("--")]

    print("=" * 104, flush=True)
    print("91 — 표본 밖 18.4년 · 사전등록 tasks/91 · **아무것도 안 고쳤다**", flush=True)
    print("=" * 104, flush=True)
    print("파라미터: 비용%s · %d칸 %.0f%% · 위험 %.0f%% · 손절 -%.0f%% / 익절 +%.0f%% 절반 -> 추격"
          % (COST, SLOTS, CAP * 100, RISK * 100, STOP, TARGET), flush=True)
    print("seed %d · 등급 [%.2f, %.2f)\n" % (n_seed, LO, HI), flush=True)

    allres = {}
    for lab, years, d0, d1 in WINDOWS:
        if only and not any(o in lab for o in only):
            continue
        mf = "61-monthly-us.json" if "이미본" in lab else "91-monthly-us-full.json"
        (by0, by1, by2), missing = load_ladder(years, d0, d1, mf)
        if missing:
            print("🚨 %s — 경로 파일 없음: %s  **건너뛴다**\n" % (lab, missing), flush=True)
            continue
        print("-" * 104, flush=True)
        print("### %s   %s ~ %s   (월말패널 %s)" % (lab, d0, d1, mf), flush=True)
        rows = []
        for name, by in (("0 선별없이", by0), ("1 +주도3업종", by1), ("2 +2·3등급", by2)):
            ev, blk, trunc = replay(by)
            n_in = sum(len(v) for v in by.values())
            rs = sim(ev, n_seed)
            eq = sorted(x["equity_pct"] for x in rs)
            dates = [p["entry_date"] for v in by.values() for p in v]
            yrs = (_ord(d1) - _ord(d0)) / 365.25
            med = st.median(eq)
            rows.append({
                "name": name, "n_path": n_in, "n_entry": len(ev), "blocked": blk,
                "trunc": trunc, "years": yrs, "med": med, "cagr": cagr(med, yrs),
                "p25": eq[int(n_seed * .25)], "p5": eq[int(n_seed * .05)],
                "mdd": st.median(x["mdd_pct"] for x in rs),
                "win": st.median(x["win_rate"] for x in rs),
                "per_trade": st.median(x["filled_per_trade"] for x in rs),
                "n_filled": st.median(x["n_filled"] for x in rs),
                "first": min(dates) if dates else "-", "last": max(dates) if dates else "-",
                "eq": eq})
        print("  %-13s %8s %7s %6s %12s %10s %12s %12s %8s %7s %8s"
              % ("사다리", "경로", "진입", "체결", "자산중앙", "**연환산**",
                 "하위25%", "운나쁠때5%", "MDD", "승률", "거래당"), flush=True)
        print("  " + "-" * 108, flush=True)
        for r in rows:
            print("  %-13s %8d %7d %6d %+11.2f%% %+9.2f%% %+11.2f%% %+11.2f%% %7.1f%% %6.1f%% %+7.3f%%"
                  % (r["name"], r["n_path"], r["n_entry"], r["n_filled"], r["med"],
                     r["cagr"], r["p25"], r["p5"], r["mdd"], r["win"], r["per_trade"]),
                  flush=True)
        print("     경로 잘림(250봉 상한): %s"
              % " · ".join("%s %d" % (r["name"][:1], r["trunc"]) for r in rows), flush=True)
        print("     open_until 로 막힘:    %s"
              % " · ".join("%s %d" % (r["name"][:1], r["blocked"]) for r in rows), flush=True)
        print("     진입 첫날~끝날:        %s ~ %s (%.2f년)"
              % (rows[0]["first"], rows[0]["last"], rows[0]["years"]), flush=True)

        print("\n  지수 (같은 창 · 배당 재투자 = **지수에 유리한 자**)", flush=True)
        bm = {}
        for tk in ("SPY", "QQQ"):
            b = bench(tk, d0, d1)
            bm[tk] = b
            if b:
                print("     %-4s %+11.2f%% · 연 %+7.2f%% · MDD %7.2f%% · 수익/낙폭 %5.2f  (%s~%s)"
                      % (tk, b["total"], b["cagr"], b["mdd"],
                         abs(b["total"] / b["mdd"]) if b["mdd"] else float("nan"),
                         b["d0"], b["d1"]), flush=True)
        allres[lab] = {"rows": rows, "bm": bm, "d0": d0, "d1": d1}

        if "대조" in lab:
            print("", flush=True)
            continue
        r0, r1, r2 = rows[0], rows[1], rows[2]
        sp = bm.get("SPY")
        print("\n  §3 합격선 — 값 보기 «전»에 적힌 것", flush=True)
        a = sp is not None and r2["cagr"] > sp["cagr"]
        print("   A★ 조합 연환산 > S&P500          %+.2f%% vs %+.2f%%        -> **%s**"
              % (r2["cagr"], sp["cagr"] if sp else float("nan"),
                 "통과" if a else "미통과"), flush=True)
        bmed = r2["cagr"] - sp["cagr"] if sp else float("nan")
        b25 = cagr(r2["p25"], r2["years"]) - sp["cagr"] if sp else float("nan")
        okb = (bmed > 0) and (b25 > 0)
        print("   B★ seed 축이 부호를 안 뒤집는다   중앙 %+.2f%%p · 하위25%% %+.2f%%p -> **%s**"
              % (bmed, b25, "통과" if okb else "미통과"), flush=True)
        mar = abs(r2["med"] / r2["mdd"]) if r2["mdd"] else float("nan")
        marb = abs(sp["total"] / sp["mdd"]) if sp and sp["mdd"] else float("nan")
        okc = mar > marb
        print("   C★ 수익/낙폭 > S&P500            %.2f vs %.2f                -> **%s**"
              % (mar, marb, "통과" if okc else "미통과"), flush=True)
        okd = r0["cagr"] < r1["cagr"] < r2["cagr"]
        print("   D★ 사다리 «순서» 0 < 1 < 2       %+.2f < %+.2f < %+.2f       -> **%s**"
              % (r0["cagr"], r1["cagr"], r2["cagr"], "통과" if okd else "미통과"), flush=True)
        sd = st.pstdev([cagr(x, r2["years"]) for x in r2["eq"]])
        mde = 2.8 * sd / math.sqrt(n_seed)
        print("   E  MDE(연환산·단일비교) = 2.8·sd/√n = %.3f%%p" % mde, flush=True)
        print("      seed 축 표준편차 %.3f%%p · 관측 초과분 %+.3f%%p -> %s"
              % (sd, bmed, "가릴 수 있는 크기" if abs(bmed) > mde else "🚨 못 가림"),
              flush=True)
        print("      🚨 이 MDE 는 «seed 축»만이다. 자료 축(국면)은 훨씬 크다.", flush=True)
        print("", flush=True)

    (OUT / "91-out-of-sample.json").write_text(
        json.dumps({k: {"rows": [{kk: vv for kk, vv in r.items() if kk != "eq"}
                                 for r in v["rows"]],
                        "bm": v["bm"], "d0": v["d0"], "d1": v["d1"]}
                    for k, v in allres.items()}, ensure_ascii=False,
                   separators=(",", ":")), encoding="utf-8")
    print("저장: 91-out-of-sample.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
