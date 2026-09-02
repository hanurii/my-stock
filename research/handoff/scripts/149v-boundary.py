# -*- coding: utf-8 -*-
"""검증 세션 — 149a 선행계산 반론.  «필요 R» 의 경계가 «어디»인지, 그리고
   「앞 통과」와 「뒤에서 확인 가능」이 «같은 선»인지를 잰다.  뒤 구간 안 봄."""
from math import sqrt, erf

def Phi(z): return 0.5*(1.0+erf(z/sqrt(2.0)))

Z_OBS   = 1.826160     # 148 자A +20 (앞)
THR_FRONT = 2.985582   # 148 앞 문턱 (max-T + Bonferroni N=9)
C_CI    = 1.645        # 앞 «신뢰구간» 상수 (단측 95%) — 뒤의 z95 와 «다른 것»
R_AVAIL = (1.15, 1.81) # 조사 세션이 낸 뒤/앞 크기비
N_FRONT_DAYS = 348

def need_R(z, z95=1.645, power=0.50):
    """뒤 구간이 앞의 몇 배여야 검출력 `power` 가 나오나."""
    th = z - C_CI                       # 앞 효과의 단측 95% 하한 (z 단위)
    if th <= 0: return float("inf")
    from math import log
    # power = Phi(th*sqrt(R) - z95)  →  th*sqrt(R) = z95 + Phinv(power)
    add = 0.0 if abs(power-0.5)<1e-9 else (0.8416 if abs(power-0.8)<1e-9 else None)
    assert add is not None
    return ((z95+add)/th)**2

print("="*78)
print("① 필요 R 이 «1.81 이하»가 되는 앞 구간 z 는 얼마인가  ← 이게 진짜 경계선")
print("="*78)
for r in (1.00, 1.15, 1.81, 3.00):
    z_star = C_CI + 1.645/sqrt(r)
    print("  뒤가 앞의 %.2f배라면  →  앞 구간 z 가 **%.4f 이상**이어야 뒤에서 확인 가능" % (r, z_star))
print()
z_star_max = C_CI + 1.645/sqrt(R_AVAIL[1])
print("  ⇒ 있는 자료(R=1.81)로 확인 가능한 «최소» 앞 z = **%.4f**" % z_star_max)
print("  ⇒ 148 의 앞 문턱               = **%.4f**   (차이 %+.4f = %.1f%%)"
      % (THR_FRONT, THR_FRONT-z_star_max, 100*(THR_FRONT-z_star_max)/z_star_max))
print("  ⇒ 148 의 관측                  = **%.4f**   (경계보다 %+.4f **아래**)" % (Z_OBS, Z_OBS-z_star_max))
print()
print("  ★★ **「앞 문턱을 넘는다」와 「뒤에서 확인할 수 있다」가 «4% 안»에서 같은 선이다.**")
print("     ⇒ 두뇌 세션의 ㉯(「앞 통과는 필요조건이 아니다」)는 «형식적으로» 맞지만")
print("       **N=9 인 이 판에서는 두 기준이 «사실상 같은 선»이라 실익이 없다**")
print("     ⚠️ 단 이건 «N=9 에서의 수치적 일치»다 — N=3 이었다면 문턱 2.4 → 필요 R=4.7 로 «어긋난다»")

print()
print("="*78)
print("② 규약을 «전부» 계산하고 «가장 엄한» 것을 쓴다 (유형 42)")
print("="*78)
rows = [("(가) 두뇌가 «쓴» 그대로 · 검출력 50%", need_R(Z_OBS, 1.645, 0.50)),
        ("(다) 검출력 80%",                      need_R(Z_OBS, 1.645, 0.80)),
        ("     z95 를 폭 위끝 1.83 으로",         need_R(Z_OBS, 1.83, 0.50)),
        ("     z95 를 폭 아래끝 1.55 로",         need_R(Z_OBS, 1.55, 0.50))]
for lab, r in rows:
    short = r / R_AVAIL[1]
    print("  %-38s 필요 R = %8.2f배   →  있는 것의 **%.0f배**가 더 필요" % (lab, r, short))
print()
print("  ⇒ **가장 엄한 것(검출력 80%)을 써도, 가장 무른 것(z95=1.55)을 써도 «40배 이상» 모자란다**")
print("  ⇒ 조사 세션 §2·§5 의 «안 정한 것»들은 판정을 «못 바꾼다»")

print()
print("="*78)
print("③ 유형 1 짝규칙 — 「넘으려면 무엇이 «얼마»여야 하나」")
print("="*78)
r = need_R(Z_OBS)
print("  뒤 구간 체결일이 앞의 **%.1f배** 여야 한다" % r)
print("  앞이 %d일 이므로  →  뒤가 **%.0f 거래일 = 약 %.0f년**" % (N_FRONT_DAYS, N_FRONT_DAYS*r, N_FRONT_DAYS*r/252))
print("  ⇒ **자료가 낸 적 없는 크기다. 이 문턱은 «장식이 아니라» 닫힘이다**")
print()
print("  ★ 조사 세션 §3(날당 분산이 다를 수 있다)이 판정을 뒤집으려면:")
print("     R_유효 = R_날수 x (앞분산/뒤분산) >= %.2f  이고 R_날수=1.81 이므로" % r)
print("     → 뒤 구간의 «날당 표준편차»가 앞의 **1/%.2f = %.2f배**여야 한다"
      % (sqrt(r/R_AVAIL[1]), 1/sqrt(r/R_AVAIL[1])))
print("     ⇒ **못 잰 것은 맞지만, 46배를 메울 크기가 «아니다»**")
