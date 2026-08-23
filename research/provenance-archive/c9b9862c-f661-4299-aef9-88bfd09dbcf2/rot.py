import sys,json,statistics,random;sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events
from cal import sim
ev=load_events(); R={r.name:r for r in make_all()}
sdates=sorted(set(e['scan_date'] for e in ev))
def flagmap(name):
    m={}
    for e in ev: m[e['scan_date']]=R[name](e)
    return m
def run(flagbydate):
    S={i for i,e in enumerate(ev) if flagbydate.get(e['scan_date']) is True}
    if not S: return None,0
    r,tk=sim(ev,S,n_iter=60)
    return r,len(S)

for name in ['EW20_baseline(등가중20일선)','코스닥20일선','나스닥20일선','코스피20일선']:
    fm=flagmap(name)
    seq=[fm[d] for d in sdates]
    actual,ns=run(fm)
    res=[]
    n=len(sdates)
    for k in range(1,n):   # every non-zero circular shift = exhaustive null
        rot=seq[k:]+seq[:k]
        rm=dict(zip(sdates,rot))
        r,_=run(rm)
        res.append(r)
    res_sorted=sorted(res)
    better=sum(1 for x in res if x>=actual)
    print('%-28s 실제 %+7.2f%% (후보 %d)  |  회전널 %d개 중 실제이상 %d개 = p=%.3f  중앙 %+6.2f%%  5~95%% [%+.1f%%, %+.1f%%]'
          %(name,actual,ns,len(res),better,better/len(res),statistics.median(res),
            res_sorted[int(.05*len(res))],res_sorted[int(.95*len(res))]))
