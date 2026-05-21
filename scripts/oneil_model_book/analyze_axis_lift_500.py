"""[3] 변별축 전면 재대조 — 위너200 vs 안오름500 enrichment lift.

각 축의 통과기준은 *원전/사용자 지정*만 사용(임의 컷오프 금지):
 L  rs_score ≥ 80            (user_canslim_thresholds)
 C  eps_yoy_q1_pct ≥ +25%    (분기 EPS YoY +25%)
 I  fgn_net_60d>0 OR inst_net_60d>0  (외인 또는 기관 60일 순매수)
 A* 최근 연간 EPS > 0         (A의 흑자요건 단순 프록시 — 정식 80점/ROE
                               아님, 방향 확인용으로만 표기)
 S  부채비율(말) ≤ 130%       (130% 초과 제외 기준)
 M  market_regime '상승' 포함  (시장 상승국면)
lift = P(통과|위너) / P(통과|안오름).  결손은 분모서 제외(추정 없음).
사용: python analyze_axis_lift_500.py
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
        try:
            return float(x.strip().replace("%", "").replace(",", ""))
        except ValueError:
            return None
    return None


def last_annual(r, k):
    v = r.get(k)
    return (num(v[-1][1]) if isinstance(v, list) and v
            and isinstance(v[-1], (list, tuple)) else None)


def L_(r):
    v = num(r.get("rs_score"))
    return None if v is None else v >= 80


def C_(r):
    v = num(r.get("eps_yoy_q1_pct"))
    return None if v is None else v >= 25


def I_(r):
    f, i = num(r.get("fgn_net_60d")), num(r.get("inst_net_60d"))
    return None if (f is None and i is None) else ((f or 0) > 0 or (i or 0) > 0)


def A_(r):
    v = last_annual(r, "annual_eps_3y")
    return None if v is None else v > 0


def S_(r):
    v = last_annual(r, "debt_ratio_3y")
    return None if v is None else v <= 130


def M_(r):
    s = r.get("market_regime_at_pivot")
    return None if not s else ("상승" in s)


AXES = [("L 상대강도 rs≥80", L_), ("C 분기EPS YoY≥+25%", C_),
        ("I 외인/기관 60일 순매수", I_), ("A* 연간EPS>0(프록시)", A_),
        ("S 부채비율≤130%", S_), ("M 시장 상승국면", M_)]


def rate(rws, fn):
    ev = [fn(r) for r in rws]
    val = [e for e in ev if e is not None]
    miss = len(ev) - len(val)
    passed = sum(1 for e in val if e)
    return (passed / len(val) if val else None), passed, len(val), miss


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12")
    ap.add_argument("--ctl", default="c2024-12-ctrl500")
    ap.add_argument("--tag", default="n500")
    a = ap.parse_args()
    W, Lo = rows(a.win), rows(a.ctl)
    out = [f"[3] 변별축 재대조 lift [{a.win} vs {a.ctl}] — "
           f"위너 n={len(W)} vs 안오름 n={len(Lo)}",
           "통과율(통과/유효) · lift=위너통과율÷안오름통과율 · 결손 제외",
           "기준=원전/사용자 지정만. *수익 보장 아님·방향 지표*",
           "-" * 60]
    for name, fn in AXES:
        pw, aw, vw, mw = rate(W, fn)
        pl, al, vl, ml = rate(Lo, fn)
        lift = (pw / pl) if (pw is not None and pl) else None
        sw = "결손전부" if pw is None else f"{pw*100:.0f}% ({aw}/{vw})"
        sl = "결손전부" if pl is None else f"{pl*100:.0f}% ({al}/{vl})"
        sf = "n/a" if lift is None else f"{lift:.2f}x"
        out.append(f"■ {name}: 위너 {sw} | 안오름 {sl} | "
                   f"lift {sf} | 결손 W{mw}/Lo{ml}")
    out += ["-" * 60,
            "해석: lift>1=위너에 더 흔함(변별축), ≈1=무변별, <1=역효과.",
            "L·I 가 높게 재현되면 코어 선별축 n500 재확인. C/A/S 약하거나",
            "≈1이면 '필터로 쓰지 말 것'(생존자 착시) 재확인.",
            "한계: 단일 사이클·사후·상폐 제외(안오름 손실 과소)·A는",
            "정식 정의 아닌 흑자 프록시·결손 축은 표본 작을 수 있음."]
    p = CY.parent / f"_axis_lift_{a.tag}.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
