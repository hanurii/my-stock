import json, os
from collections import Counter, defaultdict
import numpy as np
from scipy import stats as st
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
J=json.load(open(SP+'/joined.json',encoding='utf-8'))
closed=[r for r in J if r.get('resolved') and r['resolved']['outcome']!='open']
print('closed',len(closed))
nm={ }
for r in closed: nm[r['code']]=r['name']
cc=Counter(r['code'] for r in closed)
print('repeat top:',[(nm[c],n) for c,n in cc.most_common(6)])

def band(s):
    return '<20' if s<20 else ('20-50' if s<50 else '>=50')
tab=defaultdict(lambda:[0,0])
for r in closed:
    b=band(r['score']); tab[b][0]+=1
    if r['resolved']['outcome']=='stop': tab[b][1]+=1
print('--- draft bands (closed) ---')
obs=[]
for b in ['<20','20-50','>=50']:
    n,s=tab[b]; print(f'{b}: n={n} stop={s/n*100:.1f}%')
    obs.append([s,n-s])
chi2,p,dof,exp=st.chi2_contingency(np.array(obs))
print('chi2 p=%.4f'%p)

sc=np.array([r['score'] for r in closed])
stop=np.array([1 if r['resolved']['outcome']=='stop' else 0 for r in closed])
cur=np.array([r['resolved']['cur_ret_pct'] for r in closed])
mg=np.array([r['resolved']['max_gain_pct'] for r in closed])
for nmx,y in [('stop',stop),('cur_ret',cur),('max_gain',mg)]:
    rho,p=st.spearmanr(sc,y); print(f'score~{nmx}: rho={rho:+.3f} p={p:.3f}')

print('--- 10pt bins (closed) ---')
cent=[];rate=[]
for lo in range(0,100,10):
    hi=lo+10
    g=[r for r in closed if (r['score']>=lo and (r['score']<hi if hi<100 else r['score']<=100))]
    if not g: print(f'{lo}-{hi}: 0'); continue
    n=len(g); s=sum(1 for r in g if r['resolved']['outcome']=='stop')
    print(f'{lo}-{hi}: n={n} stop={s/n*100:.1f}% tgt={(n-s)/n*100:.1f}% curmed={np.median([r["resolved"]["cur_ret_pct"] for r in g]):+.2f}% mgmed={np.median([r["resolved"]["max_gain_pct"] for r in g]):.2f}%')
    cent.append(lo+5); rate.append(s/n)
rho,p=st.spearmanr(cent,rate); print(f'bin-center~bin-stoprate rho={rho:+.3f} p={p:.3f}')

# first appearance only
seen=set(); first=[]
for r in sorted(J,key=lambda x:x['date']):
    if r['code'] in seen: continue
    seen.add(r['code']); first.append(r)
print('\n--- first appearance ---')
print('first n',len(first))
fc=[r for r in first if r.get('resolved') and r['resolved']['outcome']!='open']
print('first closed',len(fc))
tab=defaultdict(lambda:[0,0])
for r in fc:
    b=band(r['score']); tab[b][0]+=1
    if r['resolved']['outcome']=='stop': tab[b][1]+=1
obs=[]
for b in ['<20','20-50','>=50']:
    n,s=tab[b]; print(f'{b}: n={n} stop={s/n*100:.1f}%'); obs.append([s,n-s])
chi2,p,dof,exp=st.chi2_contingency(np.array(obs)); print('chi2 p=%.3f'%p)
sc=np.array([r['score'] for r in fc]); stop=np.array([1 if r['resolved']['outcome']=='stop' else 0 for r in fc])
cur=np.array([r['resolved']['cur_ret_pct'] for r in fc])
print('score~stop rho=%+.3f p=%.3f'%st.spearmanr(sc,stop))
print('score~cur  rho=%+.3f p=%.3f'%st.spearmanr(sc,cur))

# censoring
print('\n--- censoring ---')
allres=[r for r in J if r.get('resolved')]
sc=np.array([r['score'] for r in allres]); op=np.array([1 if r['resolved']['outcome']=='open' else 0 for r in allres])
print('score~open rho=%+.3f p=%.3g'%st.spearmanr(sc,op))
dates=sorted(set(r['date'] for r in allres)); di={d:i for i,d in enumerate(dates)}
ordv=np.array([di[r['date']] for r in allres])
print('dateorder~score rho=%+.3f p=%.3g'%st.spearmanr(ordv,sc))
print('dateorder~open  rho=%+.3f p=%.3g'%st.spearmanr(ordv,op))
q=np.quantile(sc,[1/3,2/3]); print('score terciles cut',q)
for i,(lo,hi) in enumerate([(-1,q[0]),(q[0],q[1]),(q[1],101)]):
    g=[r for r,s in zip(allres,sc) if lo<s<=hi]
    n=len(g); cl=sum(1 for r in g if r['resolved']['outcome']!='open')
    print(f'Q{i+1}: n={n} closed_rate={cl/n*100:.0f}%')
