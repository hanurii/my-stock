# -*- coding: utf-8 -*-
import json, collections, statistics as st
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
rows=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E,h,l,c=p['entry_price'],p['h'],p['l'],p['c']; T,S=E*1.20,E*0.90; n=len(c)
        a1=a2=None
        for i in range(n):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: a1=((c[i]/E-1)*100,'loss','both',i); break
            if ht: a1=((c[i]/E-1)*100,'win','target',i); break
            if hs: a1=((c[i]/E-1)*100,'loss','stop',i); break
        if a1 is None: a1=((c[-1]/E-1)*100,None,'last',n-1)
        for i in range(n):
            if h[i]>=T: a2=((c[i]/E-1)*100,'win','target',i); break
        if a2 is None: a2=((c[-1]/E-1)*100,None,'last',n-1)
        rows.append({'a':(a1,a2,((c[-1]/E-1)*100,None,'last',n-1))})
    del d
def lab(v): return v[1] if v[1] else ('win' if v[0]>0 else 'loss')
def stats(rs,arm):
    nets=[net(r['a'][arm][0]) for r in rs]; labs=[lab(r['a'][arm]) for r in rs]
    w=[x for x,L in zip(nets,labs) if L=='win']; lo=[x for x,L in zip(nets,labs) if L!='win']
    wr=len(w)/len(nets)*100; be=abs(st.mean(lo))/(st.mean(w)+abs(st.mean(lo)))*100
    return len(nets),wr,be,wr-be,st.mean(nets)
print("== 여유 음수 분해 (①) — 옛 표본에서 한 단계씩 ==")
old=[r for r in rows if r['a'][0][2] in ('target','stop') and r['a'][0][3]>0]   # 당일접촉 제외·미결착 제외
print("  ㉮ 옛 표본(당일접촉 74 · 미결착 21 제외)   n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%"%stats(old,0))
plusm1=[r for r in rows if r['a'][0][2]!='last']
print("  ㉯ + M1 당일접촉 74건 편입                n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%"%stats(plusm1,0))
print("  ㉰ + 미결착 21건 편입 (=결과 파일 값)      n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%"%stats(rows,0))
print("  → M1 편입이 %+.2f%%p, 미결착 편입이 %+.2f%%p"
      %(stats(plusm1,0)[3]-stats(old,0)[3], stats(rows,0)[3]-stats(plusm1,0)[3]))
print("\n== 보유일과 시간당 수익 ==")
for nm,ix in (('①',0),('②',1),('③',2)):
    days=[r['a'][ix][3]+1 for r in rows]
    m=st.mean([net(r['a'][ix][0]) for r in rows])
    print("  %s 보유일 중앙 %3.0f · 평균 %5.1f  거래당 %+6.3f%%  거래일당 %+.4f%%"
          %(nm, st.median(days), st.mean(days), m, m/st.mean(days)))
