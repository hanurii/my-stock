# -*- coding: utf-8 -*-
import json, glob, os, bisect, collections, statistics as st, random
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8')); nqd=sorted(NQ['up'])
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    EV+=[e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV=U
for e in EV:
    e['net']=FEE(e['gain_at_resolve_pct']); e['nq']=NQ['up'][nqd[bisect.bisect_left(nqd,e['entry_date'])-1]]
def sim(pool,slots=5,seed=0):
    byday=collections.defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in pool]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]: eq+=wg*e['net']/100
        held=[h for h in held if h[0]>d]
        fr=slots-len(held)
        if fr>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:fr]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100
def med(p,N=41):
    r=sorted(sim(p,seed=s) for s in range(N)); return r[N//2]
print("="*88); print("⑩ 전·후반 분할 (앞 절반에서 본 걸 뒤 절반이 재현하는가)"); print("="*88)
for lab,lo,hi in (('전반 2021-2023','2021','2024'),('후반 2024-2026','2024','2027')):
    sub=[e for e in EV if lo<=e['entry_date'][:4]<hi]
    a=[e for e in sub if e['nq']]; b=[e for e in sub if not e['nq']]
    print(f"  {lab}: 상승일만 {med(a):>+7.1f}%  하락일만 {med(b):>+7.1f}%  격차 {med(a)-med(b):>+7.1f}%p  |"
          f"  거래당 {st.mean([x['net'] for x in a]):+.2f}% vs {st.mean([x['net'] for x in b]):+.2f}%")
print("\n"+"="*88); print("⑪ 원형이동 순열 밀도 상향 (자산곡선)"); print("="*88)
days=sorted({e['entry_date'] for e in EV})
lab0=[NQ['up'][nqd[bisect.bisect_left(nqd,d)-1]] for d in days]
def split(L):
    S=dict(zip(days,L)); return [e for e in EV if S[e['entry_date']]],[e for e in EV if not S[e['entry_date']]]
A,Bq=split(lab0); obs=med(A)-med(Bq)
cnt=tot=0; dist=[]
for sh in range(10,len(days)-10,3):
    a,b=split(lab0[sh:]+lab0[:sh])
    if len(a)<300 or len(b)<300: continue
    d=med(a,11)-med(b,11); dist.append(d); tot+=1
    if d<=obs: cnt+=1
dist.sort()
print(f"  관측 {obs:+.1f}%p   순열 {tot}회 중앙 {dist[len(dist)//2]:+.1f}%p  5%={dist[len(dist)//20]:+.1f}  95%={dist[-max(1,len(dist)//20)]:+.1f}")
print(f"  더 극단(음) {cnt}/{tot} → 단측 p={(cnt+1)/(tot+1):.3f}")
print(f"\n  ※ 순열 중앙값이 0이 아니라 {dist[len(dist)//2]:+.1f}%p → 이 지표는 대칭이 아님(라벨 True 쪽 거래가 더 많아 생기는 구조적 쏠림)")
