# -*- coding: utf-8 -*-
"""16번 본전 승률 산수 검산 — 사용자에게 갈 가장 중요한 한 줄."""
import json, statistics as st, collections
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
rows=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E=p['entry_price']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=(i,'loss'); break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=r
        rows.append({'y':p['entry_date'][:4],'net':net((c[i]/E-1)*100),'lab':lb})
    del d
print("M1 유니버스 %d건" % len(rows))
for tag, iswin in (("청산 사유(목표 도달)", lambda r: r['lab']=='win'),
                   ("순수익 > 0", lambda r: r['net']>0)):
    W=[r['net'] for r in rows if iswin(r)]; L=[r['net'] for r in rows if not iswin(r)]
    wr=100*len(W)/len(rows); mw=st.mean(W); ml=st.mean(L)
    be=abs(ml)/(mw+abs(ml))*100
    print("\n[%s]" % tag)
    print("   승률 %.2f%%  ·  이긴 거래 평균 %+.3f%%p  ·  진 거래 평균 %+.3f%%p" % (wr,mw,ml))
    print("   필요 본전 승률 = |%.3f| / (%.3f + |%.3f|) = **%.2f%%**" % (ml,mw,ml,be))
    print("   여유 = %.2f − %.2f = **%+.2f%%p**" % (wr,be,wr-be))
print("\n[비용 무시 값과 대조]  10/(20+10) = %.2f%%" % (10/(20+10)*100))
print("   → 비용 반영 본전이 그보다 %.2f%%p 높다" % (35.19-33.33))
print("\n[거래당 순수익] %+.4f%%" % st.mean(r['net'] for r in rows))
print("[연도별 거래당 순수익]")
g=collections.defaultdict(list)
for r in rows: g[r['y']].append(r['net'])
neg=0
for y in sorted(g):
    m=st.mean(g[y]); neg += m<0
    print("   %s  %+.3f%%  (n=%4d) %s" % (y,m,len(g[y]),"←마이너스" if m<0 else ""))
print("   → 6년 중 %d년 마이너스  (파일: 4년)" % neg)
