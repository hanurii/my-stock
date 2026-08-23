import pickle,os,sys,json
sys.path.insert(0,r'C:\Users\hanul\playground\my-stock\scripts')
os.chdir(r'C:\Users\hanul\playground\my-stock')
from canslim_lib import ohlcv_matrix
import numpy as np
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=pickle.load(open(os.path.join(SP,'rows.pkl'),'rb'))
cache={}
def ser(code):
    if code not in cache:
        try: cache[code]=ohlcv_matrix.get_series(code)
        except Exception as e: cache[code]=None
    return cache[code]
H=[5,10,20,30]
out=[]
nprice=0; pricediff=[]
for r in rows:
    s=ser(r['code'])
    if not s: continue
    dates=list(s['dates']); 
    if r['date'] not in dates: continue
    i=dates.index(r['date'])
    closes=np.array(s['closes'],dtype=float); lows=np.array(s['lows'],dtype=float); highs=np.array(s['highs'],dtype=float)
    base=closes[i]
    if base and r['rec_price']: pricediff.append((r['rec_price']/base-1)*100)
    rec=dict(r); rec['base']=base
    for h in H:
        j=i+h
        if j>=len(closes): rec[f'touch{h}']=None; rec[f'ret{h}']=None; rec[f'mfe{h}']=None; continue
        w_low=lows[i+1:j+1]; w_high=highs[i+1:j+1]
        rec[f'touch{h}']= 1 if (w_low.min()/base-1)*100 <= -10.0 else 0
        rec[f'ret{h}']=(closes[j]/base-1)*100
        rec[f'mfe{h}']=(w_high.max()/base-1)*100
    out.append(rec)
pd=np.array(pricediff)
print('rows with ohlcv',len(out),'rec_price vs close median diff %.4f%%'%np.median(pd))
for h in H:
    v=[r for r in out if r.get(f'touch{h}') is not None]
    print('H=%d n=%d uniq=%d touch=%.1f%%'%(h,len(v),len(set(r['code'] for r in v)),100*np.mean([r[f'touch{h}'] for r in v])))
pickle.dump(out,open(os.path.join(SP,'fw.pkl'),'wb'))
