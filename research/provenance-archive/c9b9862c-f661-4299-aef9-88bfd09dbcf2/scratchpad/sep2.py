import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
from scipy.stats import norm
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
sys.path.insert(0,SP)
from logit import logit_fit, cluster_se
R=[x for x in json.load(open(SP+'/H10.json',encoding='utf-8')) if x['ext'] is not None]
y=np.array([x['touch'] for x in R],dtype=float)
sc=np.array([x['score'] for x in R],dtype=float)
le=np.log1p(np.array([x['ext'] for x in R],dtype=float)/100.0)
gid=np.array([x['code'] for x in R])
def rep(lab,X,names):
    b,se,Iinv,p=logit_fit(X,y); cse=cluster_se(X,y,b,Iinv,gid)
    parts=[]
    for i,n in enumerate(names):
        if n=='const': continue
        z=b[i]/se[i]; zc=b[i]/cse[i]
        parts.append(f"{n}: b={b[i]:+.4f} naive z={z:+.2f} p={2*(1-norm.cdf(abs(z))):.3g} | CLUSTERED z={zc:+.2f} p={2*(1-norm.cdf(abs(zc))):.4f}")
    print(f'  [{lab}] '+'\n           '.join(parts))
o=np.ones(len(y))
print('=== logistic (cluster SE by stock, 76 clusters) ===')
rep('ext + score', np.column_stack([o,le,sc]), ['const','log1p(ext)','score'])
rep('score only ', np.column_stack([o,sc]), ['const','score'])
rep('ext only   ', np.column_stack([o,le]), ['const','log1p(ext)'])

print('\n=== score effect WITHIN extension strata ===')
for lab,sub in [('ext<150',[x for x in R if x['ext']<150]),('ext>=150',[x for x in R if x['ext']>=150])]:
    s=np.array([x['score'] for x in sub]); t=np.array([x['touch'] for x in sub])
    rho,p=st.spearmanr(s,t)
    print(f'  {lab}: n={len(sub)} codes={len(set(x["code"] for x in sub))} touch={t.mean()*100:.1f}%  score~touch rho={rho:+.3f} p={p:.3f}')
    for b,f in [('<20',lambda v:v<20),('20-50',lambda v:20<=v<50),('>=50',lambda v:v>=50)]:
        g=[x for x in sub if f(x['score'])]
        if g: print(f'      score {b}: n={len(g)} codes={len(set(z["code"] for z in g))} touch={np.mean([z["touch"] for z in g])*100:.1f}%')

print('\n=== STOCK-LEVEL (first recommendation per stock; the only independent unit) ===')
seen=set();first=[]
for x in sorted(R,key=lambda z:z['date']):
    if x['code'] in seen: continue
    seen.add(x['code']); first.append(x)
print('n stocks',len(first),'overall touch=%.1f%%'%(np.mean([x['touch'] for x in first])*100))
hi=[x for x in first if x['ext']>=150]; lo=[x for x in first if x['ext']<150]
kh=sum(x['touch'] for x in hi); kl=sum(x['touch'] for x in lo)
print(f'  ext>=150: n={len(hi)} touch={kh/len(hi)*100:.1f}% med10dret={np.median([x["ret"] for x in hi]):+.2f}%')
print(f'  ext<150 : n={len(lo)} touch={kl/len(lo)*100:.1f}% med10dret={np.median([x["ret"] for x in lo]):+.2f}%')
print('  fisher p=%.3g'%st.fisher_exact([[kh,len(hi)-kh],[kl,len(lo)-kl]])[1])
for b,f in [('<20',lambda v:v<20),('20-50',lambda v:20<=v<50),('>=50',lambda v:v>=50)]:
    g=[x for x in first if f(x['score'])]
    print(f'  score {b}: n={len(g)} touch={np.mean([x["touch"] for x in g])*100:.1f}% med10dret={np.median([x["ret"] for x in g]):+.2f}%')
s=np.array([x['score'] for x in first]);t=np.array([x['touch'] for x in first]);e=np.array([x['ext'] for x in first])
print('  score~touch rho=%+.3f p=%.4f'%st.spearmanr(s,t))
print('  ext~touch   rho=%+.3f p=%.3g'%st.spearmanr(e,t))
rs_=st.rankdata(s);re_=st.rankdata(e);rt_=st.rankdata(t)
def partial(a,b,c):
    rab=np.corrcoef(a,b)[0,1];rac=np.corrcoef(a,c)[0,1];rbc=np.corrcoef(b,c)[0,1]
    r=(rab-rac*rbc)/np.sqrt((1-rac**2)*(1-rbc**2)); n=len(a)
    tt=r*np.sqrt((n-3)/(1-r**2)); return r,2*(1-st.t.cdf(abs(tt),n-3))
print('  partial score~touch | ext: rho=%+.3f p=%.3f'%partial(rs_,rt_,re_))
print('  partial ext~touch | score: rho=%+.3f p=%.4f'%partial(re_,rt_,rs_))
