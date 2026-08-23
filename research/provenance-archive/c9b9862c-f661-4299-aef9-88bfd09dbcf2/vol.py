import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
from scipy.stats import norm
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
sys.path.insert(0,SP)
from logit import logit_fit, cluster_se
from canslim_lib import ohlcv_matrix
R=[x for x in json.load(open(SP+'/H10.json',encoding='utf-8')) if x['ext'] is not None]
cache={}
def ser(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
for x in R:
    s=ser(x['code']); i=s['dates'].index(x['date'])
    cl=np.array(s['closes'][max(0,i-20):i+1],dtype=float)
    r=np.diff(np.log(cl))
    x['vol20']=float(np.std(r,ddof=1)*100)         # daily % stdev, 20d, prior to entry
    hi=np.array(s['highs'][max(0,i-19):i+1],float); lo=np.array(s['lows'][max(0,i-19):i+1],float)
    x['atr20']=float(np.mean((hi-lo)/cl[-len(hi):])*100)
    x['zret']=x['ret']/(x['vol20']*np.sqrt(10)) if x['vol20']>0 else None
print('vol20 median %.2f%%/day'%np.median([x['vol20'] for x in R]))
print('ext~vol20 rho=%+.3f p=%.3g'%st.spearmanr([x['ext'] for x in R],[x['vol20'] for x in R]))
print('score~vol20 rho=%+.3f p=%.3g'%st.spearmanr([x['score'] for x in R],[x['vol20'] for x in R]))
lo_=[x for x in R if x['ext']<150]; hi_=[x for x in R if x['ext']>=150]
print('vol20 median: ext<150 %.2f%%  ext>=150 %.2f%%'%(np.median([x['vol20'] for x in lo_]),np.median([x['vol20'] for x in hi_])))

y=np.array([x['touch'] for x in R],float); gid=np.array([x['code'] for x in R])
le=np.log1p(np.array([x['ext'] for x in R],float)/100); v=np.array([x['vol20'] for x in R],float)
sc=np.array([x['score'] for x in R],float); o=np.ones(len(y))
def rep(lab,X,names):
    b,se,Iinv,p=logit_fit(X,y); cse=cluster_se(X,y,b,Iinv,gid)
    for i,n in enumerate(names):
        if n=='const': continue
        z=b[i]/se[i]; zc=b[i]/cse[i]
        print(f'  [{lab}] {n}: b={b[i]:+.4f} naive p={2*(1-norm.cdf(abs(z))):.3g} | CLUSTERED z={zc:+.2f} p={2*(1-norm.cdf(abs(zc))):.4f}')
print('\n=== logistic touch ~ ... , cluster SE ===')
rep('vol only', np.column_stack([o,v]),['const','vol20'])
rep('ext+vol ', np.column_stack([o,le,v]),['const','log1p(ext)','vol20'])
rep('ext+vol+score', np.column_stack([o,le,v,sc]),['const','log1p(ext)','vol20','score'])

print('\n=== RETURN (not touch): vol-standardised 10d return ===')
for lab,sub in [('ext<150',lo_),('ext>=150',hi_)]:
    print(f'  {lab}: n={len(sub)} raw_med={np.median([x["ret"] for x in sub]):+.2f}%  volstd_med={np.median([x["zret"] for x in sub]):+.3f} sigma')
print('  MWU raw p=%.3g | volstd p=%.3g'%(st.mannwhitneyu([x['ret'] for x in hi_],[x['ret'] for x in lo_]).pvalue,
                                          st.mannwhitneyu([x['zret'] for x in hi_],[x['zret'] for x in lo_]).pvalue))
print('  ext~zret rho=%+.3f p=%.3g'%st.spearmanr([x['ext'] for x in R],[x['zret'] for x in R]))
print('  score~zret rho=%+.3f p=%.3g'%st.spearmanr([x['score'] for x in R],[x['zret'] for x in R]))

print('\n=== STOCK-LEVEL, vol-standardised ===')
seen=set();first=[]
for x in sorted(R,key=lambda z:z['date']):
    if x['code'] in seen: continue
    seen.add(x['code']); first.append(x)
fh=[x for x in first if x['ext']>=150]; fl=[x for x in first if x['ext']<150]
print(f'  ext>=150 n={len(fh)} volstd_med={np.median([x["zret"] for x in fh]):+.3f}s  vol20med={np.median([x["vol20"] for x in fh]):.2f}%')
print(f'  ext<150  n={len(fl)} volstd_med={np.median([x["zret"] for x in fl]):+.3f}s  vol20med={np.median([x["vol20"] for x in fl]):.2f}%')
print('  MWU volstd p=%.4g'%st.mannwhitneyu([x['zret'] for x in fh],[x['zret'] for x in fl]).pvalue)
# touch controlling vol at stock level: match on vol tercile
vs=np.array([x['vol20'] for x in first]); q=np.quantile(vs,[1/3,2/3])
for i,(a,b) in enumerate([(-1,q[0]),(q[0],q[1]),(q[1],1e9)]):
    g=[x for x in first if a<x['vol20']<=b]
    gh=[x for x in g if x['ext']>=150]; gl=[x for x in g if x['ext']<150]
    f=lambda z: (np.mean([q2['touch'] for q2 in z])*100 if z else float('nan'))
    print(f'  vol tercile {i+1} ({a if a>0 else 0:.2f}-{b if b<1e8 else 99:.2f}%/d): ext>=150 n={len(gh)} touch={f(gh):.0f}% | ext<150 n={len(gl)} touch={f(gl):.0f}%')
json.dump(R,open(SP+'/H10v.json','w',encoding='utf-8'),ensure_ascii=False)
