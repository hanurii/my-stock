import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
from canslim_lib import ohlcv_matrix
R=json.load(open(SP+'/H10v.json',encoding='utf-8'))
seen=set();first=[]
for x in sorted(R,key=lambda z:z['date']):
    if x['code'] in seen: continue
    seen.add(x['code']); first.append(x)
hi=[x for x in first if x['ext']>=150]
print('ext>=150 first-appearance stocks:',len(hi))
print('rec dates:',Counter(x['date'] for x in hi).most_common())
cache={}
def ser(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
# When did each touch -10%? calendar day of first touch
tdays=[]
for x in hi:
    s=ser(x['code']); ds=s['dates']; i=ds.index(x['date']); e=s['closes'][i]
    for k in range(i+1,i+11):
        if s['lows'][k]<=e*0.90: tdays.append((ds[k],x['name'],k-i)); break
print('\nfirst -10% touch calendar dates:')
for d,n,k in sorted(tdays): print(f'  {d}  day+{k:<2} {n}')
print('\ntouch-date histogram:',Counter(d for d,_,_ in tdays).most_common())
print('bars-to-touch median',np.median([k for _,_,k in tdays]))

# daily return correlation among the 24 during July
codes=[x['code'] for x in hi]
s0=ser(codes[0]); ds=s0['dates']
j0=ds.index('2026-07-01'); j1=ds.index('2026-08-08')
M=[]
for c in codes:
    s=ser(c); cl=np.array(s['closes'][j0:j1+1],float); M.append(np.diff(np.log(cl)))
M=np.array(M)
C=np.corrcoef(M)
iu=np.triu_indices(len(codes),1)
print('\nmean pairwise daily-return correlation among the 24 (Jul1-Aug8): %.3f'%C[iu].mean())
lo=[x for x in first if x['ext']<150]
codes2=[x['code'] for x in lo]
M2=[]
for c in codes2:
    s=ser(c); cl=np.array(s['closes'][j0:j1+1],float); M2.append(np.diff(np.log(cl)))
M2=np.array(M2); C2=np.corrcoef(M2); iu2=np.triu_indices(len(codes2),1)
print('mean pairwise corr among the 52 non-extended: %.3f'%C2[iu2].mean())
# effective n
def neff(n,rbar): return n/(1+(n-1)*max(rbar,0))
print('effective independent n for the 24: %.1f  (rbar=%.3f)'%(neff(24,C[iu].mean()),C[iu].mean()))
print('effective independent n for the 52: %.1f'%neff(52,C2[iu2].mean()))

# market context
import FinanceDataReader as fdr
try:
    k=fdr.DataReader('KS11','2026-06-25','2026-08-21')
    print('\nKOSPI 2026-07-01..08-08: start %.1f end %.1f  chg %.1f%%'%(k['Close'].iloc[0],k['Close'].iloc[-1],(k['Close'].iloc[-1]/k['Close'].iloc[0]-1)*100))
except Exception as e:
    print('fdr fail',e)
