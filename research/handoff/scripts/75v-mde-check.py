# -*- coding: utf-8 -*-
"""75v — 두뇌 세션의 「필요 연수」 식 `T > (hw/|L|)²` 를 **독립으로** 검산한다.

🚨 `75a-mde.py` 를 읽지 «않고» 사양(메시지에 적힌 두 줄)만 보고 다시 세웠다.
   ① 효과는 «누적»이라 창을 T 배 늘리면 T 배
   ② 폭은 블록 수가 T 배라 √T 배
   → 0 배제 조건  T·|L| > √T·hw  ⟺  **T > (hw/|L|)²**   (전부 «로그» 단위)

검산 둘
-------
(가) 두뇌 세션이 낸 「필요 배수」가 로그 단위로 재현되는가
(나) `hw` 를 «폭의 절반» 대신 **「점추정 → 가까운 쪽 경계」 거리**로 바꾸면 어떻게 되는가
     — 부트스트랩 중앙이 구간 «가운데»에 있지 않으면 둘이 갈린다. 경계 칸에서 갈린다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/75v-mde-check.py
"""
from __future__ import annotations

import math

YEARS = 9.0        # 미국 창 2017-09 ~ 2026-08


def lg(pct):
    """% 총수익 → 로그 단위."""
    return math.log(1.0 + pct / 100.0)


# 두뇌 세션이 보낸 표 — (이름, 관측 효과%, 두뇌 세션 필요 효과%, 두뇌 세션 필요 배수)
ROWS = (
    ("H − P0",                    -65.01, 173.59, 0.9),
    ("H′ − P0",                   -40.74, 179.04, 3.8),
    ("H-avgstop − P0",            -23.74, 143.59, 10.8),
    ("H′-avgstop − P0",            -2.02, 106.33, 1254.0),
    ("H′-avgstop − P0(0.16)",      22.64,  89.91, 9.9),
    ("★ H-avgstop − H  손절축",    102.38, 133.10, 1.4),
    ("H′-avgstop − H′  손절축",     56.08, 122.96, 3.2),
)

# 구간을 아는 칸만 — (이름, 관측%, 하단%, 상단%)  두뇌 세션이 보낸 값
INTERVALS = (
    ("H − P0 (블록 20)",            -65.01, -85.45,   0.96),
    ("H-avgstop − H (블록 20)",     102.38, -12.93, 373.07),
    ("H′-avgstop − H′ (블록 20)",    56.08, -36.33, 216.51),
    ("H′-avgstop − P0(0.16) 블록20",  22.64, -33.89, 138.45),
)


def main() -> int:
    print("=" * 92)
    print("75v — 「필요 연수」 식 독립 검산")
    print("=" * 92)
    print("(가) 로그 단위로 두뇌 세션의 «필요 배수»가 재현되는가")
    print("     T = (ln(1+필요/100) / |ln(1+관측/100)|)²")
    print()
    print("  %-26s %10s %10s %10s %10s" % ("비교", "두뇌 배수", "내 배수", "차", "판정"))
    worst = 0.0
    for nm, obs, need, mult in ROWS:
        t = (lg(need) / abs(lg(obs))) ** 2
        d = abs(t - mult) / max(1e-12, mult)
        worst = max(worst, d)
        print("  %-26s %10.1f %10.2f %9.1f%% %10s"
              % (nm, mult, t, 100 * d, "일치" if d < 0.05 else "**어긋남**"))
    print()
    print("  → 최대 상대 편차 %.2f%%  ⇒  **식과 로그 단위 사용은 재현된다**" % (100 * worst))

    print()
    print("(나) 🚨 `hw` 를 «가까운 쪽 경계까지의 거리»로 바꾸면")
    print("     — 구간이 로그 축에서도 «중앙에 대칭»이 아니면 둘이 갈린다")
    print()
    print("  %-30s %9s %9s %9s %9s"
          % ("비교", "폭절반T", "가까운쪽T", "필요연수", "지금 0"))
    for nm, obs, lo, hi in INTERVALS:
        L = lg(obs)
        a_lo, a_hi = lg(lo), lg(hi)
        hw = (a_hi - a_lo) / 2.0                       # 두뇌 세션 방식
        # 🚨 0 이 «어느 쪽»에 있나 — 효과가 음수면 0 은 «위», 양수면 «아래»에 있다.
        #    min() 을 쓰면 반대쪽 경계를 잡는다(내가 처음에 그렇게 틀렸다).
        near = abs(L - a_hi) if L < 0 else abs(L - a_lo)
        t_hw = (hw / abs(L)) ** 2
        t_near = (near / abs(L)) ** 2
        print("  %-30s %9.2f %9.2f %9.1f %9s"
              % (nm, t_hw, t_near, t_near * YEARS,
                 "배제" if (a_lo > 0 or a_hi < 0) else "포함"))
    print()
    print("  ★ 두 T 가 갈리는 폭이 곧 «중앙이 구간 가운데에서 벗어난 정도»다.")
    print("    경계 칸(= 필요 배수 ≈ 1)에서만 결론이 달라진다 — 그게 「H − P0」다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
