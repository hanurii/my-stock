# -*- coding: utf-8 -*-
import json,os,statistics as st
from collections import Counter
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=json.load(open(os.path.join(SP,'tradesB.json'),encoding='utf-8'))
print('score_prev==0:',sum(1 for r in rows if r['score_prev']==0),'  <5:',sum(1 for r in rows if r['score_prev']<5))
print('tightest_prev:',Counter(r['tight_prev'] for r in rows).most_common())
print()
def band(s):
    if s<20: return 'A 0~20 (간당간당)'
    if s<50: return 'B 20~50 (보통)'
    return 'C 50~100 (안전)'
for key in ('score_prev','score_same'):
    print('===',key,'===')
    g={}
    for r in rows: g.setdefault(band(r[key]),[]).append(r)
    for b in sorted(g):
        v=g[b]; w=sum(1 for x in v if x['outcome']=='win')
        print(f'  {b}: n={len(v):2d} 승={w} 승률={w/len(v)*100:.0f}% 평균순수익={st.mean([x["net"] for x in v]):+.2f}% 중앙값={st.median([x["net"] for x in v]):+.2f}%')
    # finer deciles
    print('  --- 5구간 ---')
    g2={}
    for r in rows:
        s=r[key]
        k=min(int(s//20),4)
        g2.setdefault(k,[]).append(r)
    for k in sorted(g2):
        v=g2[k]; w=sum(1 for x in v if x['outcome']=='win')
        print(f'   {k*20}~{k*20+20}: n={len(v):2d} 승률={w/len(v)*100:.0f}% 평균={st.mean([x["net"] for x in v]):+.2f}%')
    print()
# median split
for key in ('score_prev','score_same'):
    med=st.median([r[key] for r in rows])
    lo=[r for r in rows if r[key]<=med]; hi=[r for r in rows if r[key]>med]
    print(key,'median',round(med,1))
    for lab,v in (('하위',lo),('상위',hi)):
        w=sum(1 for x in v if x['outcome']=='win')
        print(f'  {lab} n={len(v)} 승률={w/len(v)*100:.0f}% 평균={st.mean([x["net"] for x in v]):+.2f}%')
print()
# correlation score vs net
def pearson(x,y):
    mx,my=st.mean(x),st.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    den=(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**0.5
    return num/den if den else 0
def spearman(x,y):
    def rank(v):
        s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v); i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
            avg=(i+j)/2+1
            for k in range(i,j+1): r[s[k]]=avg
            i=j+1
        return r
    return pearson(rank(x),rank(y))
for key in ('score_prev','score_same'):
    x=[r[key] for r in rows]; y=[r['net'] for r in rows]
    print(key,'pearson r=%.3f spearman=%.3f'%(pearson(x,y),spearman(x,y)))
