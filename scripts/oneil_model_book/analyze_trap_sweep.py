"""[#3 민감도] L + '선행상승 ≥ T%' 제외필터 임계 스위프 (2 사이클).

#3에서 L+선행상승이 최고 스위트스폿 → 임계 T 를 0~200% 훑어
위너잔존·안오름제거·lift·자연혼합 정밀도가 어떻게 변하는지, 그리고
c2024-12 와 c2020-03 둘 다에서 같은 방향인지(교차 견고성) 측정.
선행상승 결손은 '탈락'(안오름에 결손 많음=상승동력 부재 신호).

정직: 단일사이클쌍·사후·생존자·경계 데이터유래(원전/정밀컷 아님,
방향·민감도 확인용). 라이브 5신호와 model_book 변수 근사.
사용: python analyze_trap_sweep.py
"""
import json
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
THRS = [0, 25, 50, 75, 100, 150, 200]
PAIRS = [("c2024-12", "c2024-12-ctrl500", "2024-25(소수테마)"),
         ("c2020-03", "c2020-03-ctrl500", "2020-21(코로나광범위)")]


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def passes(r, thr):
    rs = num(r.get("rs_score"))
    if rs is None or rs < 80:
        return False
    if thr <= 0:
        return True
    pu = num(r.get("prior_uptrend_pct"))
    return pu is not None and pu >= thr      # 결손=탈락


def main():
    L = ["[#3 민감도] L(rs≥80) + 선행상승≥T% — 임계 스위프 · 2 사이클",
         "정밀도=위너통과/(위너+안오름통과) 자연혼합. *사후·생존자·방향용*",
         "=" * 64]
    for win, ctl, nm in PAIRS:
        W, Lo = rows(win), rows(ctl)
        L += [f"■ {nm}  (위너 {len(W)} : 안오름 {len(Lo)})",
              " T% | 위너통과 | 안오름통과 | 위너잔존 | 안오름제거 | lift | 정밀도"]
        for t in THRS:
            wp = sum(1 for r in W if passes(r, t))
            lp = sum(1 for r in Lo if passes(r, t))
            wr = wp / len(W) * 100 if W else 0
            lr = (1 - lp / len(Lo)) * 100 if Lo else 0
            lift = (wp / len(W)) / (lp / len(Lo)) if (Lo and lp) else None
            prec = wp / (wp + lp) * 100 if (wp + lp) else None
            L.append(f"{t:4d} | {wp:3d}/{len(W)} | {lp:3d}/{len(Lo)} | "
                     f"{wr:4.0f}% | {lr:4.0f}% | "
                     f"{'n/a' if lift is None else f'{lift:5.1f}x'} | "
                     f"{'n/a' if prec is None else f'{prec:4.0f}%'}")
        L.append("-" * 64)
    L += ["해석: 두 사이클서 정밀도·lift 가 같은 방향으로 오르면 임계가",
          "교차 견고. 위너잔존이 급락하는 T 직전이 실전 스위트스폿.",
          "정직한 한계: 사후·생존자(상폐 제외→안오름·필터가치 과소)·",
          "경계 데이터유래(원전 아님)·model_book 변수(라이브 근사)·",
          "2 사이클(추가 사이클로 임계 정식 보정 차기)."]
    out = CY.parent / "_trap_filter_sweep.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
