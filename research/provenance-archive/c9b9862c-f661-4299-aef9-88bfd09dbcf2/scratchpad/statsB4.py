# -*- coding: utf-8 -*-
import json,os,math,statistics as st
from collections import Counter
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=json.load(open(os.path.join(SP,'tradesB.json'),encoding='utf-8'))
led=json.load(open(os.path.join(SP,'ledgerB.json'),encoding='utf-8'))
def mw(x,y):
    allv=sorted([(v,0) for v in x]+[(v,1) for v in y],key=lambda t:t[0])
    rk=[0]*len(allv); i=0
    while i<len(allv):
        j=i
        while j+1<len(allv) and allv[j+1][0]==allv[i][0]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): rk[k]=avg
        i=j+1
    n1,n2=len(x),len(y)
    R1=sum(rk[k] for k in range(len(allv)) if allv[k][1]==0)
    U1=R1-n1*(n1+1)/2
    U=min(U1,n1*n2-U1); mu=n1*n2/2
    cnt=Counter(v for v,_ in allv); N=n1+n2
    tie=sum(t**3-t for t in cnt.values())
    sd=(n1*n2/12*((N+1)-tie/(N*(N-1))))**0.5
    z=(U-mu+0.5)/sd if sd else 0
    return U1/(n1*n2), z, math.erfc(abs(z)/math.sqrt(2))
closed=[x for x in led if x['outcome'] in ('target','stop')]
for key in ('sp','ss'):
    a=[x[key] for x in closed if x['outcome']=='target']; b=[x[key] for x in closed if x['outcome']=='stop']
    auc,z,p=mw(a,b)
    print(f'원장 {key}: AUC(target>stop)={auc:.3f} z={z:.2f} p={p:.4f}  n={len(a)}/{len(b)}')
print()
# real trades subsets
def summarize(v,label,key='score_prev'):
    if not v: return
    w=[x for x in v if x['outcome']=='win']; l=[x for x in v if x['outcome']=='loss']
    if not w or not l:
        print(f'{label}: n={len(v)} 승={len(w)} (검정불가)'); return
    auc,z,p=mw([x[key] for x in w],[x[key] for x in l])
    print(f'{label}: n={len(v)} 승률={len(w)/len(v)*100:.0f}% 승중앙={st.median([x[key] for x in w]):.1f} 패중앙={st.median([x[key] for x in l]):.1f} AUC={auc:.3f} p={p:.3f}')
summarize(rows,'전체 63건')
summarize([r for r in rows if r['open_date'] not in ('2026-08-18','2026-08-19')],'8/18~19 폭락 제외')
summarize([r for r in rows if r['open_date']<'2026-08-01'],'7월 매수')
summarize([r for r in rows if r['open_date']>='2026-08-01'],'8월 매수')
summarize([r for r in rows if r['setup']=='VCP'],'VCP')
summarize([r for r in rows if r['setup']=='3C'],'3C')
print()
# per-condition margin (pct) vs outcome, real trades
labels={'1':'①150·200선','2':'②150>200','3':'③200선상승','4':'④50선정렬','5':'⑤50일선','6':'⑥52주저가','7':'⑦52주고가','8':'⑧RS'}
print('조건별 여유율(prev) 승 vs 패 중앙값:')
for k in '12345678':
    w=[r['per_prev'][k]['pct'] for r in rows if r['outcome']=='win']
    l=[r['per_prev'][k]['pct'] for r in rows if r['outcome']=='loss']
    auc,z,p=mw(w,l)
    print(f"  {labels[k]:<10} 승={st.median(w):5.1f} 패={st.median(l):5.1f} AUC={auc:.3f} p={p:.3f}")
print()
print('⑦ 52주고가 실제 이격(%) 승 vs 패:')
w=[r['per_prev']['7']['margin']-25 for r in rows if r['outcome']=='win']
l=[r['per_prev']['7']['margin']-25 for r in rows if r['outcome']=='loss']
print('  승 중앙 %.1f%% 패 중앙 %.1f%%'%(st.median(w),st.median(l)))
