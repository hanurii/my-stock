"""[1] 섹터 무리 재검증 — 위너 200 vs 안오름 대조군 500 (비순환).

기존 analyze_sector_cluster(대조 100)을 대조 500으로 5배 확대.
HHI=섹터집중(↑뭉침), 유효섹터수=1/HHI, 라벨순열검정 p값.
네트워크 불요·환각 금지·결손 제외(추정 없음).
사용: python analyze_sector_cluster_500.py
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"


def secs(p):
    m = json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
    return [str(r.get("induty_group3")) for r in m
            if not r.get("error") and r.get("induty_group3") not in (None, "", "None")]


def hhi(labels):
    n = len(labels)
    c = Counter(labels)
    h = sum((v / n) ** 2 for v in c.values()) if n else 0
    return h, (1 / h if h else 0), c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12", help="위너 사이클 디렉터리")
    ap.add_argument("--ctl", default="c2024-12-ctrl500", help="안오름 대조 디렉터리")
    ap.add_argument("--tag", default="n500", help="출력 파일 태그")
    a = ap.parse_args()

    win = secs(a.win)
    ctl = secs(a.ctl)
    hw, ew, cw = hhi(win)
    hc, ec, cc = hhi(ctl)

    def top5(c, n):
        return ", ".join(f"{k}:{v}({round(100*v/n)}%)" for k, v in c.most_common(5))

    L = [f"[1] 섹터 무리 재검증 — {a.win}(위너) vs {a.ctl}(안오름) (비순환)",
         f"위너 {a.win}  n={len(win)}: HHI {hw:.3f} · 유효섹터 {ew:.1f} · "
         f"top5 {top5(cw,len(win))}",
         f"안오름 {a.ctl} n={len(ctl)}: HHI {hc:.3f} · 유효섹터 {ec:.1f} · "
         f"top5 {top5(cc,len(ctl))}", ""]

    pool = list(win) + list(ctl)
    nw, nc = len(win), len(ctl)
    obs = hw - hc
    random.seed(7)
    N, ge = 4000, 0
    for _ in range(N):
        random.shuffle(pool)
        if (hhi(pool[:nw])[0] - hhi(pool[nw:nw + nc])[0]) >= obs:
            ge += 1
    p = ge / N
    L += [f"순열검정(N={N}): 관측 위너HHI−대조HHI = {obs:+.3f}",
          f"  무작위로 이만큼 격차 날 확률 p = {p:.4f} "
          f"({'유의 — 위너가 우연 이상으로 섹터 집중(섹터무리 진짜·n500 재확인)' if p < 0.05 else '비유의'})",
          "",
          "해석: 위너 HHI > 대조 HHI & p<0.05 → 위너는 안오름보다 소수",
          "핫섹터에 유의하게 더 뭉친다 = 섹터 무리는 비순환 위너 특성.",
          "한계: induty_group3 3자리·단일 사이클 대조·상폐 제외(생존자)·"
          "사후. 대조 100→500 확대로 신뢰도 강화(절대수치 아닌 방향)."]
    out = CY.parent / f"_sector_cluster_{a.tag}.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} (p={p:.4f}, winHHI={hw:.3f} ctlHHI={hc:.3f})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
