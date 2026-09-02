# -*- coding: utf-8 -*-
"""150 결산표 검증 + 149 의 「N=1」이 129 때문에 흔들릴 때의 영향."""
from math import sqrt, log, exp, erf
def Phi(z): return 0.5*(1.0+erf(z/sqrt(2.0)))
def Phinv(p):
    lo,hi=-12.,12.
    for _ in range(300):
        m=(lo+hi)/2
        if Phi(m)<p: lo=m
        else: hi=m
    return (lo+hi)/2

Y, P0 = 27.4, 1000.0
def ann(total): return (total/P0)**(1.0/Y) - 1.0

print("="*78); print("A. 🚨 「QQQ+이동평균」은 «벤치마크»가 아니라 «칸 중 최선»이다"); print("="*78)
rows=[("우리 현행",9280),("QQQ+**200**일선",9412),("QQQ 그냥 보유",None),
      ("QQQ+**250**일선",13339),("스캔 최선(20칸)",12908)]
QQQ_ANN = 0.0970
for lab,t in rows:
    a = QQQ_ANN if t is None else ann(t)
    print("  %-22s  연 **%+.2f%%**%s" % (lab, 100*a, "   (총액 %s만)"%f"{t:,}" if t else "   (129 인용)"))
g_ma  = ann(13339)-ann(9412)
g_ours= ann(9412)-ann(9280)
print()
print("  🚨 이동평균 «칸 하나»(200↔250) 폭    = **%.2f%%p**" % (100*g_ma))
print("  🚨 우리 vs QQQ+200일선 차이           = **%.2f%%p**" % (100*g_ours))
print("  ⇒ **칸 폭이 «차이»의 %.0f배**. 「QQQ+250일선」은 «자유 파라미터 1개를 최적화한 값»이다" % (g_ma/g_ours))
print("  ⇒ **파라미터 0 개인 벤치마크는 «QQQ 그냥 보유» 하나뿐**  →  우리 %.2f vs 9.70 = **−1.23%%p**"
      % (100*ann(9280)))

print(); print("="*78); print("B. 🚨 「우리가 SPY 를 이겼다(8.47 vs 7.74)」는 «적을 수 없다»"); print("="*78)
spy=7.74
for dy,lab in ((0.0,"배당 «미포함»이면"),(1.5,"SPY 배당 1.5%/년 넣으면"),(1.8,"1.8%/년 넣으면")):
    v=spy+dy
    print("  %-26s SPY 연 %.2f%%  →  우리 8.47%% 가 %s" % (lab, v, "**이긴다**" if 8.47>v else "**진다**"))
print("  ⇒ **배당 처리를 모르면 부호가 뒤집힌다 → 「못 확인」이 아니라 «비교 불가»가 맞다**")
print("  ⇒ 반면 QQQ 비교는 «이미 지고» 배당을 넣으면 «더» 지므로  →  「못 확인, 방향은 우리에게 불리」로 충분")
print("  🚨 그리고 프로젝트 안에 «다른 규약»이 이미 있다 — 표본밖 판에서 SPY 를 «배당 포함 7.04%»로 씀")

print(); print("="*78); print("C. 129 가 뒤 구간을 이미 열었다면 149 의 수는?"); print("="*78)
Z_OBS, C_CI = 1.826160, 1.645
for n,lab in ((1,"㉠ 물음이 다르다 → 계열 분리 (N=1)"),(2,"㉡ 같은 자료다 → N=2 (Bonferroni)")):
    z95 = Phinv(1.0-0.05/n)
    R   = (z95/(Z_OBS-C_CI))**2
    print("  %-34s  z95 = **%.4f**  →  필요 R = **%7.2f배**  (있는 것 1.81)" % (lab, z95, R))
print("  ⇒ **㉠·㉡ 둘 다 «한참» 미통과. 갈릴 필요가 없다** → 유형 42: 둘 다 적고 «엄한 쪽»을 쓴다")
print("  ⇒ 그리고 «엄한 쪽»(㉡)이 조사 세션에게 «불리»한 쪽이다 — 그래서 ㉠ 로 기운 것을 «안 믿는» 게 맞다")
