import json, os, sys
import numpy as np
from collections import defaultdict, Counter
from scipy import stats as st
sys.path.insert(0,'scripts')
os.chdir('C:/Users/hanul/playground/my-stock')
from canslim_lib import ohlcv_matrix
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
J=json.load(open(SP+'/joined.json',encoding='utf-8'))
cache={}
def ser(code):
    if code not in cache:
        try: cache[code]=ohlcv_matrix.get_series(code)
        except Exception: cache[code]=None
    return cache[code]

def build(H):
    rows=[]
    for r in J:
        s=ser(r['code'])
        if not s: continue
        ds=s['dates']
        try: i=ds.index(r['date'])
        except ValueError: continue
        if i+H >= len(ds): continue      # need H full bars AFTER rec day
        entry=s['closes'][i]             # buy at rec-day close
        if not entry or entry<=0: continue
        lows=s['lows'][i+1:i+1+H]; cl=s['closes'][i+1:i+1+H]
        if len(cl)<H: continue
        touch = 1 if min(lows) <= entry*0.90 else 0
        ret = (cl[-1]/entry-1)*100
        mfe = (max(s['highs'][i+1:i+1+H])/entry-1)*100
        low52=r['low52']; ext = (entry/low52-1)*100 if low52 else None
        rows.append(dict(code=r['code'],name=r['name'],date=r['date'],score=r['score'],
                         tightest=r['tightest'],touch=touch,ret=ret,mfe=mfe,ext=ext,
                         rs=r['rs_a'],ret252=r['ret252'],entry=entry,rec=r['rec_price'],
                         high52=r['high52']))
    return rows

# rec_price vs close sanity
R10=build(10)
d=[abs(x['rec']/x['entry']-1)*100 for x in R10 if x['rec']]
print('n H=10',len(R10),'unique codes',len(set(x["code"] for x in R10)))
print('rec_price vs close: median diff %.4f%% , max %.3f%%, >1%% count %d'%(np.median(d),max(d),sum(1 for v in d if v>1)))
json.dump(R10,open(SP+'/H10.json','w',encoding='utf-8'),ensure_ascii=False)

def band(s): return '<20' if s<20 else ('20-50' if s<50 else '>=50')
def ci(k,n):
    lo,hi=st.beta.ppf(0.025,k,n-k+1) if k>0 else (0,0), None
    from statsmodels.stats.proportion import proportion_confint
    return proportion_confint(k,n,method='wilson')

for H in [5,10,20,30]:
    R=build(H)
    sc=np.array([x['score'] for x in R]); tc=np.array([x['touch'] for x in R]); rt=np.array([x['ret'] for x in R])
    rho,p=st.spearmanr(sc,tc)
    print(f'\n=== H={H} n={len(R)} codes={len(set(x["code"] for x in R))} touch={tc.mean()*100:.1f}% | score~touch rho={rho:+.3f} p={p:.4f}')
    tab=defaultdict(lambda:[0,0,[]])
    for x in R:
        b=band(x['score']); tab[b][0]+=1; tab[b][1]+=x['touch']; tab[b][2].append(x['ret'])
    obs=[]
    for b in ['<20','20-50','>=50']:
        n,k,rr=tab[b]; obs.append([k,n-k])
        print(f'  {b}: n={n} touch={k/n*100:.1f}% med_ret={np.median(rr):+.2f}%')
    chi2,pp,_,_=st.chi2_contingency(np.array(obs)); print('  chi2 p=%.4f'%pp)
    kw=st.kruskal(*[tab[b][2] for b in ['<20','20-50','>=50']]); print('  kruskal ret p=%.4f'%kw.pvalue)
