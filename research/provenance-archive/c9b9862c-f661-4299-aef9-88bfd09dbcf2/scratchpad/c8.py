# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, random
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']
def sim(byd_days, keyname, block, slots=5):
    cap=100.0; op=[]; tk=0
    for d in byd_days[0]:
        stay=[]
        for rd,amt,net in op:
            if rd<=d: cap+=amt*(1+net/100)
            else: stay.append((rd,amt,net))
        op=stay
        for e in byd_days[1].get(d,[]):
            if block(e) or len(op)>=slots: continue
            size=cap/slots
            if size<=0: continue
            size=min(size,cap); cap-=size
            op.append((e['resolve_date'],size,e['net'])); tk+=1
    for rd,amt,net in op: cap+=amt*(1+net/100)
    return cap-100, tk
NOBLK=lambda e: False
BLK=lambda e: e['_reg'] is False and e['_nq'] is True
base=[];rule=[];diff=[]
for seed in range(300):
    rnd=random.Random(seed)
    for e in EV: e['_k']=rnd.random()
    byd=collections.defaultdict(list)
    for e in EV: byd[e['entry_date']].append(e)
    for d in byd: byd[d].sort(key=lambda e:e['_k'])
    days=[d for d in rdates if d>=min(byd)]
    a,_=sim((days,byd),'_k',NOBLK); b,_=sim((days,byd),'_k',BLK)
    base.append(a); rule.append(b); diff.append(b-a)
def q(v,p): 
    s=sorted(v); return s[int(len(s)*p)]
print("★ 슬롯5 자산곡선은 '하루 후보 중 누구를 담느냐'(동점 처리)에 엄청나게 민감 — 300회 무작위")
print(f"  현행    중앙 {st.median(base):+7.1f}%  10%분위 {q(base,.1):+7.1f}%  90%분위 {q(base,.9):+7.1f}%  (음수 비율 {sum(1 for x in base if x<0)/3:.0f}%)")
print(f"  규칙적용 중앙 {st.median(rule):+7.1f}%  10%분위 {q(rule,.1):+7.1f}%  90%분위 {q(rule,.9):+7.1f}%  (음수 비율 {sum(1 for x in rule if x<0)/3:.0f}%)")
print(f"  ★같은 순서 짝비교 개선 {sum(1 for x in diff if x>0)}/300회 ({sum(1 for x in diff if x>0)/3:.0f}%), 차이 중앙 {st.median(diff):+.1f}%p (10%분위 {q(diff,.1):+.1f} / 90%분위 {q(diff,.9):+.1f})")
print(f"  참고: 확정 사실의 '-20.7%'는 이 분포의 {sum(1 for x in base if x<-20.7)/3:.0f}%분위 근처 — 즉 자산곡선 수치 자체가 동점처리 하나로 ±수십%p 흔들림")
