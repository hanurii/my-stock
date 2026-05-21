"""'섹터 무리' 비순환 검증 — 위너가 비위너보다 섹터로 더 뭉치나?

§5 '동업종 위너수'는 위너 집합 안에서 위너를 센 순환(생존자) 지표.
비순환 검증: 위너(c2024-12 200) vs 비위너 대조군(c2024-12-ctrl 100)
의 induty_group3 섹터 집중도(HHI·유효섹터수)를 비교하고, 라벨
순열검정으로 '위너가 더 집중'이 우연 이상인지 p값 산출. 같은
유니버스서 뽑힌 대조군이 동등 집중이면 유니버스 아티팩트, 위너가
유의하게 더 집중이면 '섹터 무리'=진짜 위너 특성. c2020-03(100)도
참고. 네트워크 불요·환각 금지.

사용: python analyze_sector_cluster.py
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"


def secs(p):
    m = json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
    return [str(r.get("induty_group3")) for r in m
            if r.get("induty_group3") not in (None, "", "None")]


def hhi(labels):
    n = len(labels)
    c = Counter(labels)
    h = sum((v / n) ** 2 for v in c.values())
    return h, (1 / h if h else 0), c


def main():
    win = secs("c2024-12")          # 위너 200
    ctl = secs("c2024-12-ctrl")     # 비위너 100
    w20 = secs("c2020-03")          # 위너 100 (참고·교차)

    hw, ew, cw = hhi(win)
    hc, ec, cc = hhi(ctl)
    h2, e2, c2 = hhi(w20)

    def top5(c, n):
        return ", ".join(f"{k}:{v}({round(100*v/n)}%)"
                         for k, v in c.most_common(5))

    L = ["[섹터 무리 비순환 검증] HHI=섹터집중(↑=뭉침), 유효섹터수=1/HHI",
         f"위너 c2024-12 n={len(win)}: HHI {hw:.3f} · 유효섹터 {ew:.1f} · "
         f"top5 {top5(cw,len(win))}",
         f"비위너 대조  n={len(ctl)}: HHI {hc:.3f} · 유효섹터 {ec:.1f} · "
         f"top5 {top5(cc,len(ctl))}",
         f"(참고 위너 c2020-03 n={len(w20)}: HHI {h2:.3f} · 유효섹터 "
         f"{e2:.1f} · top5 {top5(c2,len(w20))})",
         ""]

    # 순열검정: 위너+대조 풀에서 라벨 무작위 재배정, 위너HHI−대조HHI 분포
    pool = [(s, 1) for s in win] + [(s, 0) for s in ctl]
    nw, nc = len(win), len(ctl)
    obs = hw - hc
    random.seed(7)
    ge = 0
    N = 2000
    sp = [s for s, _ in pool]
    for _ in range(N):
        random.shuffle(sp)
        a = sp[:nw]
        b = sp[nw:nw + nc]
        if (hhi(a)[0] - hhi(b)[0]) >= obs:
            ge += 1
    p = ge / N
    L += [f"순열검정(N={N}): 관측 위너HHI−대조HHI = {obs:+.3f}",
          f"  무작위로 이만큼 집중 격차가 날 확률 p = {p:.3f} "
          f"({'유의 — 위너가 우연 이상으로 더 섹터 집중(섹터무리 진짜)' if p<0.05 else '비유의 — 위너·대조 섹터집중 차이 우연 범위(섹터무리=유니버스 아티팩트 가능)'})",
          "",
          "해석: 위너 HHI > 대조 HHI 이고 p<0.05 면 '위너는 비위너보다",
          "섹터로 유의하게 더 뭉친다' = 섹터 무리가 비순환적 위너 특성.",
          "p≥0.05 면 §5의 동업종위너수는 순환(생존자) 착시로 결론.",
          "한계: 표본 200/100·induty_group3 3자리·단일 사이클 대조"
          "(c2020-03는 대조군 없어 참고만)·종목선택 무관 사후."]
    out = CY.parent / "_sector_cluster.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} (p={p:.3f})", file=sys.stderr)


if __name__ == "__main__":
    main()
