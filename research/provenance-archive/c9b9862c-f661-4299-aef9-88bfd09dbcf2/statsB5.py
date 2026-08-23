# -*- coding: utf-8 -*-
import json,os,statistics as st
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=json.load(open(os.path.join(SP,'tradesB.json'),encoding='utf-8'))
print('전체: n=%d 승률=%.0f%% 평균순수익=%+.2f%% 중앙값=%+.2f%%'%(len(rows),
   sum(1 for r in rows if r['outcome']=='win')/len(rows)*100, st.mean([r['net'] for r in rows]), st.median([r['net'] for r in rows])))
z=[r for r in rows if r['score_prev']==0]
nz=[r for r in rows if r['score_prev']>0]
for lab,v in (('score=0(전일 8조건 중 하나 탈락)',z),('score>0',nz)):
    print('%s n=%d 승률=%.0f%% 평균=%+.2f%%'%(lab,len(v),sum(1 for r in v if r['outcome']=='win')/len(v)*100,st.mean([r['net'] for r in v])))
print(' score=0 목록:',[(r['name'],r['open_date'],r['net']) for r in z])
print()
# 초안 경계 검증 - prev
for lo,hi,lab in ((0,20,'🔴<20'),(20,50,'🟡20~50'),(50,101,'🟢≥50')):
    v=[r for r in rows if lo<=r['score_prev']<hi]
    print('%s n=%2d 승률=%.0f%% 평균=%+.2f%%'%(lab,len(v),sum(1 for r in v if r['outcome']=='win')/len(v)*100,st.mean([r['net'] for r in v])))
print()
print('보유일수 분포 - 패:',sorted(r['hold'] for r in rows if r['outcome']=='loss'))
print('손실건 중 net<=-4.5%%인 건수:',sum(1 for r in rows if r['net']<=-4.5), '/ 총 패', sum(1 for r in rows if r['outcome']=='loss'))
print('손실건 중 -4.5~-6%% (손절선 딱 맞음):',sum(1 for r in rows if -6.5<=r['net']<=-4.5))
