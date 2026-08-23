import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
HAVE_SM=False
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
R=[x for x in json.load(open(SP+'/H10.json',encoding='utf-8')) if x['ext'] is not None]
print('n',len(R),'codes',len(set(x['code'] for x in R)))
print('score~ext spearman rho=%+.3f p=%.3g'%st.spearmanr([x['score'] for x in R],[x['ext'] for x in R]))
print('score~rs    rho=%+.3f p=%.3g'%st.spearmanr([x['score'] for x in R],[x['rs'] for x in R]))
print('score~ret252 rho=%+.3f p=%.3g'%st.spearmanr([x['score'] for x in R],[x['ret252'] for x in R]))

y=np.array([x['touch'] for x in R],dtype=float)
sc=np.array([x['score'] for x in R],dtype=float)
le=np.log1p(np.array([max(x['ext'],-99) for x in R],dtype=float)/100.0)
X=sm.add_constant(np.column_stack([le,sc]))
gid=np.array([x['code'] for x in R])
m=sm.Logit(y,X).fit(disp=0)
mc=sm.Logit(y,X).fit(cov_type='cluster',cov_kwds={'groups':gid},disp=0)
print('\n=== logistic: touch ~ log(1+ext) + score ===')
print('  naive  : ext b=%+.3f z=%+.2f p=%.3g | score b=%+.4f z=%+.2f p=%.3f'%(m.params[1],m.tvalues[1],m.pvalues[1],m.params[2],m.tvalues[2],m.pvalues[2]))
print('  cluster: ext b=%+.3f z=%+.2f p=%.3g | score b=%+.4f z=%+.2f p=%.3f'%(mc.params[1],mc.tvalues[1],mc.pvalues[1],mc.params[2],mc.tvalues[2],mc.pvalues[2]))
# reverse: score alone clustered
X1=sm.add_constant(sc.reshape(-1,1))
m1=sm.Logit(y,X1).fit(cov_type='cluster',cov_kwds={'groups':gid},disp=0)
print('  score ALONE (cluster): b=%+.4f z=%+.2f p=%.4f'%(m1.params[1],m1.tvalues[1],m1.pvalues[1]))
X2=sm.add_constant(le.reshape(-1,1))
m2=sm.Logit(y,X2).fit(cov_type='cluster',cov_kwds={'groups':gid},disp=0)
print('  ext   ALONE (cluster): b=%+.4f z=%+.2f p=%.4f'%(m2.params[1],m2.tvalues[1],m2.pvalues[1]))

print('\n=== score effect WITHIN extension strata ===')
for lab,sub in [('ext<150',[x for x in R if x['ext']<150]),('ext>=150',[x for x in R if x['ext']>=150])]:
    s=np.array([x['score'] for x in sub]); t=np.array([x['touch'] for x in sub])
    rho,p=st.spearmanr(s,t)
    print(f'  {lab}: n={len(sub)} codes={len(set(x["code"] for x in sub))} touch={t.mean()*100:.1f}%  score~touch rho={rho:+.3f} p={p:.3f}')
    for b,f in [('<20',lambda v:v<20),('20-50',lambda v:20<=v<50),('>=50',lambda v:v>=50)]:
        g=[x for x in sub if f(x['score'])]
        if g: print(f'      score {b}: n={len(g)} touch={np.mean([x["touch"] for x in g])*100:.1f}%')

print('\n=== STOCK-LEVEL (each stock counted once, first recommendation) ===')
seen={};first=[]
for x in sorted(R,key=lambda z:z['date']):
    if x['code'] in seen: continue
    seen[x['code']]=1; first.append(x)
print('n stocks',len(first),'touch=%.1f%%'%(np.mean([x['touch'] for x in first])*100))
hi=[x for x in first if x['ext']>=150]; lo=[x for x in first if x['ext']<150]
kh=sum(x['touch'] for x in hi); kl=sum(x['touch'] for x in lo)
print(f'  ext>=150: n={len(hi)} touch={kh/len(hi)*100:.1f}% med_ret={np.median([x["ret"] for x in hi]):+.2f}%')
print(f'  ext<150 : n={len(lo)} touch={kl/len(lo)*100:.1f}% med_ret={np.median([x["ret"] for x in lo]):+.2f}%')
print('  fisher p=%.3g'%st.fisher_exact([[kh,len(hi)-kh],[kl,len(lo)-kl]])[1])
for b,f in [('<20',lambda v:v<20),('20-50',lambda v:20<=v<50),('>=50',lambda v:v>=50)]:
    g=[x for x in first if f(x['score'])]
    print(f'  score {b}: n={len(g)} touch={np.mean([x["touch"] for x in g])*100:.1f}% med_ret={np.median([x["ret"] for x in g]):+.2f}%')
s=np.array([x['score'] for x in first]);t=np.array([x['touch'] for x in first])
print('  score~touch rho=%+.3f p=%.4f'%st.spearmanr(s,t))
e=np.array([x['ext'] for x in first])
print('  ext~touch   rho=%+.3f p=%.3g'%st.spearmanr(e,t))
# partial: score~touch controlling ext (stock level)
import itertools
res_s=st.rankdata(s)-np.polyval(np.polyfit(st.rankdata(e),st.rankdata(s),1),st.rankdata(e))
res_t=st.rankdata(t)-np.polyval(np.polyfit(st.rankdata(e),st.rankdata(t),1),st.rankdata(e))
print('  partial score~touch | ext : rho=%+.3f p=%.3f'%st.pearsonr(res_s,res_t))
