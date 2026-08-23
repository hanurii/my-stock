import sys; sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from base import load
import numpy as np, pandas as pd
from scipy import stats as st
ev,r=load(); r=r.reset_index(drop=True)
di=r.groupby('scan_date').ngroup().values; nd=di.max()+1
w=r['w'].values.astype(float); ci=r.groupby('code').ngroup().values; nc=ci.max()+1
def diff_stat(idx,thr):
    d=di[idx]; ww=w[idx]; hi=(r['pct_all'].values[idx]>thr)
    sA=np.bincount(d[hi],ww[hi],minlength=nd); cA=np.bincount(d[hi],minlength=nd)
    sB=np.bincount(d[~hi],ww[~hi],minlength=nd); cB=np.bincount(d[~hi],minlength=nd)
    v=(cA>0)&(cB>0)
    if v.sum()==0: return np.nan
    return (sA[v]/cA[v]-sB[v]/cB[v]).mean(), int(v.sum())
rng=np.random.default_rng(11)
idxmap=[np.where(ci==j)[0] for j in range(nc)]
for thr,lab in [(0.75,'상위25%'),(0.5,'상위50%')]:
    obs,ndv=diff_stat(np.arange(len(w)),thr)
    bs=[]
    for _ in range(3000):
        pick=rng.integers(0,nc,nc)
        ii=np.concatenate([idxmap[j] for j in pick])
        x=diff_stat(ii,thr)
        if x==x if not isinstance(x,tuple) else True:
            bs.append(x[0] if isinstance(x,tuple) else np.nan)
    bs=np.array([b for b in bs if b==b])
    print(f'[{lab} vs 나머지, 같은날 짝지음] 비교가능일={ndv} 관측 승률차={100*obs:+.1f}%p  종목클러스터 부트스트랩 95%CI {100*np.quantile(bs,.025):+.1f}~{100*np.quantile(bs,.975):+.1f}%p  P(효과<0)={np.mean(bs<0):.3f}')
# 실현수익 차이도
r['ret']=r['gain_at_resolve_pct']
for thr,lab in [(0.75,'상위25%'),(0.5,'상위50%')]:
    hi=r['pct_all']>thr
    print(f'   {lab}: 승률 {100*r[hi].w.mean():.1f}%(n{hi.sum()}) vs {100*r[~hi].w.mean():.1f}%(n{(~hi).sum()}) / 실현 {r[hi].ret.mean():+.2f}% vs {r[~hi].ret.mean():+.2f}%')
