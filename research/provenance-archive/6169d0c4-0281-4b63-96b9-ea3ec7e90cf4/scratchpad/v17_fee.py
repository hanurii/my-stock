# -*- coding: utf-8 -*-
"""(A) 수수료 산수 검산 — 현행 vs 우대."""
import json, statistics as st
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
# 현행: 매도 0.14%수수료+0.2%세금=0.34% · 매수 0.14%
cur  = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
# 우대: 수수료 0.0034%(양쪽) · 세금 0.2%(매도만)
pref = lambda g: ((1+g/100)*(1-0.002034)/(1+0.000034)-1)*100
rows=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E=p['entry_price']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=i; break
            if ht: r=i; break
            if hs: r=i; break
        if r is None: r=len(c)-1
        rows.append((c[r]/E-1)*100
                    )
    del d
print("M1 유니버스 %d건" % len(rows))
print("\n왕복 비용 산수")
print("  현행: 매도 0.34%% + 매수 0.14%% = 왕복 **0.48%%**  (곱셈 정확값 %.4f%%)"
      % (100*(1-(1-0.0034)/(1+0.0014))))
print("  우대: 매도 0.2034%% + 매수 0.0034%% = 왕복 **0.2068%%**  (곱셈 정확값 %.4f%%)"
      % (100*(1-(1-0.002034)/(1+0.000034))))
print("  → 절감 %.4f%%p" % (100*((1-(1-0.0034)/(1+0.0014))-(1-(1-0.002034)/(1+0.000034)))))
for lab,f,exp in (("현행",cur,"-0.0786 / 35.19 / -0.26"),("우대",pref,"+0.1950 / 34.50 / +0.65")):
    nets=[f(g) for g in rows]
    W=[x for x in nets if x>0]; L=[x for x in nets if x<=0]
    wr=100*len(W)/len(nets); mw=st.mean(W); ml=st.mean(L)
    be=abs(ml)/(mw+abs(ml))*100
    print("\n[%s]  (보고값 거래당/본전/여유 = %s)" % (lab,exp))
    print("   거래당 순수익 %+.4f%%" % st.mean(nets))
    print("   승률(순>0) %.2f%% · 이긴 평균 %+.4f · 진 평균 %+.4f" % (wr,mw,ml))
    print("   본전 %.2f%%  ·  여유 %+.4f%%p  ·  항등식 거래당/(W-L) %+.4f%%p"
          % (be, wr-be, st.mean(nets)/(mw-ml)*100))

print("\n=== 부호 반전의 통계적 의미 ===")
import math, random, collections
for lab,f in (("현행",cur),("우대",pref)):
    nets=[f(g) for g in rows]
    m=st.mean(nets); sd=st.pstdev(nets); se=sd/math.sqrt(len(nets))
    print("  %s 거래당 %+.4f%%  ·  SD %.2f%%p  ·  SE %.4f%%p  ·  95%% 구간 %+.4f ~ %+.4f  0포함=%s"
          % (lab,m,sd,se,m-1.96*se,m+1.96*se,(m-1.96*se)<0<(m+1.96*se)))
# 날 단위 블록 부트스트랩(자기상관 보존)
paths_day=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E=p['entry_price']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            if h[i]>=T or l[i]<=S: r=i; break
        if r is None: r=len(c)-1
        paths_day.append((p['entry_date'], (c[r]/E-1)*100))
    del d
byday=collections.defaultdict(list)
for dte,g in paths_day: byday[dte].append(g)
days=sorted(byday)
def boot(f,seed=170000,n=1000):
    rnd=random.Random(seed); out=[]
    for _ in range(n):
        s=[]
        while len(s)<len(days):
            L=rnd.randint(20,40); a=rnd.randint(0,max(0,len(days)-L)); s+=days[a:a+L]
        s=s[:len(days)]
        v=[f(g) for dd in s for g in byday[dd]]
        out.append(st.mean(v))
    out.sort(); return out[25], out[975]
for lab,f in (("현행",cur),("우대",pref)):
    lo,hi=boot(f)
    print("  %s 블록 부트스트랩 95%% %+.4f ~ %+.4f  0포함=%s" % (lab,lo,hi,lo<0<hi))
