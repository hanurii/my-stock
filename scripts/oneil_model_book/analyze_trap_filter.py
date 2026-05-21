"""[#3] 안오름 함정을 제외 필터로 결합 시 변별력 변화 (c2024-12).

코어 선별 L(rs≥80)에, [2]에서 나온 '안오름 공통 함정'을 *제외 필터*로
하나씩/전부 더해, 위너 잔존·안오름 제거·lift·자연혼합 정밀도가
어떻게 변하는지 측정. 모집단 = 위너200 : 안오름500 (자연 비율).

제외 필터(안오름처럼 보이면 탈락) — 경계는 [2] 위너/안오름 분포 기반
(임의 등급 아님·방향 확인용·정밀 컷은 차기):
 F1 선행상승  prior_uptrend_pct ≥ 50      (위너中106 vs 안오름中30, 결손=탈락)
 F2 시장국면  market_regime '상승' 포함
 F3 신고가    pivot_vs_prior_52w_high_pct ≥ 70 (위너 Q1 70.5)
 F4 외인매집  fgn_net_60d > 0
정직: 단일 사이클·사후·생존자(상폐 제외)·경계 데이터유래(원전 아님).
사용: python analyze_trap_filter.py
"""
import json
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def base_L(r):
    v = num(r.get("rs_score"))
    return v is not None and v >= 80


def F1(r):
    v = num(r.get("prior_uptrend_pct"))
    return v is not None and v >= 50


def F2(r):
    s = r.get("market_regime_at_pivot")
    return bool(s) and ("상승" in s)


def F3(r):
    v = num(r.get("pivot_vs_prior_52w_high_pct"))
    return v is not None and v >= 70


def F4(r):
    v = num(r.get("fgn_net_60d"))
    return v is not None and v > 0


FILTERS = [("F1 선행상승≥50", F1), ("F2 시장상승", F2),
           ("F3 신고가≥70%", F3), ("F4 외인매집", F4)]


def passes(r, fs):
    return base_L(r) and all(f(r) for _, f in fs)


def evaluate(W, Lo, fs):
    wp = sum(1 for r in W if passes(r, fs))
    lp = sum(1 for r in Lo if passes(r, fs))
    wr = wp / len(W) if W else 0
    lr = 1 - (lp / len(Lo)) if Lo else 0
    lift = (wp / len(W)) / (lp / len(Lo)) if (Lo and lp) else None
    prec = wp / (wp + lp) if (wp + lp) else None     # 자연혼합(200:500)
    return wp, lp, wr, lr, lift, prec


def main():
    W, Lo = rows("c2024-12"), rows("c2024-12-ctrl500")
    L = [f"[#3] 안오름 함정 제외필터 결합 변별력 — 위너 {len(W)} : 안오름 {len(Lo)}",
         "선별 = L(rs≥80) + 제외필터. 자연혼합 정밀도 = 위너통과/(위너+안오름통과)",
         "*확률·사후·단일사이클·생존자. lift>1=변별, 정밀도↑=실전 골라냄.*",
         "-" * 66,
         "구성 | 위너통과 | 안오름통과 | 위너잔존% | 안오름제거% | lift | 정밀도"]

    def line(name, fs):
        wp, lp, wr, lr, lift, prec = evaluate(W, Lo, fs)
        L.append(f"{name:16s} | {wp:3d}/{len(W)} | {lp:3d}/{len(Lo)} | "
                 f"{wr*100:4.0f}% | {lr*100:4.0f}% | "
                 f"{'n/a' if lift is None else f'{lift:4.1f}x'} | "
                 f"{'n/a' if prec is None else f'{prec*100:4.0f}%'}")

    line("BASE L만", [])
    for nm, f in FILTERS:
        line(f"L+{nm}", [(nm, f)])
    line("L+전체(F1~F4)", FILTERS)
    L += ["-" * 66,
          "해석: BASE 대비 정밀도(자연혼합서 통과자가 진짜 위너일 확률)와",
          "lift 가 오르면 그 제외필터가 안오름을 더 걸러 변별력 강화.",
          "단 위너잔존%가 크게 떨어지면 '좋은 위너도 같이 버림'(trade-off).",
          "정직한 한계: 단일 사이클·사후·생존자(상폐 제외 → 안오름 손실",
          "·필터 가치 과소)·경계는 [2] 분포 유래(원전/정밀 컷 아님,",
          "방향 확인용)·model_book 변수 기반(라이브 5신호와 근사)."]
    out = CY.parent / "_trap_filter.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
