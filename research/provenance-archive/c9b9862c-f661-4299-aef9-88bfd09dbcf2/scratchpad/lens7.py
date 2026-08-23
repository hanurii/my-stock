import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('lens.py',encoding='utf-8').read().split('# ---- A.')[0])
ALL=CONF; UP=[e for e in CONF if e['up']]
byidx={e['idx']:e for e in EV}
def agg_of(pool,seeds=300):
    a=defaultdict(float)
    for s in range(seeds):
        r,n,c=sim(pool,s,track=True)
        for i,v in c.items(): a[i]+=v
    return a
aU=agg_of(UP); aA=agg_of(ALL)
rU=sorted(aU.items(),key=lambda kv:-kv[1]); rA=sorted(aA.items(),key=lambda kv:-kv[1])
print('=== N. 대칭성: 최고 기여 vs 최악 기여 동수 제거 ===')
for k in [1,3,5,10]:
    up_best=run(UP,exclude=frozenset(i for i,_ in rU[:k]))['med']
    up_worst=run(UP,exclude=frozenset(i for i,_ in rU[-k:]))['med']
    al_best=run(ALL,exclude=frozenset(i for i,_ in rA[:k]))['med']
    al_worst=run(ALL,exclude=frozenset(i for i,_ in rA[-k:]))['med']
    print(f"k={k:2d}: 상승국면 최고{k}제거 {up_best:+7.2f}% / 최악{k}제거 {up_worst:+7.2f}%  |  전부매수 최고 {al_best:+7.2f}% / 최악 {al_worst:+7.2f}%")
print('\n=== O. 총이익/총손실 구조 (평균 300회) ===')
for nm_,a in [('상승국면',aU),('전부매수',aA)]:
    gp=sum(v for v in a.values() if v>0); gl=-sum(v for v in a.values() if v<=0)
    print(f"{nm_}: 총이익 {gp/300*100:+.1f}%p, 총손실 -{gl/300*100:.1f}%p, 순 {(gp-gl)/300*100:+.1f}%p → 순이익은 총이익의 {100*(gp-gl)/gp:.0f}%")
print('\n=== P. 상위 기여 5건의 성격 (대박인가 평범한 목표달성인가) ===')
for i,v in rU[:5]:
    e=byidx[i]
    print(f"   {e['name']:>10s} {e['entry_date']} 실현 {e['gain_at_resolve_pct']:+6.2f}%  최대상승 {e['max_gain_pct']:+6.1f}%  보유 {e['days_held']}일  평균기여 {v/300*100:+.2f}%p")
w=sorted([e['gain_at_resolve_pct'] for e in UP if e['result']=='win'],reverse=True)
print(f"\n상승국면 승자 {len(w)}건 실현수익 분포: 최대 {w[0]:+.1f}% / P90 {w[int(.1*len(w))]:+.1f}% / 중앙 {st.median(w):+.1f}% (목표 +20% 고정이라 홈런 자체가 구조적으로 불가)")
