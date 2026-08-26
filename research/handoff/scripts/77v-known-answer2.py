# -*- coding: utf-8 -*-
"""물음 둘째 — 「스트림 10개의 중앙」과 「10×100 을 통째로 모은 중앙」이 왜 갈리나.

`band_paired` 는 스트림마다 100회를 뽑아 **% 로 바꾼 뒤 1,000개를 통째로** 정렬한다.
`exp` 가 볼록이므로 **% 공간에서 섞으면** 스트림별 퍼짐이 달라져 중앙이 끌린다.

정답을 아는 판: 스트림 10개의 참값(로그)을 «내가 정하고», 퍼짐은 «전부 같게» 준다.
그러면 「중앙」은 정의상 스트림 참값의 중앙이어야 한다.
"""
import math
import random
import statistics as st

STREAMS_LOG = [0.40, 0.34, 0.26, 0.14, 0.11, 0.10, -0.05, -0.22, -0.43, -0.92]
SD = 0.45          # 스트림 안 재표집 퍼짐(로그) — 전부 같게
REPS = 100


def main():
    rnd = random.Random(3)
    pct, logs = [], []
    for mu in STREAMS_LOG:
        for _ in range(REPS):
            x = rnd.gauss(mu, SD)
            logs.append(x)
            pct.append((math.exp(x) - 1) * 100)
    pct.sort()
    logs.sort()
    truth = st.median(STREAMS_LOG)

    print("=" * 88)
    print("스트림 10 × 재표집 100 — 「중앙」을 어디서 잡나")
    print("=" * 88)
    print("  스트림 참값(로그)  : %s" % " ".join("%+.2f" % x for x in STREAMS_LOG))
    print()
    print("  %-44s %+12.2f%%" % ("① 참값 — 스트림 중앙을 %로 (정답)",
                                 (math.exp(truth) - 1) * 100))
    print("  %-44s %+12.2f%%" % ("② % 공간에서 1,000개를 통째로 (band_paired 방식)",
                                 st.median(pct)))
    print("  %-44s %+12.2f%%" % ("③ 로그 공간에서 통째로 → 마지막에 exp",
                                 (math.exp(st.median(logs)) - 1) * 100))
    print("  %-44s %+12.2f%%"
          % ("④ 스트림마다 중앙 → 그 중앙들의 중앙",
             (math.exp(st.median([st.median([rnd.gauss(mu, SD) for _ in range(REPS)])
                                  for mu in STREAMS_LOG])) - 1) * 100))
    print()
    print("  ★ ②가 ①에서 멀면 «% 공간에서 섞은 것» 자체가 원인이다.")
    print("    ③④가 ①에 가까우면 고치는 법이 그 둘이다.")


main()
