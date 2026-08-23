# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, math, random
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']; ridx={d:i for i,d in enumerate(rdates)}
KS=dict(zip(rdates,R['kospi']))
A=[e for e in EV if e['_reg'] is False and e['_nq'] is True]
Bc=[e for e in EV if e['_reg'] is False and e['_nq'] is False]
# 승률 차이 유의성 — 일 단위 블록 부트스트랩
byday=collections.defaultdict(list)
for e in EV:
    if e['_reg'] is False: byday[e['entry_date']].append(e)
daysA=sorted({e['entry_date'] for e in A}); daysB=sorted({e['entry_date'] for e in Bc})
def wrp(ev): return sum(1 for x in ev if x['result']=='win')/len(ev) if ev else float('nan')
obs=wrp(A)-wrp(Bc)
p1,p2=wrp(A),wrp(Bc); pp=(235+188)/1297
z=(p1-p2)/math.sqrt(pp*(1-pp)*(1/781+1/516))
print(f"승률차 {p1*100:.1f}% - {p2*100:.1f}% = {obs*100:+.1f}%p, 나이브 z={z:.2f} (p={2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2)))):.4f})")
random.seed(7)
cntw=cntm=0; NB=4000
allday=daysA+daysB
labs={d:True for d in daysA}; labs.update({d:False for d in daysB})
for _ in range(NB):
    sh=random.sample(allday,len(allday))
    la={d:(i<len(daysA)) for i,d in enumerate(sh)}
    a=[x for d in allday if la[d] for x in byday[d]]
    b=[x for d in allday if not la[d] for x in byday[d]]
    if wrp(a)-wrp(b)<=obs: cntw+=1
    d1=st.mean([x['net'] for x in a])-st.mean([x['net'] for x in b])
    if d1<=-1.88: cntm+=1
print(f"일단위 무작위재배치(4000회): 승률차 p={(cntw+1)/(NB+1):.4f}, 거래당차 p={(cntm+1)/(NB+1):.4f}  ※단측·보정전")

# ==== 슬롯5 자산곡선 시뮬 ====
def sim(events, block=None, seed=0, rank='rs'):
    ev=sorted(events,key=lambda e:(e['entry_date'], -e.get('rs',0), e['code']))
    byd=collections.defaultdict(list)
    for e in ev: byd[e['entry_date']].append(e)
    days=[d for d in rdates if d>=min(byd) and d<=max(rdates)]
    cap=100.0; open_pos=[]  # (resolve_date, amount, net)
    taken=0; skipped=0
    for d in days:
        # 청산 먼저
        stay=[]
        for rd,amt,net in open_pos:
            if rd<=d: cap+=amt*(1+net/100)
            else: stay.append((rd,amt,net))
        open_pos=stay
        for e in byd.get(d,[]):
            if block and block(e): skipped+=1; continue
            if len(open_pos)>=5: continue
            size=cap/ (5-len(open_pos)) if False else cap/5
            # 표준: 자본의 1/5을 편입 (빈 슬롯 있을 때)
            size=min(size, cap)
            if size<=0: continue
            cap-=size; open_pos.append((e['resolve_date'], size, e['net'])); taken+=1
    for rd,amt,net in open_pos: cap+=amt*(1+net/100)
    return cap-100, taken, skipped
tot,tk,sk=sim(EV)
tot2,tk2,sk2=sim(EV, block=lambda e: e['_reg'] is False and e['_nq'] is True)
d0=min(e['entry_date'] for e in EV); d1=max(e['resolve_date'] for e in EV)
ks=(KS[max(k for k in KS if k<=d1)]/KS[min(k for k in KS if k>=d0)]-1)*100
print(f"\n슬롯5 시뮬(자본1/5, 재현): 전체 {tot:+.1f}% (체결 {tk}건) / 같은기간 코스피 {ks:+.1f}%")
print(f"슬롯5 시뮬(조정+NQ상승 금지) : {tot2:+.1f}% (체결 {tk2}건, 건너뜀 {sk2}건)")
