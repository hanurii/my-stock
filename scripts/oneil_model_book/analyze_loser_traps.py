"""[2] 안오름만의 공통 함정 — 위너200 vs 안오름500 분포 대조.

각 핵심 축의 분포(중앙·Q1·Q3)를 두 그룹에 대고, '안오름이 위너와
어디서 갈리는가'(방향·중앙격차·결손율)를 raw로 제시. 임의 등급·컷오프
없음(원전/사용자 지정 외 분류 금지). 결손은 결손대로 — 추정 없음.
사용: python analyze_loser_traps.py
"""
import json
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"


def rows(p):
    m = json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
    return [r for r in m if not r.get("error")]


def num(x):
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace("%", "").replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def last_annual(r, key):
    v = r.get(key)
    if isinstance(v, list) and v:
        return num(v[-1][1]) if isinstance(v[-1], (list, tuple)) else None
    return None


def q(vals, frac):
    if not vals:
        return None
    s = sorted(vals)
    i = max(0, min(len(s) - 1, int(round(frac * (len(s) - 1)))))
    return s[i]


def stat(rws, getter):
    vals = [g for g in (getter(r) for r in rws) if g is not None]
    miss = len(rws) - len(vals)
    if not vals:
        return None, None, None, miss, 0
    return q(vals, .5), q(vals, .25), q(vals, .75), miss, len(vals)


AXES = [
    ("RS 상대강도(rs_score)", lambda r: num(r.get("rs_score"))),
    ("base 깊이%(base_depth_pct)", lambda r: num(r.get("base_depth_pct"))),
    ("base 길이일(base_len_days)", lambda r: num(r.get("base_len_days"))),
    ("선행상승%(prior_uptrend_pct)", lambda r: num(r.get("prior_uptrend_pct"))),
    ("신고가대비%(pivot_vs_prior_52w_high_pct)",
     lambda r: num(r.get("pivot_vs_prior_52w_high_pct"))),
    ("거래량/50일(pivot_volume_vs_50d_avg)",
     lambda r: num(r.get("pivot_volume_vs_50d_avg"))),
    ("외국인60일순매수(fgn_net_60d)", lambda r: num(r.get("fgn_net_60d"))),
    ("기관60일순매수(inst_net_60d)", lambda r: num(r.get("inst_net_60d"))),
    ("직전분기EPS YoY%(eps_yoy_q1_pct)", lambda r: num(r.get("eps_yoy_q1_pct"))),
    ("최근연간EPS(annual_eps_3y 말)", lambda r: last_annual(r, "annual_eps_3y")),
    ("부채비율%(debt_ratio_3y 말)", lambda r: last_annual(r, "debt_ratio_3y")),
]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12")
    ap.add_argument("--ctl", default="c2024-12-ctrl500")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    W, Lo = rows(a.win), rows(a.ctl)
    out = [f"[2] 안오름 공통 함정 [{a.win} vs {a.ctl}] — "
           f"위너 n={len(W)} vs 안오름 n={len(Lo)}",
           "각 축: 중앙(Q1~Q3) | 결손수.  *raw 분포, 등급 없음, 추정 없음*",
           "-" * 64]
    for name, g in AXES:
        wm, wq1, wq3, wmiss, wn = stat(W, g)
        lm, lq1, lq3, lmiss, ln = stat(Lo, g)

        def f(x):
            return "결손" if x is None else (f"{x:,.1f}" if abs(x) >= 100 else f"{x:.2f}")
        gap = ("" if wm is None or lm is None
               else f"  Δ중앙(위너−안오름)={wm-lm:+,.1f}")
        out += [f"■ {name}",
                f"   위너  : {f(wm)} ({f(wq1)}~{f(wq3)}) | 결손 {wmiss}/{len(W)}",
                f"   안오름: {f(lm)} ({f(lq1)}~{f(lq3)}) | 결손 {lmiss}/{len(Lo)}"
                f"{gap}"]
    # 시장국면 분포(범주형)
    def regdist(rws):
        from collections import Counter
        c = Counter((r.get("market_regime_at_pivot") or "결손") for r in rws)
        n = len(rws)
        return ", ".join(f"{k}:{round(100*v/n)}%" for k, v in c.most_common())
    out += ["■ pivot 시점 시장국면(market_regime_at_pivot)",
            f"   위너  : {regdist(W)}",
            f"   안오름: {regdist(Lo)}"]
    out += ["-" * 64,
            "해석: Δ중앙이 크고 같은 방향이면 '안오름은 그 축이 약함' =",
            "      위너 진입 전 그 축을 확인하라는 근거. 분포 겹침 크면",
            "      단독 변별 약함. 한계: 사후·생존자(상폐 제외, 안오름",
            "      손실 과소)·단일 사이클·일부 축 결손 큼(추정 안 함)."]
    p = CY.parent / f"_loser_traps{a.tag}.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {p} (axes {len(AXES)}+regime, W={len(W)} Lo={len(Lo)})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
