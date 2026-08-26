# -*- coding: utf-8 -*-
"""정답을 «아는» 계열을 먹여 `band_paired` 의 중앙이 무엇을 재는지 본다.

물음: 부트스트랩 중앙 median(exp(Σ 재표집 d)) 이 «관측» exp(Σd) 를 되돌려 주는가?
  - 가벼운 꼬리(모든 날이 비슷) → 되돌려 줘야 한다
  - 무거운 꼬리(며칠이 다 함) → **되돌려 주지 않는다**(재표집 중앙이 그 며칠을 잃는다)

이건 74v ⑥에서 A₁₀(+11.45%) 와 band_paired(−2.02%) 가 갈린 이유의 후보다.
"""
import math
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path("research/handoff/scripts").resolve()))
import dataaxis as da                                   # noqa: E402

N = 2250
BLOCK = 20
REPS = 2000


def observed(d):
    return (math.exp(sum(d)) - 1) * 100


def boot_median(d, block=BLOCK, reps=REPS, seed=7):
    rnd = random.Random(seed)
    v = [(math.exp(sum(da._resample(d, block, rnd))) - 1) * 100 for _ in range(reps)]
    return st.median(sorted(v))


def main():
    print("=" * 88)
    print("정답을 아는 계열 — band_paired 의 «중앙»이 관측을 되돌려 주는가")
    print("=" * 88)
    print("  %-34s %14s %14s %10s" % ("계열", "관측", "부트 중앙", "비"))

    rnd = random.Random(1)
    cases = []

    # ① 가벼운 꼬리 — 매일 조금씩 같은 방향
    d1 = [0.0001 + rnd.gauss(0, 0.001) for _ in range(N)]
    cases.append(("① 가벼운 꼬리 (매일 +0.01%)", d1))

    # ② 무거운 꼬리 — 총합은 ①과 «같게» 맞추되 며칠이 다 만든다
    base = sum(d1)
    d2 = [rnd.gauss(0, 0.001) for _ in range(N)]
    d2 = [x - sum(d2) / N for x in d2]                  # 평균 0 으로
    for i in (137, 902, 1544):                          # 세 날이 전부를 만든다
        d2[i] += base / 3.0
    cases.append(("② 무거운 꼬리 (세 날이 전부)", d2))

    # ③ 중간 — 서른 날이 만든다
    d3 = [rnd.gauss(0, 0.001) for _ in range(N)]
    d3 = [x - sum(d3) / N for x in d3]
    for i in range(30):
        d3[i * 70 + 11] += base / 30.0
    cases.append(("③ 서른 날이 만든다", d3))

    for nm, d in cases:
        o, b = observed(d), boot_median(d)
        print("  %-34s %+13.2f%% %+13.2f%% %9.2f배"
              % (nm, o, b, (b / o) if abs(o) > 1e-9 else float("nan")))

    print()
    print("  ★ ①이 1.0 배 근처인데 ②가 크게 작으면 —")
    print("    **`band_paired` 의 중앙은 «관측»이 아니라 «며칠을 잃은 세계»를 잰다.**")
    print("    그러면 그 중앙을 「효과 크기」로 읽으면 안 된다(구간은 여전히 유효하다).")


main()
