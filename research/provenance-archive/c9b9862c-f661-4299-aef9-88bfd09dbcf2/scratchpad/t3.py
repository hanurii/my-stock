import json,os,numpy as np,sys,collections
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
A=json.load(open(os.path.join(SP,'an.json'),encoding='utf-8'))
D=[r for r in A if r['w10'] and r['vol'] is not None]
cache={}
def s_(c):
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    return cache[c]
bad=[]
for r in D:
    s=s_(r['code']); d=list(s['dates']); i=d.index(r['date'])
    raw=(s['closes'][i+10]/r['rec_price']-1)*100
    r['raw10']=raw
    r['gap_recclose']=(r['rec_price']/s['closes'][i]-1)*100
    if raw<-30: bad.append((r['name'],r['date'],round(raw,1),round(r['gap_recclose'],1),r['w10'][0],round(r['vol'],2)))
print('raw<-30 건수', len(bad))
for b in sorted(bad,key=lambda x:x[2])[:15]: print(' ',b)
print()
print('rec_price vs 당일종가 괴리 절대값 분포:', np.percentile([abs(r['gap_recclose']) for r in D],[50,90,99]).round(2))
print('괴리 >5%인 건:', sum(1 for r in D if abs(r['gap_recclose'])>5))
# check whether rule-return vs raw consistent
mism=[r for r in D if r['w10'][0]=='open' and abs(r['w10'][1]-r['raw10'])>0.01]
print('open인데 rule!=raw:', len(mism))
