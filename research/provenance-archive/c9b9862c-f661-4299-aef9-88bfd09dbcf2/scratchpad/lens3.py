import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('lens.py',encoding='utf-8').read().split('# ---- A.')[0])
UP=[e for e in CONF if e['up']]; ALL=CONF
byidx={e['idx']:e for e in EV}
agg=defaultdict(float)
for s in range(NS):
    r,n,c=sim(UP,s,track=True)
    for i,v in c.items(): agg[i]+=v
rank=[i for i,_ in sorted(agg.items(),key=lambda kv:-kv[1])]
aggA=defaultdict(float)
for s in range(NS):
    r,n,c=sim(ALL,s,track=True)
    for i,v in c.items(): aggA[i]+=v
rankA=[i for i,_ in sorted(aggA.items(),key=lambda kv:-kv[1])]

print('\n=== F. 같은 거래를 양쪽에서 똑같이 지운 짝비교 ===')
print(' k | 상승국면(중앙)  전부매수(중앙)   차이   | 각 arm 자기 상위k 제거시 전부매수')
for k in [0,1,2,3,5,10]:
    exU=frozenset(rank[:k]); exA_same=exU
    u=run(UP,exclude=exU); a=run(ALL,exclude=exA_same); aown=run(ALL,exclude=frozenset(rankA[:k]))
    print(f"{k:2d} | {u['med']:+7.2f}%  {a['med']:+7.2f}%  {u['med']-a['med']:+7.2f}%p |  {aown['med']:+7.2f}%")

print('\n=== G. 이익 집중도 (상승국면, 300회 평균 기여) ===')
pos=sorted([v for v in agg.values() if v>0],reverse=True)
gp=sum(pos); gl=-sum(v for v in agg.values() if v<=0)
print(f"평균 총이익 {gp/NS*100:+.1f}%p, 총손실 {-gl/NS*100:+.1f}%p, 순 {(gp-gl)/NS*100:+.1f}%p, 이익거래 {len(pos)}종")
for k in [1,3,5,10,20]:
    print(f"   기여 상위 {k:2d}건 = 총이익의 {100*sum(pos[:k])/gp:5.1f}%")

print('\n=== H. leave-one-out 전수 (60회 중앙값) ===')
base=run(UP,ns=60)['med']
loo=[]
for e in UP:
    loo.append((run(UP,exclude=frozenset([e['idx']]),ns=60)['med'], e['idx']))
loo.sort(key=lambda x:x[0])
print(f"기준 {base:+.2f}%  |  최저 {loo[0][0]:+.2f}%  최고 {loo[-1][0]:+.2f}%  중앙 {st.median([x[0] for x in loo]):+.2f}%")
for m,i in loo[:5]:
    e=byidx[i]; print(f"   -{e['name']:>10s} {e['entry_date']} {e['gain_at_resolve_pct']:+6.2f}% → {m:+7.2f}% (Δ{m-base:+.2f}%p)")
print(f"단일 제거로 0% 이하가 되는 거래: {sum(1 for m,_ in loo if m<=0)}건")

print('\n=== I. 시기 집중도: 마지막 달(2026-08) 진입 제외 ===')
for cut in ['2026-08-01','2026-07-01','2026-06-01']:
    exU=frozenset(e['idx'] for e in UP if e['entry_date']>=cut)
    exA=frozenset(e['idx'] for e in ALL if e['entry_date']>=cut)
    u=run(UP,exclude=exU); a=run(ALL,exclude=exA)
    print(f"{cut} 이후 진입 제외 → 상승국면 {u['med']:+7.2f}% ({u['ntr']:.0f}건)  전부매수 {a['med']:+7.2f}% ({a['ntr']:.0f}건)  차이 {u['med']-a['med']:+6.2f}%p")
