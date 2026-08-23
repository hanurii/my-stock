import json,os,sys,numpy as np
from collections import Counter
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
from canslim_lib import ohlcv_matrix
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
R=json.load(open(SP+'/H10.json',encoding='utf-8'))
codes={}
for x in R: codes.setdefault(x['code'],x['name'])
print('codes in H10:',len(codes))
print('\n=== daily moves beyond Korean +-30% limit (rebase suspects) ===')
susp={}
for c,n in codes.items():
    s=ohlcv_matrix.get_series(c)
    ds=s['dates']; cl=np.array(s['closes'],dtype=float)
    # restrict to last 400 bars (covers 52w lookback + window)
    lo=max(0,len(cl)-400)
    r=cl[lo+1:]/cl[lo:-1]-1
    idx=np.where(np.abs(r)>0.32)[0]
    if len(idx):
        susp[c]=[(ds[lo+1+i], round(float(r[i])*100,1)) for i in idx]
        print(f'  {c} {n:<14} {susp[c][:5]}')
print('suspect codes:',len(susp),'/',len(codes))

# is 나이스정보통신 window contaminated?
s=ohlcv_matrix.get_series('036800'); ds=s['dates']
i=ds.index('2026-07-01')
print('\n036800 나이스정보통신 closes 2026-06-25..2026-08-05:')
j=ds.index('2026-06-25')
print([(ds[k],s['closes'][k]) for k in range(j,min(j+30,len(ds)))])
