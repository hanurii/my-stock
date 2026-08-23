import json, sys, random, statistics as st, time
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('lens.py',encoding='utf-8').read().split('# ---- A.')[0])
UP=[e for e in CONF if e['up']]; ALL=CONF
print(f"확정 580 중 상승국면 후보 {len(UP)}건 / 조정국면 {len(ALL)-len(UP)}건")

def med_and_top(pool, seeds=25, k=0):
    """median result over seeds; if k>0 remove that pool's own top-k contributors first"""
    if k>0:
        agg=defaultdict(float)
        for s in range(seeds):
            r,n,c=sim(pool,s,track=True)
            for i,v in c.items(): agg[i]+=v
        ex=frozenset(i for i,_ in sorted(agg.items(),key=lambda kv:-kv[1])[:k])
    else: ex=frozenset()
    return st.median([sim(pool,s,exclude=ex)[0] for s in range(seeds)])

t0=time.time()
obs={k:med_and_top(UP,25,k) for k in [0,1,3,5]}
print('관측(상승국면, 25시드):', {k:round(v,2) for k,v in obs.items()})
NDRAW=300
rng=random.Random(7)
null={0:[],1:[],3:[],5:[]}
for d in range(NDRAW):
    samp=rng.sample(ALL,len(UP))
    for k in null: null[k].append(med_and_top(samp,15,k))
print(f'null {NDRAW}회 완료 {time.time()-t0:.0f}s')
print('\n=== J. "무작위로 같은 건수만 고른 필터" null 과의 비교 (각 arm 자기 상위k 제거 후) ===')
for k in [0,1,3,5]:
    ns=sorted(null[k]); o=obs[k]
    p=sum(1 for x in ns if x>=o)/len(ns)
    print(f"k={k}: 관측 {o:+7.2f}%  null 중앙 {st.median(ns):+7.2f}%  null P90 {ns[int(.9*len(ns))]:+7.2f}%  p={p:.3f}")
