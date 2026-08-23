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
variants={}
for basis in ['close','rec']:
  for meas in ['low','close']:
    for incl in [0,1]:   # incl=1 → include recommendation day itself in window
      key=(basis,meas,incl); res=[]
      for r in rows:
        s=ser(r['code'])
        if not s or r['date'] not in s['dates']: continue
        i=list(s['dates']).index(r['date']); j=i+10
        c=np.array(s['closes'],float); lo=np.array(s['lows'],float)
        if j>=len(c): continue
        base = c[i] if basis=='close' else r['rec_price']
        arr = lo if meas=='low' else c
        w=arr[i+1-incl:j+1]
        res.append(1 if (w.min()/base-1)*100 <= -10.0 else 0)
      variants[key]=(len(res),100*np.mean(res))
for k,v in variants.items(): print(k,'n=%d touch=%.1f%%'%v)
