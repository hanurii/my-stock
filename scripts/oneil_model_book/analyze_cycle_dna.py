"""[사이클 DNA] ① 사이클 지문 + ② 전이성 점수표.

질문(사용자): 패턴이 *사이클 색깔*을 타는가? 타면 누적 인사이트는
다음(다른 색깔) 사이클에 못 쓴다. c2020-03(동학개미·광범위) vs
c2024-12(반도체+선진화·대형편중) 두 체질을 *숫자로* 대조.

① 지문: 시장주도(코스피/코스닥)·위너 시총·섹터집중(HHI)·매수주체
   (외인/기관/개인 순매수 부호)·위너 DNA(RS·선행상승·base·EPS).
② 점수표: 발견 패턴별 c2020 vs c2024 → 같은 방향? 크기 안정? →
   전이가능 / 부분 / 사이클전용 분류.
③ (별도) 3번째 사이클 건설은 사용자 요청 시.

★최대 한계: 완성 사이클 n=2. "둘이 일치/상충"은 말하되 "새 3번째
색깔 사이클 전이"는 증명 불가(n=2). 사후·종가·표본·추정 없음.
재사용: analyze_doppelganger.rows/num, analyze_trap_filter base_L/F1,
기존 *_rows.json(doppelganger/path_mae/profit_protect/equity_rt).
사용: python scripts/oneil_model_book/analyze_cycle_dna.py
"""
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from analyze_doppelganger import rows, num                 # noqa: E402
from analyze_trap_filter import base_L, F1                  # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"
CY = OUT / "cycles"
PAIR = ["c2020-03", "c2024-12"]


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def cyc_index(cid):
    ci = json.loads((CY / "cycles_index.json").read_text(encoding="utf-8"))
    L = ci["cycles"] if isinstance(ci, dict) else ci
    for c in L:
        if c["cycle_id"] == cid:
            return c
    return {}


def hhi(rws, key="induty_group3"):
    c = Counter(r.get(key) for r in rws if r.get(key))
    n = sum(c.values())
    return sum((v / n) ** 2 for v in c.values()) if n else None


def jload(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fingerprint(cid):
    W = rows(cid)
    ci = cyc_index(cid)
    mk = Counter(r.get("market") for r in W)
    nW = len(W)

    def share(getter, sign=1):
        v = [num(r.get(getter)) for r in W]
        v = [x for x in v if x is not None]
        pos = sum(1 for x in v if x * sign > 0)
        return (100 * pos / len(v)) if v else None, med(v)
    fg_p, fg_m = share("fgn_net_60d")
    og_p, og_m = share("inst_net_60d")
    iv_p, iv_m = share("indiv_net_60d_approx")
    return {
        "cid": cid,
        "kospi_gain": ci.get("kospi_gain_pct"),
        "kosdaq_gain": ci.get("kosdaq_gain_pct"),
        "win_kospi%": round(100 * mk.get("KOSPI", 0) / nW, 0),
        "win_kosdaq%": round(100 * mk.get("KOSDAQ", 0) / nW, 0),
        "mcap_med_eok": med([num(r.get("market_cap_at_pivot_eok"))
                             for r in W]),
        "sector_HHI": hhi(W),
        "fgn>0%": fg_p, "inst>0%": og_p, "indiv>0%": iv_p,
        "fgn_med": fg_m, "inst_med": og_m, "indiv_med": iv_m,
        "RS_med": med([num(r.get("rs_score")) for r in W]),
        "priorUp_med": med([num(r.get("prior_uptrend_pct")) for r in W]),
        "baseDepth_med": med([num(r.get("base_depth_pct")) for r in W]),
        "epsYoY_med": med([num(r.get("eps_yoy_q1_pct")) for r in W]),
    }


def trap_precision(cid):
    """analyze_trap_filter 정의: L+선행상승≥50, 위너 vs ctrl500 자연혼합."""
    W = rows(cid)
    Lo = rows(cid + "-ctrl500")
    fs = [base_L, F1]
    wp = sum(1 for r in W if all(f(r) for f in fs))
    lp = sum(1 for r in Lo if all(f(r) for f in fs))
    return (100 * wp / (wp + lp)) if (wp + lp) else None


def classify(a, b, higher_better=True, ratio_tol=2.0):
    """두 사이클 값 → 전이가능/부분/사이클전용."""
    if a is None or b is None:
        return "결손"
    if (a > 0) != (b > 0) and (abs(a) > 1e-6 and abs(b) > 1e-6):
        return "★사이클전용(부호반전)"
    lo, hi = sorted([abs(a), abs(b)])
    r = hi / lo if lo > 1e-9 else float("inf")
    if r <= ratio_tol:
        return "전이가능(방향·크기 안정)"
    return f"부분(방향OK·크기 {r:.1f}배 차)"


def main():
    fps = {c: fingerprint(c) for c in PAIR}
    L = ["[사이클 DNA] 사이클 지문 + 전이성 점수표  "
         f"({PAIR[0]} vs {PAIR[1]})",
         "질문: 패턴이 사이클 색깔을 타나? = 누적 인사이트가 다음",
         "사이클에 전이되나? *n=2 — 일치/상충만, 새 3번째 전이는 미증명*",
         "=" * 70,
         "■ ① 사이클 지문 (체질을 숫자로)",
         f"  {'지표':<22}| {PAIR[0]:>12} | {PAIR[1]:>12} | 해석"]

    def row(label, key, fmt="{:.1f}", note=""):
        a, b = fps[PAIR[0]].get(key), fps[PAIR[1]].get(key)
        fa = "결손" if a is None else fmt.format(a)
        fb = "결손" if b is None else fmt.format(b)
        L.append(f"  {label:<22}| {fa:>12} | {fb:>12} | {note}")

    row("코스피 상승%", "kospi_gain", "{:.0f}")
    row("코스닥 상승%", "kosdaq_gain", "{:.0f}",
        "코스닥>코스피=광범위/개인장")
    row("위너 코스피비중%", "win_kospi%", "{:.0f}")
    row("위너 코스닥비중%", "win_kosdaq%", "{:.0f}")
    row("위너 시총중앙(억)", "mcap_med_eok", "{:,.0f}",
        "클수록 대형주 주도")
    row("섹터집중 HHI", "sector_HHI", "{:.3f}",
        "높을수록 소수테마 편중")
    row("위너 외인순매수>0%", "fgn>0%", "{:.0f}")
    row("위너 기관순매수>0%", "inst>0%", "{:.0f}")
    row("위너 개인순매수>0%", "indiv>0%", "{:.0f}",
        "개인↑&외인↓=동학개미형")
    row("위너 RS중앙", "RS_med", "{:.0f}")
    row("위너 선행상승중앙%", "priorUp_med", "{:.0f}")
    row("위너 base깊이중앙%", "baseDepth_med", "{:.1f}")
    row("위너 직전EPS YoY중앙%", "epsYoY_med", "{:.0f}")

    # ② 점수표
    L += ["-" * 70, "■ ② 전이성 점수표 (발견 패턴별 c2020 vs c2024)",
          f"  {'패턴':<20}| {PAIR[0]:>10} | {PAIR[1]:>10} | 판정"]
    sc = []

    def sec(label, a, b, hb=True, tol=2.0, fa=None, fb=None):
        v = classify(a, b, hb, tol)
        sc.append((label, v))
        sa = "결손" if a is None else (fa or "{:.1f}").format(a)
        sb = "결손" if b is None else (fb or "{:.1f}").format(b)
        L.append(f"  {label:<20}| {sa:>10} | {sb:>10} | {v}")

    # RS·선행상승(모델북)
    sec("위너 RS중앙", fps[PAIR[0]]["RS_med"], fps[PAIR[1]]["RS_med"])
    sec("위너 선행상승중앙%", fps[PAIR[0]]["priorUp_med"],
        fps[PAIR[1]]["priorUp_med"])
    sec("섹터집중 HHI", fps[PAIR[0]]["sector_HHI"],
        fps[PAIR[1]]["sector_HHI"], fa="{:.3f}", fb="{:.3f}")
    # trap 정밀도
    tp = {c: trap_precision(c) for c in PAIR}
    sec("trap정밀도%(L+선행)", tp[PAIR[0]], tp[PAIR[1]],
        fa="{:.0f}", fb="{:.0f}")
    # 산출물 기반
    for c in PAIR:
        pass
    dop = {c: jload(CY / c / "doppelganger_rows.json") for c in PAIR}

    def dop_prec(c):
        d = dop[c]
        try:
            return d["screens"]["L+선행상승>=50"]["precision_natural_pct"]
        except Exception:
            return None
    sec("도플갱어정밀도%", dop_prec(PAIR[0]), dop_prec(PAIR[1]),
        fa="{:.0f}", fb="{:.0f}")

    pm = {c: jload(CY / c / "path_mae_rows.json") for c in PAIR}

    def mae_breach(c):
        d = pm[c]
        if not d or "rows" not in d:
            return None
        v = [r.get("mae") for r in d["rows"] if r.get("mae") is not None]
        return (100 * sum(1 for x in v if x <= -0.15) / len(v)) if v else None
    sec("MAE −15%돌파%(위너)", mae_breach(PAIR[0]), mae_breach(PAIR[1]),
        fa="{:.0f}", fb="{:.0f}")

    eq = {c: jload(CY / c / "equity_curve_rt_rows.json") for c in PAIR}

    def gcagr(c):
        d = eq[c]
        try:
            return d["guard"]["cagr"] * 100
        except Exception:
            return None
    sec("가드자본곡선 CAGR%", gcagr(PAIR[0]), gcagr(PAIR[1]),
        fa="{:+.0f}", fb="{:+.0f}")

    # 판정 집계
    tr = sum(1 for _, v in sc if v.startswith("전이가능"))
    pa = sum(1 for _, v in sc if v.startswith("부분"))
    cs = sum(1 for _, v in sc if v.startswith("★사이클전용"))
    L += ["=" * 70, "■ ③ 판정",
          f"  전이가능 {tr} · 부분(방향OK·크기차) {pa} · "
          f"사이클전용(부호반전) {cs}  / 평가 {len(sc)}",
          "  해석: '전이가능/부분'이 다수면 *방향성 인사이트는 다음",
          "  사이클에 쓸 수 있음*(선별 골격 L·선행상승·방향). '사이클",
          "  전용'·큰 크기차가 핵심 수익지표(정밀도·CAGR)에 몰리면 →",
          "  *절대 성과는 사이클 체질 의존, 종목패턴 암기보다 사이클",
          "  체질 판별을 최상위 스위치로* 두는 게 정답(나쁜결과의 쓸모).",
          "★한계: n=2 — 두 사이클 일치/상충만 측정. 새 3번째 색깔",
          "  사이클 전이는 미증명(3번 작업=과거사이클 건설 필요,",
          "  2015전 재무·수급 결손 반쪽). 사후·종가·표본·추정없음."]

    txt = "\n".join(L)
    (OUT / "_cycle_dna.txt").write_text(txt, encoding="utf-8")
    (OUT / "_cycle_dna.json").write_text(json.dumps(
        {"fingerprint": fps, "scorecard": sc,
         "tally": {"transfer": tr, "partial": pa, "cycle_only": cs}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 사이클 DNA·전이성 [{PAIR[0]} vs {PAIR[1]}]\n\n"
                f"```\n{txt}\n```\n")
    print(txt)


if __name__ == "__main__":
    main()
