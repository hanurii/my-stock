import json,os,sys,numpy as np
from collections import Counter,defaultdict
from scipy import stats as st
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
from canslim_lib import ohlcv_matrix
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
R=json.load(open(SP+'/H10.json',encoding='utf-8'))
cache={}
def ser(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
print('=== zero-volume bars inside the 10-day window ===')
bad=defaultdict(int); rowsbad=0
for x in R:
    s=ser(x['code']); ds=s['dates']; i=ds.index(x['date'])
    v=s['volumes'][i+1:i+11]
    z=sum(1 for q in v if not q or q==0)
    if z>0:
        bad[(x['code'],x['name'])]+=1; rowsbad+=1
        x['zerovol']=z
    else: x['zerovol']=0
print('rows with >=1 zero-volume bar:',rowsbad,'/',len(R))
for k,v in sorted(bad.items(),key=lambda t:-t[1]): print('  ',k,v,'rows')

def band(s): return '<20' if s<20 else ('20-50' if s<50 else '>=50')
print('\n=== H=10 touch rate, with vs without halted-window rows ===')
for lab,sub in [('ALL',R),('clean (no zero-vol bar)',[x for x in R if x['zerovol']==0])]:
    tab=defaultdict(lambda:[0,0,[]])
    for x in sub:
        b=band(x['score']); tab[b][0]+=1; tab[b][1]+=x['touch']; tab[b][2].append(x['ret'])
    obs=[]
    print(f'-- {lab}: n={len(sub)} codes={len(set(x["code"] for x in sub))}')
    for b in ['<20','20-50','>=50']:
        n,k,rr=tab[b]; obs.append([k,n-k])
        print(f'   {b}: n={n} touch={k/n*100:.1f}% med_ret={np.median(rr):+.2f}%')
    chi2,pp,_,_=st.chi2_contingency(np.array(obs)); print('   chi2 p=%.4g'%pp)
    sc=np.array([x['score'] for x in sub]); tc=np.array([x['touch'] for x in sub])
    print('   score~touch rho=%+.3f p=%.4g'%st.spearmanr(sc,tc))
json.dump(R,open(SP+'/H10.json','w',encoding='utf-8'),ensure_ascii=False)
