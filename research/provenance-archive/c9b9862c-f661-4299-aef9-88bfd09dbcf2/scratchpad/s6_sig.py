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
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}; KOS=dict(zip(REG['dates'],REG['kospi']))
def before(k):
    i=bisect.bisect_left(nqd,k); return nqd[i-1]
for e in EV:
    e['net']=FEE(e['gain_at_resolve_pct']); e['nq']=NQ['up'][before(e['entry_date'])]; e['reg']=UP.get(e['scan_date'])

def daycluster(sub):
    byd=collections.defaultdict(list)
    for e in sub: byd[(e['entry_date'],e['nq'])].append(e['net'])
    A=[st.mean(v) for (d,l),v in byd.items() if l]; Bd=[st.mean(v) for (d,l),v in byd.items() if not l]
    d=st.mean(A)-st.mean(Bd); se=(st.variance(A)/len(A)+st.variance(Bd)/len(Bd))**0.5
    return d,d/se,len(A),len(Bd)
print("="*90); print("⑧ 부분집합별 일단위 클러스터 검정 (t>2 라야 유의)"); print("="*90)
for lab,sub in (('전체',EV),
                ('상승국면만',[e for e in EV if e['reg'] is True]),
                ('조정국면만',[e for e in EV if e['reg'] is False]),
                ('2021-2024',[e for e in EV if e['entry_date'][:4]<'2025']),
                ('2025-2026',[e for e in EV if e['entry_date'][:4]>='2025'])):
    d,t,na,nb=daycluster(sub)
    print(f"  {lab:<12} 일평균차 {d:>+7.2f}%p  t={t:>+6.2f}  {'유의' if abs(t)>1.96 else '무의미(노이즈)'}   ({na}일/{nb}일)")

# 연도 부호검정
sg=[]
for y in ('2021','2022','2023','2024','2025','2026'):
    a=[e['net'] for e in EV if e['entry_date'][:4]==y and e['nq']]; b=[e['net'] for e in EV if e['entry_date'][:4]==y and not e['nq']]
    sg.append(st.mean(a)-st.mean(b))
neg=sum(1 for s in sg if s<0)
print(f"\n  연도 부호검정: 음 {neg}/6 → 양측 p={2*sum(__import__('math').comb(6,k) for k in range(neg,7))/64:.3f} (동전던지기와 구분 안 됨)" if neg>=3 else "")

# ---- 자산곡선 재현
def sim(events, slots=5, seed=0, filt=None):
    pool=[e for e in events if (filt is None or filt(e))]
    byday=collections.defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; n=0; w=0
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in pool]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq += wg*e['net']/100; n+=1; w+= e['result']=='win'
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100, n, (w/n*100 if n else 0)
print("\n"+"="*90); print("⑨ 슬롯5 자산곡선 재현 (200회 무작위 배정, 중앙값)"); print("="*90)
def band(f,N=200):
    r=sorted(f(i)[0] for i in range(N)); return r[N//2], r[N//20], r[-N//20]
for lab,filt in (('① 전부 매수',None),
                 ('② 나스닥 상승일만',lambda e: e['nq']),
                 ('③ 나스닥 하락일만',lambda e: not e['nq'])):
    md,lo,hi=band(lambda s: sim(EV,seed=s,filt=filt))
    print(f"  {lab:<20} 최종 {md:>+8.1f}%   (5~95%: {lo:+.0f}% ~ {hi:+.0f}%)")
d0=min(e['entry_date'] for e in EV); d1=max(e['resolve_date'] for e in EV)
ks=(KOS[max(d for d in REG['dates'] if d<=d1)]/KOS[min(d for d in REG['dates'] if d>=d0)]-1)*100
print(f"\n  기간 {d0} ~ {d1}   코스피 {ks:+.1f}%")
