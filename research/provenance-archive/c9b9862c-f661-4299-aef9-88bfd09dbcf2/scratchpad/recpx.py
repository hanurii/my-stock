import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
from canslim_lib import ohlcv_matrix
J=json.load(open(SP+'/joined.json',encoding='utf-8'))
cache={}
def ser(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
def build(H,use_rec):
    rows=[]
    for r in J:
        s=ser(r['code'])
        if not s: continue
        ds=s['dates']
        try: i=ds.index(r['date'])
        except ValueError: continue
        if i+H>=len(ds): continue
        entry = r['rec_price'] if use_rec else s['closes'][i]
        if not entry or entry<=0: continue
        lows=s['lows'][i+1:i+1+H]
        if len(lows)<H: continue
        rows.append(dict(code=r['code'],name=r['name'],score=r['score'],
                         touch=1 if min(lows)<=entry*0.90 else 0))
    return rows
def band(s): return '<20' if s<20 else ('20-50' if s<50 else '>=50')
for lab,ur in [('entry = rec-day CLOSE (correct)',False),('entry = ledger rec_price (basis-mismatched)',True)]:
    R=build(10,ur)
    print(f'--- {lab}: n={len(R)} overall touch={np.mean([x["touch"] for x in R])*100:.1f}%')
    for b in ['<20','20-50','>=50']:
        g=[x for x in R if band(x['score'])==b]
        print(f'    {b}: n={len(g)} touch={np.mean([x["touch"] for x in g])*100:.1f}%')
    print('    score~touch rho=%+.3f p=%.4g'%st.spearmanr([x['score'] for x in R],[x['touch'] for x in R]))
    g=[x for x in R if x['code']=='036800']
    print(f'    036800 나이스정보통신 rows={len(g)} touch={np.mean([x["touch"] for x in g])*100:.0f}%  scores={sorted(round(x["score"],1) for x in g)}')
