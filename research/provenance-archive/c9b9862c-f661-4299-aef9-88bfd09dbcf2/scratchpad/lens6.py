import json, sys, random, statistics as st, time
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('lens.py',encoding='utf-8').read().split('# ---- A.')[0])
ALL=CONF; UP=[e for e in CONF if e['up']]
dates=pit['dates']; upflag=[bool(x) for x in pit['up']]; N=len(dates)
SEEDS=40   # 관측·null 모두 동일 시드수, 통계량은 시드평균(중앙값보다 잡음 작음)
def stat(pool,k=0,seeds=SEEDS):
    if not pool: return 0.0,0
    ex=frozenset()
    if k>0:
        agg=defaultdict(float)
        for s in range(seeds):
            r,n,c=sim(pool,s,track=True)
            for i,v in c.items(): agg[i]+=v
        ex=frozenset(i for i,_ in sorted(agg.items(),key=lambda kv:-kv[1])[:k])
    rs=[sim(pool,s,exclude=ex) for s in range(seeds)]
    return st.mean([x[0] for x in rs]), st.mean([x[1] for x in rs])
KS=[0,1,3,5]
obs={k:stat(UP,k) for k in KS}
oall={k:stat(ALL,k) for k in KS}
print('관측 상승국면 (시드평균 40회):', {k:round(v[0],2) for k,v in obs.items()})
print('관측 전부매수 (자기 상위k 제거):', {k:round(v[0],2) for k,v in oall.items()})
t0=time.time()
rot=defaultdict(list)
for j in range(1,N):
    s={dates[i] for i in range(N) if upflag[(i+j)%N]}
    p=[e for e in ALL if e['scan_date'] in s]
    for k in KS: rot[k].append(stat(p,k)[0])
print(f'\n=== M. 국면라벨 원형회전 null (블록보존, 오프셋 213개 전수, 동일 추정량) === {time.time()-t0:.0f}s')
for k in KS:
    ns=sorted(rot[k]); o=obs[k][0]
    pv=(sum(1 for x in ns if x>=o)+1)/(len(ns)+1)
    print(f"상위{k}건 제거: 관측 {o:+7.2f}%  null 중앙 {st.median(ns):+7.2f}%  P90 {ns[int(.9*len(ns))]:+7.2f}%  최대 {ns[-1]:+7.2f}%  p={pv:.3f}")
