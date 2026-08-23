import pickle,os,sys
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
        except Exception: cache[code]=None
    return cache[code]
out=[];diffs=[]
for r in rows:
    s=ser(r['code'])
    if not s or r['date'] not in s['dates']: continue
    i=list(s['dates']).index(r['date'])
    c=np.array(s['closes'],float); lo=np.array(s['lows'],float); hi=np.array(s['highs'],float)
    base=r['rec_price'] or c[i]
    diffs.append((r['rec_price']/c[i]-1)*100)
    rec=dict(r); rec['base']=base; rec['close_i']=c[i]
    # expansion vs 52w low  (as-of, from candidates file)
    rec['exp']= (base/r['low52']-1)*100 if r['low52'] else None
    for h in (5,10,20,30):
        j=i+h
        if j>=len(c):
            rec[f't{h}']=None; rec[f'r{h}']=None; continue
        rec[f't{h}']=1 if (lo[i+1:j+1].min()/base-1)*100<=-10.0 else 0
        rec[f'r{h}']=(c[j]/base-1)*100
    out.append(rec)
d=np.array(diffs)
print('n',len(out),'rec/close diff: median %.4f  p90 %.3f  max %.3f  |>1%%| count %d'%(np.median(d),np.percentile(np.abs(d),90),np.max(np.abs(d)),int((np.abs(d)>1).sum())))
pickle.dump(out,open(os.path.join(SP,'fw3.pkl'),'wb'))
