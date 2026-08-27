# -*- coding: utf-8 -*-
"""91 — **표본 밖 18.4년**. 사전등록 `tasks/91-us-out-of-sample.md` (**개정 1** 포함).

🚨🚨 **아무것도 안 고친다.** 파라미터는 81번 정본 그대로이고, 이 창은 «한 번만» 쓴다.
🚨 74번과 «같은 부품»을 쓴다(경로단계 필터 · `resolve_trade` · `sim_lots`).
   달라지는 것은 **연도 범위**와 **월말 패널(전체이력판)** 둘뿐이다.

개정 1 (검증 세션 `35f2aaa4`) — 값 보기 «전»에 들어갔다
------------------------------------------------------
① **D★** = 「한 판의 순서」가 아니라 **「200판 중 0<①<② 인 비율」**. 우연 16.7% · 통과선 50%.
② **ext 미사용이 91 의 규약**. 1999~2016 엔 ext 가 없으므로 그것만이 «대칭»이다.
   `--ext` 를 주면 쓰는데, 그건 **관문 ②a(코드 검증)** 전용이다.
③ **관문 ②** 에 숫자 문턱 — ②a(ext 사용·200판) 의 중앙 95% 구간이 74번 +298.44% 를 품는가.
   ②b(ext 미사용) 와의 차 = **ext 227건의 효과**(새로 재는 값).

실행:
  PYTHONIOENCODING=utf-8 python research/handoff/scripts/91-us-out-of-sample.py [창이름…] [--quick] [--ext]
"""
from __future__ import annotations

import datetime as _dt
import importlib.util as _u
import json
import math
import random
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

CANON_74 = 298.44          # 74번 정본 (ext 사용 · 200판)
D_CHANCE = 100.0 / 6.0     # 사다리 세 칸의 순서가 우연히 맞을 확률
D_PASS = 50.0              # 개정 1-① 통과선

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


def boot_ci(vals, b=4000, seed=0, lo=2.5, hi=97.5):
    """중앙값의 부트스트랩 구간. 🚨 난수는 «고정»한다(재현)."""
    rnd = random.Random(seed)
    n = len(vals)
    meds = []
    for _ in range(b):
        meds.append(st.median(vals[rnd.randrange(n)] for _ in range(n)))
    meds.sort()
    return meds[int(b * lo / 100)], meds[int(b * hi / 100)]


# ═════════════════════════════════════════════════════════════════════════
# 1. 경로 적재 + 사다리 세 칸
# ═════════════════════════════════════════════════════════════════════════
def load_ladder(years, d0, d1, monthly_file, use_ext=False):
    """사다리 0 / ① / ② 를 **경로 단계**에서 만든다 (74 §1 과 같은 규약).

    🚨 진입 «뒤»에 거르면 안 산 종목이 `open_until` 을 잡아 나중 진입을 막는다.
    🚨 `use_ext` 는 **관문 ②a 전용**이다 — 표본 밖엔 ext 파일이 없다(개정 1-②).
    """
    pack = json.loads((OUT / monthly_file).read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    lo_ym = r61.prev_ym(d0[:7], 8)                # 6개월 수익률 + 여유
    months = sorted({m for d in monthly.values() for m in d if m >= lo_ym})
    mret = r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r61b.make_flags(mret, sector)

    ext_idx, n_ext = (pt._load_ext() if use_ext else ({}, 0))
    by0, missing = {}, []
    for y in years:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            missing.append(y)
            continue
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        if ext_idx:
            for i, p in enumerate(ps):
                q = ext_idx.get((p["scan_date"], p["code"], p["pattern"]))
                if q is not None:
                    ps[i] = q
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
    return (by0, by1, by2), missing, n_ext


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
# 3. 한 창 돌리기
# ═════════════════════════════════════════════════════════════════════════
def run_window(lab, years, d0, d1, n_seed, use_ext):
    mf = "61-monthly-us.json" if "이미본" in lab else "91-monthly-us-full.json"
    (by0, by1, by2), missing, n_ext = load_ladder(years, d0, d1, mf, use_ext)
    if missing:
        print("🚨 %s — 경로 파일 없음: %s  **건너뛴다**\n" % (lab, missing), flush=True)
        return None
    yrs = (_ord(d1) - _ord(d0)) / 365.25
    print("-" * 106, flush=True)
    print("### %s   %s ~ %s   (%.2f년 · 월말패널 %s · ext %s)"
          % (lab, d0, d1, yrs, mf, ("사용 %d개" % n_ext) if use_ext else "**미사용**"),
          flush=True)
    rows = []
    for name, by in (("0 선별없이", by0), ("1 +주도3업종", by1), ("2 +2·3등급", by2)):
        ev, blk, trunc = replay(by)
        rs = sim(ev, n_seed)
        raw = [x["equity_pct"] for x in rs]        # 🚨 seed 순서 «그대로» (D★ 짝맞춤용)
        eq = sorted(raw)
        dates = [p["entry_date"] for v in by.values() for p in v]
        med = st.median(eq)
        rows.append({
            "name": name, "n_path": sum(len(v) for v in by.values()),
            "n_entry": len(ev), "blocked": blk, "trunc": trunc, "years": yrs,
            "med": med, "cagr": cagr(med, yrs),
            "p25": eq[int(n_seed * .25)], "p5": eq[int(n_seed * .05)],
            "mdd": st.median(x["mdd_pct"] for x in rs),
            "win": st.median(x["win_rate"] for x in rs),
            "per_trade": st.median(x["filled_per_trade"] for x in rs),
            "n_filled": st.median(x["n_filled"] for x in rs),
            "first": min(dates) if dates else "-", "last": max(dates) if dates else "-",
            "raw": raw, "eq": eq,
            # 개정 2-㉡ — 판 «각각»의 수익/낙폭. 두 중앙값의 «비»는 비의 중앙값이 아니다.
            "raw_mdd": [x["mdd_pct"] for x in rs]})
    print("  %-13s %8s %7s %6s %12s %10s %12s %12s %8s %7s %8s"
          % ("사다리", "경로", "진입", "체결", "자산중앙", "**연환산**",
             "하위25%", "운나쁠때5%", "MDD", "승률", "거래당"), flush=True)
    print("  " + "-" * 108, flush=True)
    for r in rows:
        print("  %-13s %8d %7d %6d %+11.2f%% %+9.2f%% %+11.2f%% %+11.2f%% %7.1f%% %6.1f%% %+7.3f%%"
              % (r["name"], r["n_path"], r["n_entry"], r["n_filled"], r["med"],
                 r["cagr"], r["p25"], r["p5"], r["mdd"], r["win"], r["per_trade"]),
              flush=True)
    print("     경로 잘림(250봉 상한): %s   ·   open_until 로 막힘: %s"
          % (" ".join("%s%d" % (r["name"][:1], r["trunc"]) for r in rows),
             " ".join("%s%d" % (r["name"][:1], r["blocked"]) for r in rows)), flush=True)
    print("     진입 첫날~끝날: %s ~ %s" % (rows[0]["first"], rows[0]["last"]), flush=True)

    print("\n  지수 (같은 창 · **배당 재투자** = 우리에게 «불리한» 보수적 자)", flush=True)
    bm = {}
    for tk in ("SPY", "QQQ"):
        b = bench(tk, d0, d1)
        bm[tk] = b
        if b:
            print("     %-4s %+11.2f%% · 연 %+7.2f%% · MDD %7.2f%% · 수익/낙폭 %5.2f  (%s~%s · %.2f년)"
                  % (tk, b["total"], b["cagr"], b["mdd"],
                     abs(b["total"] / b["mdd"]) if b["mdd"] else float("nan"),
                     b["d0"], b["d1"], b["years"]), flush=True)
            # 🚨 개정 2-㉢ — 전략은 창의 «경계»로, 벤치마크는 자료가 «있는 날»로 연수를 잰다.
            #    지금은 며칠 차지만 덮개가 짧으면 «조용히» 어긋난다(1999 창에 계열이 2000부터면 1년).
            #    「괜찮을 것」을 검사되게 만든다.
            assert abs(b["years"] - yrs) < 0.05, \
                "🚨 연수가 어긋난다 — 전략 %.4f년 vs %s %.4f년 (%s~%s)" \
                % (yrs, tk, b["years"], b["d0"], b["d1"])
    print("     ✅ 연수 대조: 전략 %.2f년 = 지수 덮개 (assert |Δ|<0.05)" % yrs, flush=True)
    return {"rows": rows, "bm": bm, "d0": d0, "d1": d1, "years": yrs, "n_ext": n_ext}


def judge(res, n_seed):
    """§3 합격선 A★ B★ C★ D★ + E. **개정 1-① 반영.**"""
    rows, bm = res["rows"], res["bm"]
    r0, r1, r2 = rows
    sp = bm.get("SPY")
    print("\n  §3 합격선 — 값 보기 «전»에 적힌 것 (개정 1 포함)", flush=True)
    a = sp is not None and r2["cagr"] > sp["cagr"]
    print("   A★ 조합 연환산 > SPY(총수익)      %+.2f%% vs %+.2f%%        -> **%s**"
          % (r2["cagr"], sp["cagr"] if sp else float("nan"), "통과" if a else "미통과"),
          flush=True)
    bmed = r2["cagr"] - sp["cagr"] if sp else float("nan")
    b25 = cagr(r2["p25"], r2["years"]) - sp["cagr"] if sp else float("nan")
    okb = (bmed > 0) and (b25 > 0)
    print("   B★ seed 축이 부호를 안 뒤집는다   중앙 %+.2f%%p · 하위25%% %+.2f%%p -> **%s**"
          % (bmed, b25, "통과" if okb else "미통과"), flush=True)
    # 🚨 개정 2-㉡ — 이 자는 «중앙자산 ÷ 중앙MDD»다. 두 중앙값의 비는 «비의 중앙값이 아니다».
    #    등록 통계라 그대로 두되(81 의 14.42 와 이어져야 한다) **라벨을 붙이고**
    #    판 «각각»의 비를 중앙낸 값을 옆에 참고로 찍는다. 벤치마크는 경로가 하나라 정확하다.
    mar = abs(r2["med"] / r2["mdd"]) if r2["mdd"] else float("nan")
    marb = abs(sp["total"] / sp["mdd"]) if sp and sp["mdd"] else float("nan")
    okc = mar > marb
    mar_ps = st.median(abs(e / m) if m else float("nan")
                       for e, m in zip(r2["raw"], r2["raw_mdd"]))
    print("   C★ 수익/낙폭 > SPY               %.2f vs %.2f                -> **%s**"
          % (mar, marb, "통과" if okc else "미통과"), flush=True)
    print("      ⚠️ 위 값은 «중앙자산÷중앙MDD»(등록 통계). 판별 «비의 중앙값»은 %.2f — 다르면 자 탓이다."
          % mar_ps, flush=True)
    # ★ 개정 1-① — 판 «각각»에서 순서를 세고 비율을 적는다
    hit = sum(1 for s in range(n_seed)
              if r0["raw"][s] < r1["raw"][s] < r2["raw"][s])
    pct = 100.0 * hit / n_seed
    okd = pct > D_PASS
    print("   D★ 200판 중 0<1<2 인 «비율»       **%.1f%%** (%d/%d) · 우연이면 %.1f%% · 통과선 %.0f%% -> **%s**"
          % (pct, hit, n_seed, D_CHANCE, D_PASS, "통과" if okd else "미통과"), flush=True)
    print("      (참고 — 중앙값끼리의 순서: %+.2f / %+.2f / %+.2f)"
          % (r0["cagr"], r1["cagr"], r2["cagr"]), flush=True)
    # 🚨 개정 2-㉠ — `sd/√n` 은 **평균**의 표준오차인데 비교 대상 `bmed` 은 **중앙값**에서 나온다.
    #    정규 근사에서 중앙값의 SE 는 1.253배 크므로 옛 식은 **20% 낙관**이었다.
    #    `boot_ci` 가 이미 있으니 그 폭에서 직접 SE 를 뽑는다 — 정규 가정도 필요 없고 자가 하나다.
    lo_e, hi_e = boot_ci(r2["raw"])
    se_med = (cagr(hi_e, r2["years"]) - cagr(lo_e, r2["years"])) / 3.92
    mde = 2.8 * se_med
    sd = st.pstdev([cagr(x, r2["years"]) for x in r2["eq"]])
    old_mde = 2.8 * sd / math.sqrt(n_seed)
    print("   E  MDE(연환산·단일비교) = 2.8 × SE(**중앙값**) = %.3f%%p" % mde, flush=True)
    print("      SE 는 부트스트랩 폭에서: 95%% 구간 [%+.2f, %+.2f]%% → 연환산 [%+.3f, %+.3f]%%"
          % (lo_e, hi_e, cagr(lo_e, r2["years"]), cagr(hi_e, r2["years"])), flush=True)
    print("      (옛 식 2.8·sd/√n 이면 %.3f%%p — **20%% 낙관**이라 안 쓴다 · seed sd %.3f%%p)"
          % (old_mde, sd), flush=True)
    print("      관측 초과분 %+.3f%%p -> %s"
          % (bmed, "가릴 수 있는 크기" if abs(bmed) > mde else "🚨 못 가림"), flush=True)
    print("      🚨 이 MDE 는 «seed 축»만이다. 자료 축(국면)은 훨씬 크다.", flush=True)
    return {"A": a, "B": okb, "C": okc, "D": okd, "D_pct": pct,
            "excess_med": bmed, "excess_p25": b25, "mde": mde, "mde_old": old_mde,
            "mar": mar, "mar_pairwise": mar_ps, "mar_bm": marb}


# ═════════════════════════════════════════════════════════════════════════
# 4. 본실행
# ═════════════════════════════════════════════════════════════════════════
def main() -> int:
    quick = "--quick" in sys.argv
    use_ext = "--ext" in sys.argv
    n_seed = 12 if quick else N_SEED
    only = [a for a in sys.argv[1:] if not a.startswith("--")]

    print("=" * 106, flush=True)
    print("91 — 표본 밖 18.4년 · 사전등록 tasks/91(개정 1) · **아무것도 안 고쳤다**", flush=True)
    print("=" * 106, flush=True)
    print("비용%s · %d칸 %.0f%% · 위험 %.0f%% · 손절 -%.0f%% / 익절 +%.0f%% 절반 -> 추격 · seed %d · 등급 [%.2f,%.2f) · ext %s\n"
          % (COST, SLOTS, CAP * 100, RISK * 100, STOP, TARGET, n_seed, LO, HI,
             "사용" if use_ext else "미사용"), flush=True)

    allres, verd = {}, {}
    for lab, years, d0, d1 in WINDOWS:
        if only and not any(o in lab for o in only):
            continue
        res = run_window(lab, years, d0, d1, n_seed, use_ext)
        if res is None:
            continue
        if "대조" in lab:
            # ── 관문 ②(개정 1-③) ────────────────────────────────────────
            r2 = res["rows"][2]
            lo, hi = boot_ci(r2["raw"])
            print("\n  관문 ② — 74번 정본 %+.2f%% 재현" % CANON_74, flush=True)
            print("     ②%s ext %s · %d판 · 중앙 %+.2f%% · 95%% 구간 [%+.2f, %+.2f]"
                  % ("a" if use_ext else "b", "사용" if use_ext else "미사용",
                     n_seed, r2["med"], lo, hi), flush=True)
            if use_ext:
                ok = lo <= CANON_74 <= hi
                print("     -> 구간이 %+.2f%% 를 **%s** -> **%s**"
                      % (CANON_74, "품는다" if ok else "안 품는다",
                         "통과" if ok else "🚨 미통과 — 표본 밖 숫자를 읽지 않는다"), flush=True)
                verd["관문②a"] = ok
            else:
                print("     -> ②b 는 «문턱이 아니라 측정»이다. ②a 와의 차 = ext 227건의 효과.",
                      flush=True)
        else:
            verd[lab] = judge(res, n_seed)
        allres[lab] = res
        print("", flush=True)

    tag = "ext" if use_ext else "noext"
    p = OUT / ("91-out-of-sample-%s.json" % tag)
    p.write_text(json.dumps(
        {"verdict": verd, "n_seed": n_seed, "use_ext": use_ext,
         "windows": {k: {"rows": [{kk: vv for kk, vv in r.items()
                                   if kk not in ("raw", "eq")} for r in v["rows"]],
                         "bm": v["bm"], "d0": v["d0"], "d1": v["d1"],
                         "years": v["years"], "n_ext": v["n_ext"]}
                     for k, v in allres.items()}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("저장: %s" % p.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
