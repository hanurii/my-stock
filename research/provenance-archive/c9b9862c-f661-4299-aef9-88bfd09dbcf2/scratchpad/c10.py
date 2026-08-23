# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, random
EV=json.load(io.open('ev.json',encoding='utf-8'))
A=[e for e in EV if e['_reg'] is False and e['_nq'] is True]
Bc=[e for e in EV if e['_reg'] is False and e['_nq'] is False]
def mm(g):
    d=collections.defaultdict(list)
    for e in g: d[e['entry_date'][:7]].append(e['net'])
    return {k:st.mean(v) for k,v in d.items()}, d
ma,da=mm(A); mb,db=mm(Bc)
print("=== 월 단위로 봐도(월=1관측, 한 달이 통계를 지배하지 않게) ===")
print(f"  조정+NQ상승: {len(ma)}개월, 월평균의 평균 {st.mean(ma.values()):+.2f}%, 중앙 {st.median(ma.values()):+.2f}%")
print(f"  조정+NQ하락: {len(mb)}개월, 월평균의 평균 {st.mean(mb.values()):+.2f}%, 중앙 {st.median(mb.values()):+.2f}%")
both=sorted(set(ma)&set(mb))
pair=[ma[k]-mb[k] for k in both]
print(f"  같은 달 짝비교 {len(both)}개월: 상승이 나은 달 {sum(1 for x in pair if x>0)}개월 / 중앙 차이 {st.median(pair):+.2f}%p / 평균 {st.mean(pair):+.2f}%p")
import math
t=st.mean(pair)/(st.pstdev(pair)/math.sqrt(len(pair)))
print(f"  짝비교 t≈{t:.2f} (df={len(pair)-1})")
# 월 블록 부트스트랩
random.seed(3)
months=sorted(set(ma)|set(mb)); NB=5000; cnt=0
obs=st.mean([e['net'] for e in A])-st.mean([e['net'] for e in Bc])
for _ in range(NB):
    pick=[random.choice(months) for _ in months]
    a=[v for k in pick for v in da.get(k,[])]; b=[v for k in pick for v in db.get(k,[])]
    if len(a)<50 or len(b)<50: continue
    if st.mean(a)-st.mean(b)>=0: cnt+=1
print(f"  월 블록 부트스트랩(5000회): 차이가 0 이상으로 뒤집히는 비율 {cnt/NB*100:.1f}%  (관측 {obs:+.2f}%p)")
