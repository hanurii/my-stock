import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
exec(open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/lens.py',encoding='utf-8').read().split('# ---- A.')[0])

UP=[e for e in CONF if e['up']]; ALL=CONF
byidx={e['idx']:e for e in EV}

# ---- B1. 경로별 자기제거: 각 시뮬레이션에서 그 경로의 실현이익 상위 k건을 지우고 같은 시드로 재실행 ----
print('\n=== B1. 각 무작위경로에서 "그 경로의 최고 수익거래" 상위 k건 제거 후 같은 시드 재실행 ===')
for k in [0,1,2,3,5]:
    outs=[]
    for s in range(NS):
        r,n,c=sim(UP,s,track=True)
        top=sorted(c.items(),key=lambda kv:-kv[1])[:k]
        ex=frozenset(i for i,_ in top)
        r2,n2=sim(UP,s,exclude=ex)
        outs.append(r2)
    o=sorted(outs)
    print(f"k={k}: 중앙 {st.median(outs):+7.2f}%  평균 {st.mean(outs):+7.2f}%  P10 {o[30]:+7.2f}%  플러스비율 {100*sum(1 for x in outs if x>0)/NS:5.1f}%")

# ---- B2. 300회 평균 기여도 상위 k건 제거 ----
print('\n=== B2. 300회 평균 실현이익(원화 기여) 상위 k건을 풀에서 삭제 ===')
agg=defaultdict(float); cnt=defaultdict(int)
for s in range(NS):
    r,n,c=sim(UP,s,track=True)
    for i,v in c.items(): agg[i]+=v; cnt[i]+=1
rank=sorted(agg.items(),key=lambda kv:-kv[1])
tot=sum(v for v in agg.values() if v>0)
print('평균 기여 상위 10:')
for i,v in rank[:10]:
    e=byidx[i]
    print(f"   {e['name']:>10s} {e['entry_date']} {e['gain_at_resolve_pct']:+6.2f}%  채택률 {100*cnt[i]/NS:5.1f}%  평균기여 {v/NS*100:+.3f}%p")
for k in [0,1,2,3,5,10]:
    ex=frozenset(i for i,_ in rank[:k])
    r=run(UP,exclude=ex)
    print(f"k={k:2d}: 중앙 {r['med']:+7.2f}%  평균 {r['mean']:+7.2f}%  P10 {r['p10']:+7.2f}%  플러스비율 {r['pos']:5.1f}%  거래 {r['ntr']:.0f}건")

# ---- C. leave-one-out 전수 (상승국면 452중 확정분 전부) ----
print('\n=== C. 상승국면 후보 전수 leave-one-out (한 건씩 지우고 300회 중앙값) ===')
loo=[]
for e in UP:
    r=run(UP,exclude=frozenset([e['idx']]),ns=60)
    loo.append((r['med'],e))
loo.sort()
base60=run(UP,ns=60)['med']
print(f"기준(60회 중앙) {base60:+.2f}%")
print('가장 아픈 5건:')
for m,e in loo[:5]:
    print(f"   -{e['name']:>10s} {e['entry_date']} {e['gain_at_resolve_pct']:+6.2f}% → {m:+7.2f}% (Δ{m-base60:+.2f}%p)")
print(f"leave-one-out 최저 {loo[0][0]:+.2f}% / 최고 {loo[-1][0]:+.2f}% / 중앙 {st.median([x[0] for x in loo]):+.2f}%")
print(f"제거해서 마이너스가 되는 단일 거래 수: {sum(1 for m,_ in loo if m<=0)}")

# ---- D. 이익 집중도 ----
print('\n=== D. 이익 집중도 (300회 평균 기여 기준) ===')
pos=[v for v in agg.values() if v>0]; neg=[v for v in agg.values() if v<=0]
gp=sum(pos); gl=-sum(neg)
sh=sorted(pos,reverse=True)
print(f"총 실현이익 {gp/NS*100:+.1f}%p / 총 손실 {-gl/NS*100:+.1f}%p / 순 {(gp-gl)/NS*100:+.1f}%p")
for k in [1,3,5,10]:
    print(f"   상위 {k:2d}건이 총이익의 {100*sum(sh[:k])/gp:5.1f}%")
# 종목 단위
bycode=defaultdict(float)
for i,v in agg.items(): bycode[byidx[i]['code']]+=v
rc=sorted(bycode.items(),key=lambda kv:-kv[1])
print('\n=== E. 종목 단위 상위 기여 제거 ===')
for k in [1,3,5]:
    codes=set(c for c,_ in rc[:k])
    ex=frozenset(e['idx'] for e in UP if e['code'] in codes)
    r=run(UP,exclude=ex)
    nm_=', '.join(byidx[[e['idx'] for e in UP if e['code']==c][0]]['name'] for c,_ in rc[:k])
    print(f"상위 {k}종목({nm_}) 전거래 {len(ex)}건 제거 → 중앙 {r['med']:+7.2f}%  P10 {r['p10']:+7.2f}%  플러스비율 {r['pos']:5.1f}%")
