# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, random
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']
def sim(events, block, order, slots=5):
    byd=collections.defaultdict(list)
    for e in events: byd[e['entry_date']].append(e)
    for d in byd: byd[d]=order(byd[d])
    days=[d for d in rdates if d>=min(byd)]
    cap=100.0; op=[]; tk=0
    for d in days:
        stay=[]
        for rd,amt,net in op:
            if rd<=d: cap+=amt*(1+net/100)
            else: stay.append((rd,amt,net))
        op=stay
        for e in byd.get(d,[]):
            if block(e): continue
            if len(op)>=slots: continue
            size=cap/slots
            if size<=0 or size>cap: size=cap
            cap-=size; op.append((e['resolve_date'],size,e['net'])); tk+=1
    for rd,amt,net in op: cap+=amt*(1+net/100)
    return cap-100, tk
NOBLK=lambda e: False
BLK=lambda e: e['_reg'] is False and e['_nq'] is True
res={'base':[], 'rule':[]}
for seed in range(60):
    rnd=random.Random(seed)
    o=lambda L: sorted(L,key=lambda e:rnd.random())
    a,_=sim(EV,NOBLK,o); b,_=sim(EV,BLK,o)
    res['base'].append(a); res['rule'].append(b)
def s(v): return f"중앙 {st.median(v):+.1f}%  평균 {st.mean(v):+.1f}%  범위 {min(v):+.1f}~{max(v):+.1f}%"
print("슬롯5, 하루 후보 무작위 순서 60회:")
print(f"  현행(전부매수)          : {s(res['base'])}")
print(f"  조정+NQ상승 금지        : {s(res['rule'])}")
print(f"  개선된 시행 {sum(1 for a,b in zip(res['base'],res['rule']) if b>a)}/60회")
print()
for rank,key in [('RS 높은순',lambda e:-e['rs']),('거래대금 큰순',lambda e:-e['turnover_eok']),('ATR 낮은순',lambda e:e['atr_pct'])]:
    o=lambda L: sorted(L,key=key)
    a,ta=sim(EV,NOBLK,o); b,tb=sim(EV,BLK,o)
    print(f"  {rank:<14} 현행 {a:+7.1f}% ({ta}건) / 규칙적용 {b:+7.1f}% ({tb}건)  차 {b-a:+.1f}%p")
print()
# 슬롯 무제한(거래당 성적 그대로 반영되는 세계)
def sim_unlimited(events, block):
    byd=collections.defaultdict(list)
    for e in events:
        if not block(e): byd[e['entry_date']].append(e)
    return sum(e['net'] for d in byd for e in byd[d])/sum(len(v) for v in byd.values())
print(f"참고) 슬롯 무제한 거래당: 현행 {sim_unlimited(EV,NOBLK):+.2f}% / 규칙 {sim_unlimited(EV,BLK):+.2f}%")
print()
# 슬롯 수를 늘리면?
for slots in (5,10,20,40):
    rnd=random.Random(1); o=lambda L: sorted(L,key=lambda e:rnd.random())
    aa=[];bb=[]
    for seed in range(15):
        rnd2=random.Random(seed); o2=lambda L: sorted(L,key=lambda e:rnd2.random())
        aa.append(sim(EV,NOBLK,o2,slots)[0]); bb.append(sim(EV,BLK,o2,slots)[0])
    print(f"  슬롯{slots:>2}: 현행 중앙 {st.median(aa):+7.1f}% / 규칙 중앙 {st.median(bb):+7.1f}%  차 {st.median(bb)-st.median(aa):+.1f}%p")
