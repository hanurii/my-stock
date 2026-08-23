# -*- coding: utf-8 -*-
"""자산곡선 수준의 원형이동 순열: 나스닥 라벨을 달력째 밀어도 이만한 격차가 나오는가."""
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
for e in EV: e['net']=FEE(e['gain_at_resolve_pct'])
days=sorted({e['entry_date'] for e in EV})
lab0=[NQ['up'][nqd[bisect.bisect_left(nqd,d)-1]] for d in days]

def sim(pool, slots=5, seed=0):
    byday=collections.defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in pool]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]: eq += wg*e['net']/100
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100
def med(pool,N=25): 
    r=sorted(sim(pool,seed=s) for s in range(N)); return r[N//2]

def split(L):
    S={d:l for d,l in zip(days,L)}
    return [e for e in EV if S[e['entry_date']]], [e for e in EV if not S[e['entry_date']]]

A,Bq=split(lab0); obsA, obsB = med(A), med(Bq); obs=obsA-obsB
print(f"관측: 나스닥상승일만 {obsA:+.1f}%  하락일만 {obsB:+.1f}%   격차 {obs:+.1f}%p")
print("\n원형이동 순열 (달력 구조·라벨 비율 보존) ...")
cnt=tot=0; dist=[]
for sh in range(20, len(days)-20, 9):
    L=lab0[sh:]+lab0[:sh]
    a,b=split(L)
    if len(a)<300 or len(b)<300: continue
    d=med(a,15)-med(b,15); dist.append(d); tot+=1
    if d<=obs: cnt+=1
dist.sort()
print(f"  순열 {tot}회:  5%={dist[len(dist)//20]:+.1f}%p  25%={dist[len(dist)//4]:+.1f}  중앙={dist[len(dist)//2]:+.1f}  75%={dist[3*len(dist)//4]:+.1f}  95%={dist[-max(1,len(dist)//20)]:+.1f}%p")
print(f"  관측 {obs:+.1f}%p 보다 더 극단(음)인 순열: {cnt}/{tot}  → 단측 p={(cnt+1)/(tot+1):.3f}")
print(f"  {'❌ 노이즈와 구분 안 됨' if (cnt+1)/(tot+1)>=0.05 else '✅ 유의'}")
