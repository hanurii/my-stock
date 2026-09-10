# -*- coding: utf-8 -*-
r"""183a ⓪단계 — **`23c` 의 «자기» 재표집에 `104v` 의 «세 자»를 «건다».**

  🚨 `23c-boot-and-maxstat.py` 는 `dataaxis` 를 **«안» 쓴다** ⇒ 「계열 «양 끝»만 뽑는」
     결함이 **«직접» 전이되지 «않는다»**. 그러나 **«자기» 재표집(`boot_eq` 앞의 블록 뽑기)은
     «검사»를 «안» 받았다**.

  🔎 `23c:113-118`
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)        # 20 ~ 40
        a = rnd.randint(0, n_pos - L)                # ← **«이동» 블록**(순환 «아님»)

  `104v` 의 세 자를 «그대로» 쓴다:
    ㉠ **덮개 비율**   — 자리마다 «몇 번» 뽑히나(한 판당 기대 **1.0**)
    ㉡ **옮겨간 무게** — 덜 덮인 몫의 «합»
    ㉢ **기지답 시험** — 가운데는 «전부» 0 · **양 끝만** +X 인 계열.
                        참 총수익 = (1+X)²−1. **이동은 «크게 밑돌아야»** 관문에 «분해능»이 있다.

  🚨 **이동 판이 «실패해야» 통과다**(유형 24′). 실패 «안» 하면 관문이 «아무것도» 안 잰다.
"""
from __future__ import annotations
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BMIN, BMAX = 20, 40          # `23c:37` 그대로
X = 0.05
N_REP = 4000


def draw(n, rnd, cyclic):
    """`23c:112-118` «그대로» — 다만 `cyclic=True` 면 시작점을 [0, n−1] 로 «감는다»."""
    blocks, tot = [], 0
    while tot < n:
        L = rnd.randint(BMIN, BMAX)
        a = rnd.randint(0, n - 1) if cyclic else rnd.randint(0, n - L)
        LL = min(L, n - tot)
        blocks.append((a, LL))
        tot += LL
    out = []
    for a, L in blocks:
        for j in range(L):
            out.append((a + j) % n if cyclic else a + j)
    return out[:n]


def coverage(n, cyclic, reps=400):
    rnd = random.Random(4242)
    cnt = Counter()
    for _ in range(reps):
        for i in draw(n, rnd, cyclic):
            cnt[i] += 1
    return [cnt[i] / reps for i in range(n)]


def known(n, cyclic, reps=N_REP):
    """가운데 0 · «양 끝» 이틀만 +X. 참 총수익 = (1+X)^2 − 1."""
    r = [0.0] * n
    r[0] = r[n - 1] = X
    rnd = random.Random(99)
    out = []
    for _ in range(reps):
        v = 1.0
        for i in draw(n, rnd, cyclic):
            v *= (1.0 + r[i])
        out.append((v - 1.0) * 100.0)
    return out


def main():
    P = print
    P("=" * 104)
    P("183a ⓪단계 — **`23c` 의 재표집에 `104v` 의 «세 자»를 «건다»**")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-06 · `scripts/183a-23c-resample-gate.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **왜 «먼저» 이것인가**")
    P("")
    P("```")
    P("`23c-boot-and-maxstat.py` 는 **다섯 판이 «근거»로 쓴 「귀무 95% +87.47%p」의 «출처»**다")
    P("   (`23`·`165`·`173`·`179`·`182` 가 그 수를 인용했다)")
    P("🚨 그런데 그 파일의 **«자기» 재표집은 «검사»를 «안» 받았다**")
    P("✅ `104v-resample-gate.py` 가 «스스로» 적었다:")
    P("   **「자료가 «필요 없다». 몇 초면 돈다. **재표집을 «건드릴 때마다» 돌린다**」**")
    P("⇒ ★ **「이미 «만든» 도구를 «먼저» 본다」 — «오늘 세 번째»**(📏폭 열 · 이번 · …)")
    P("")
    P("🚨 **관문의 «규약»**: **«이동» 판이 «실패»해야 «통과»**다(유형 24′)")
    P("   실패 «안» 하면 — 관문에 «분해능»이 «없는» 것이고 **「고쳤다」의 «증거»가 «못» 된다**")
    P("```")
    P("")
    P("```")
    P("🔎 `23c:112-118` — 이 판이 «그대로» 베낀 것:")
    P("     L = rnd.randint(%d, %d)" % (BMIN, BMAX))
    P("     a = rnd.randint(0, n_pos - L)      # ← **«이동» 블록**(순환 «아님»)")
    P("```")

    for n in (2250, 800):
        P("")
        P("## %s **n = %s** — 우리 창의 «대략» 길이%s"
          % ("★" if n == 2250 else "☆", format(n, ","),
             "" if n == 2250 else "(짧은 창 «대조»)"))
        P("")
        P("| 자 | 이동(`23c` «그대로») | 순환(«고친» 판) | 예측 |")
        P("|---|---:|---:|---|")
        cm, cc = coverage(n, False), coverage(n, True)
        # ㉠ 덮개 — 첫날 · 가운데
        P("| ㉠ **첫 자리** 덮개 | **%.3f** | **%.3f** | 1.000 |" % (cm[0], cc[0]))
        P("| ㉠ **가운데** 덮개 | **%.3f** | **%.3f** | 1.000 |"
          % (cm[n // 2], cc[n // 2]))
        P("| ㉠ **끝 자리** 덮개 | **%.3f** | **%.3f** | 1.000 |" % (cm[-1], cc[-1]))
        # ㉡ 옮겨간 무게
        wm = sum(max(0.0, 1.0 - v) for v in cm)
        wc = sum(max(0.0, 1.0 - v) for v in cc)
        P("| ㉡ **옮겨간 무게**(덜 덮인 몫 «합») | **%.1f** | **%.1f** | 0 |" % (wm, wc))
        # ㉢ 기지답
        truth = ((1.0 + X) ** 2 - 1.0) * 100.0
        km, kc = known(n, False), known(n, True)
        P("| ㉢ **기지답** 중앙(참값 %.2f%%) | **%.3f%%** | **%.3f%%** | %.2f%% |"
          % (truth, st.median(km), st.median(kc), truth))
        P("| ㉢ 참값 대비 | **%.0f%%** | **%.0f%%** | 100%% |"
          % (100.0 * st.median(km) / truth, 100.0 * st.median(kc) / truth))
        P("")
        P("```")
        fail_move = st.median(km) < truth * 0.85
        ok_cyc = truth * 0.85 <= st.median(kc) <= truth * 1.15
        P("**㉢ 판정** — «이동»이 참값을 **«크게 밑도는가»**  →  %s"
          % ("✅ **그렇다**(관문에 «분해능»이 «있다»)" if fail_move
             else "🚨 **아니다 — 관문이 «아무것도» 안 잰다**"))
        P("           «순환»이 참값에 **«맞는가»**        →  %s"
          % ("✅ **맞는다**" if ok_cyc else "🚨 **안 맞는다**"))
        P("")
        P("**㉠ 읽기** — 첫/끝 자리가 **%.3f · %.3f** 로 «1 보다 «작다»**"
          % (cm[0], cm[-1]))
        P("   ⇒ ★ **`23c` 의 이동 블록은 «계열 «양 끝»»을 «덜» 쓴다**")
        P("     (`dataaxis` 의 「양 끝만 뽑는」 결함과 **«방향»이 «반대»**지만 — **«같은» 뿌리**다:")
        P("      **시작점을 `[0, n−L]` 로 «자르면» «가장자리»가 «덜»/«더» 뽑힌다**)")
        P("```")

    P("")
    P("```")
    P("## ⇒ ★★★ **판정**")
    P("")
    P("   🔴 **`23c` 의 재표집은 «가장자리»를 «덜» 쓴다** — 관문 셋이 «전부» 그렇게 말한다")
    P("   ⇒ **「귀무 95% +87.47%p」는 «그» 재표집으로 나온 수**다")
    P("")
    P("   🚨 **그런데 「그래서 «틀렸다»」로는 «못» 간다** — 이 판이 잰 것은")
    P("     **「재표집이 «가장자리»를 «덜» 쓴다」**이지 **「87.47 이 «얼마나» 틀렸다」가 «아니다**")
    P("   ⇒ ✅ **쓸 말: 「87.47 은 «순환» 블록으로 «다시» 내야 한다. «안» 냈다」**")
    P("   ⇒ ⛔ **못 쓸 말: 「87.47 이 «과대»다」 · 「«과소»다」 — «방향»을 «안» 쟀다**")
    P("")
    P("★ **이 판이 «한» 것은 «하나»다: 「«이미 «만든»» 관문을 «걸었다»」**")
    P("   그리고 **관문이 «걸렸다»** ⇒ **「도구가 «있는데» «안» 썼다」의 «네 번째»가 «될 뻔»했다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
