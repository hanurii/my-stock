import json, os, sys, statistics as st, collections
import numpy as np
from scipy import stats
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SCR=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
store=json.load(open(os.path.join(SCR,'percond.json'),encoding='utf-8'))
led=json.load(open('public/data/sepa-buy-rec-ledger.json',encoding='utf-8'))['entries']
H=10; rows=[]; cache={}
for e in led:
    m=store.get(e['date'],{}).get(e['code'])
    if not m: continue
    if e['code'] not in cache:
        try: cache[e['code']]=ohlcv_matrix.get_series(e['code'])
        except Exception: cache[e['code']]=None
    s=cache[e['code']]
    if not s: continue
    try: i=s['dates'].index(e['date'])
    except ValueError: continue
    if i+H>=len(s['dates']): continue
    p0=e['rec_price']; w=slice(i+1,i+1+H)
    rows.append({'date':e['date'],'code':e['code'],'m6':m['margin']['6']+30,'gm':m['score'],
      'hit':1 if (min(s['lows'][w])/p0-1)*100<=-10 else 0,'r':(s['closes'][w][-1]/p0-1)*100})
print('[날짜층화 · m6>=150 vs <150 · 고정10일]')
d=[]
for dt in sorted(set(r['date'] for r in rows)):
    g=[r for r in rows if r['date']==dt]
    hi=[r for r in g if r['m6']>=150]; lo=[r for r in g if r['m6']<150]
    if not hi or not lo: continue
    d.append(np.mean([r['hit'] for r in hi])-np.mean([r['hit'] for r in lo]))
pos=sum(1 for x in d if x>0); nz=sum(1 for x in d if x!=0)
print('  비교가능 날짜 %d | 평균차 %+.1f%%p | 확장군이 더 나쁜 날 %d/%d | 부호검정 p=%.4f'%(len(d),100*np.mean(d),pos,nz,stats.binomtest(pos,nz).pvalue))
print('\n[날짜층화 · gm 상위절반 vs 하위절반 · 고정10일] (재확인)')
d2=[]
for dt in sorted(set(r['date'] for r in rows)):
    g=[r for r in rows if r['date']==dt]
    if len(g)<4: continue
    mm=np.median([r['gm'] for r in g]); hi=[r for r in g if r['gm']>=mm]; lo=[r for r in g if r['gm']<mm]
    if not hi or not lo: continue
    d2.append(np.mean([r['hit'] for r in hi])-np.mean([r['hit'] for r in lo]))
pos=sum(1 for x in d2 if x>0); nz=sum(1 for x in d2 if x!=0)
print('  날짜 %d | 평균차 %+.1f%%p | 부호검정 p=%.4f'%(len(d2),100*np.mean(d2),stats.binomtest(pos,nz).pvalue))
