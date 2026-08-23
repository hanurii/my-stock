import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('lens.py',encoding='utf-8').read().split('# ---- A.')[0])
ALL=CONF; UP=[e for e in CONF if e['up']]
dates=pit['dates']; upflag=[bool(x) for x in pit['up']]
N=len(dates)
def pool_for(flag):
    s={dates[i] for i in range(N) if flag[i]}
    return [e for e in ALL if e['scan_date'] in s]
def med_and_top(pool, seeds=15, k=0):
    if not pool: return 0.0,0
    if k>0:
        agg=defaultdict(float)
        for s in range(seeds):
            r,n,c=sim(pool,s,track=True)
            for i,v in c.items(): agg[i]+=v
        ex=frozenset(i for i,_ in sorted(agg.items(),key=lambda kv:-kv[1])[:k])
    else: ex=frozenset()
    rs=[sim(pool,s,exclude=ex) for s in range(seeds)]
    return st.median([x[0] for x in rs]), st.median([x[1] for x in rs])

obs={k:med_and_top(UP,25,k) for k in [0,1,3,5]}
print('관측 상승국면:', {k:(round(v[0],2),v[1]) for k,v in obs.items()})

print('\n=== K. 국면 라벨 원형회전 null (블록구조 보존, 213개 오프셋 전수) ===')
res=defaultdict(list); ntr=defaultdict(list)
for j in range(1,N):
    fl=[upflag[(i+j)%N] for i in range(N)]
    p=pool_for(fl)
    for k in [0,1,3,5]:
        m,n=med_and_top(p,9,k); res[k].append(m); ntr[k].append(n)
for k in [0,1,3,5]:
    ns=sorted(res[k]); o=obs[k][0]
    pv=(sum(1 for x in ns if x>=o)+1)/(len(ns)+1)
    print(f"k={k}: 관측 {o:+7.2f}%({obs[k][1]:.0f}건)  회전null 중앙 {st.median(ns):+7.2f}% P90 {ns[int(.9*len(ns))]:+7.2f}% 최대 {ns[-1]:+7.2f}% 평균거래 {st.mean(ntr[k]):.0f}건  p={pv:.3f}")

print('\n=== L. 진입건수를 69건에 맞춘 무작위 표집 null (직전 렌즈 p=0.10 재현) ===')
rng=random.Random(11)
def subsample_to(target, seedbase):
    # binary search on candidate keep-rate to hit ~target executed trades
    lo,hi=0.02,1.0
    for _ in range(12):
        mid=(lo+hi)/2
        p=[e for e in ALL if rng.random()<mid]
        m,n=med_and_top(p,5,0)
        if n>target: hi=mid
        else: lo=mid
    return (lo+hi)/2
rate=subsample_to(69,0)
print(f'표집률 {rate:.3f}')
out=defaultdict(list); outn=[]
for d in range(300):
    p=[e for e in ALL if rng.random()<rate]
    for k in [0,1,3,5]:
        m,n=med_and_top(p,9,k); out[k].append(m)
        if k==0: outn.append(n)
print(f'평균 거래 {st.mean(outn):.0f}건')
for k in [0,1,3,5]:
    ns=sorted(out[k]); o=obs[k][0]
    pv=(sum(1 for x in ns if x>=o)+1)/(len(ns)+1)
    print(f"k={k}: 관측 {o:+7.2f}%  null 중앙 {st.median(ns):+7.2f}% P90 {ns[int(.9*len(ns))]:+7.2f}%  p={pv:.3f}")
