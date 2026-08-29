# -*- coding: utf-8 -*-
"""104v 0단계 — **재표집 관문 (합성 계열 · 기지답 시험).**

🚨 **이동 판이 «실패해야» 통과다.** 실패 안 하면 관문에 분해능이 없는 것이고,
   그러면 「고쳤다」의 증거가 못 된다 (유형 24′).

세 가지를 잰다:
  ㉠ **덮개 비율**   첫날/가운데 등장 횟수 → 예측 **1/block**
  ㉡ **옮겨간 무게** 덜 덮인 몫의 합       → 예측 **(block−1)/n**
  ㉢ **기지답 시험** 가운데는 전부 0 · 양 끝만 +X 인 계열
                    참 총수익 = (1+X)²−1.  이동은 «크게 밑돌아야» 하고 순환은 «맞아야» 한다

자료가 필요 없다. 몇 초면 돈다. 재표집을 건드릴 때마다 돌린다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/104v-resample-gate.py
"""
from __future__ import annotations

import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                    # noqa: E402

N = 2250                 # 우리 창의 대략 길이
BLOCKS = da.BLOCKS       # (20, 40, 80)
X = 0.05                 # 양 끝 이틀의 일수익
N_REP = 4000


def coverage(n, block, cyclic, rnd, reps=400):
    """원 자리 인덱스가 «몇 번» 뽑히는지 센다 — 재표집 한 판당 기대 1.0 이 정상."""
    old = da.CYCLIC[0]
    da.CYCLIC[0] = cyclic
    try:
        idx = list(range(n))
        c = Counter()
        for _ in range(reps):
            c.update(da._resample(idx, block, rnd))
        return {k: v / reps for k, v in c.items()}
    finally:
        da.CYCLIC[0] = old


def known_answer(n, block, cyclic, rnd):
    """가운데 전부 0 · 양 끝만 +X → 참 총수익 (1+X)²−1 을 재현하는가."""
    old = da.CYCLIC[0]
    da.CYCLIC[0] = cyclic
    try:
        r = [0.0] * n
        r[0] = X
        r[-1] = X
        vals = [da._compound(da._resample(r, block, rnd)) for _ in range(N_REP)]
        return st.mean(vals), st.median(vals)
    finally:
        da.CYCLIC[0] = old


def main() -> int:
    true_tot = ((1 + X) ** 2 - 1) * 100
    print("=" * 100)
    print("104v 0단계 — 재표집 관문 (합성 계열 · 자료 불필요)")
    print("   n = %d · 블록 %s · 양 끝 이틀만 +%.0f%% · **참 총수익 %.4f%%**"
          % (N, BLOCKS, X * 100, true_tot))
    print("   🚨 **이동 판이 «실패해야» 통과다** (유형 24′)")
    print("=" * 100, flush=True)

    ok_all = True
    print("\n㉠㉡ 덮개 — 첫날/가운데 비율과 «옮겨간 무게»", flush=True)
    print("  %-6s %-6s %12s %12s %12s %12s"
          % ("블록", "재표집", "첫날 덮개", "가운데 덮개", "비율", "예측 1/block"), flush=True)
    print("  " + "-" * 68, flush=True)
    for block in BLOCKS:
        for cyc, lab in ((False, "이동"), (True, "순환")):
            rnd = random.Random(104)
            cov = coverage(N, block, cyc, rnd)
            first = cov.get(0, 0.0)
            mid = st.mean(cov.get(i, 0.0) for i in range(N // 2 - 50, N // 2 + 50))
            ratio = first / mid if mid else float("nan")
            pred = 1.0 / block if not cyc else 1.0
            print("  %-6d %-6s %11.4f %11.4f %11.4f %11.4f"
                  % (block, lab, first, mid, ratio, pred), flush=True)
        # 옮겨간 무게
        # 🚨 처음엔 `sum(max(0, 1 − cov_i))/N` 로 쟀는데 «표집 잡음»이 지배했다 —
        #    400판이면 자리마다 SD≈0.05 라, 절반이 우연히 1.0 아래로 내려가 가짜 손실을 만든다.
        #    (실측 0.0263 vs 예측 0.0084 = 3.1배. 블록 80 에서만 맞은 것이 그 증거였다.)
        #    고침: ㉮ 판수를 늘리고 ㉯ 기준선을 «1.0» 이 아니라 «가운데 실측 평균»으로 두고
        #          ㉰ «양 끝 구간(block−1일)»에서만 잰다 — 잡음은 양쪽으로 상쇄된다.
        rnd = random.Random(104)
        cov = coverage(N, block, False, rnd, reps=4000)
        base = st.mean(cov.get(i, 0.0) for i in range(N // 2 - 200, N // 2 + 200))
        ends = list(range(block - 1)) + list(range(N - block + 1, N))
        lost = sum(max(0.0, base - cov.get(i, 0.0)) for i in ends) / (base * N)
        print("       → 이동 판 «옮겨간 무게» **%.4f** · 예측 (block−1)/n = **%.4f**"
              " (양 끝 %d일 · 기준선 %.4f)"
              % (lost, (block - 1) / N, len(ends), base), flush=True)

    print("\n㉢ 기지답 시험 — 참 총수익 **%.4f%%** 를 재현하는가" % true_tot, flush=True)
    print("  %-6s %-6s %14s %14s %10s"
          % ("블록", "재표집", "재표집 평균", "참값 대비", "판정"), flush=True)
    print("  " + "-" * 60, flush=True)
    for block in BLOCKS:
        row = {}
        for cyc, lab in ((False, "이동"), (True, "순환")):
            rnd = random.Random(2104)
            m, _md = known_answer(N, block, cyc, rnd)
            row[lab] = m
            rel = m / true_tot if true_tot else float("nan")
            if lab == "이동":
                good = rel < 0.5          # «크게 밑돌아야» 한다
                tag = "**실패해야 함 → %s**" % ("실패 ✅" if good else "🚨 안 실패")
            else:
                good = 0.8 <= rel <= 1.25
                tag = "맞아야 함 → %s" % ("맞음 ✅" if good else "🚨 안 맞음")
            ok_all = ok_all and good
            print("  %-6d %-6s %13.4f%% %13.3f %s" % (block, lab, m, rel, tag), flush=True)

    print("\n" + "=" * 100)
    print("관문 판정 — **%s**" % ("통과 (이동은 실패하고 순환은 맞는다)" if ok_all
                                  else "🚨 미통과 — 여기서 멈춘다"))
    print("=" * 100, flush=True)
    if not ok_all:
        print("🚨 관문이 죽었다. 이동 판이 «실패하지 않으면» 이 관문은 「고쳤다」의 증거가 못 된다.",
              flush=True)
        return 1
    print("★ 이동 판이 «실제로» 참값을 못 맞힌다 = 관문에 분해능이 있다.", flush=True)
    print("  그러므로 순환 판이 맞히는 것이 «의미 있는» 통과다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
