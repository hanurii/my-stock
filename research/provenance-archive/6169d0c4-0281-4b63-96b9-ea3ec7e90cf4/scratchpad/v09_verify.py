# -*- coding: utf-8 -*-
"""09 독립 재현 — 쉼 규칙 두 읽기·자기잠금·1순위 통계."""
import json, collections, statistics as st, random, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = slot_sim.net
paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E=p['entry_price']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=(i,'loss'); break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=r
        paths.append({'code':p['code'],'pattern':p['pattern'],'scan_date':p['scan_date'],
                      'entry_date':p['entry_date'],'resolve_date':p['dates'][i],
                      'gain':(c[i]/E-1)*100,'result':lb})
    del d
print("유니버스 %d건" % len(paths))
byday=collections.defaultdict(list)
for t in paths: byday[t['entry_date']].append(t)
dates=sorted(set(list(byday)+[t['resolve_date'] for t in paths]))

def sim(seed, mode=None, N=5, M=1, slots=5):
    """mode=None 규칙없음 · 'ga' 문자그대로 · 'na' 발동시 카운터 초기화"""
    held=[]; streak=0; block_until=-1; bought=[]; trig=set()
    for di,d in enumerate(dates):
        done=[x for x in held if x[0]<d]; held=[x for x in held if x[0]>=d]
        for rd,t in sorted(done,key=lambda x:(x[0],x[1]['code'])):
            streak = 0 if t['result']=='win' else streak+1
        fire = streak>=N
        if fire:
            trig.add(d)
            if mode=='na': streak=0
            if mode: block_until=di+M
        blocked = mode is not None and di<block_until
        free=slots-len(held)
        if free>0 and d in byday and not blocked:
            c=byday[d][:]
            c.sort(key=lambda t: slot_sim.order_key(seed,t))
            for t in c[:free]:
                held.append((t['resolve_date'],t)); bought.append((d,t))
    return bought, trig

NS=200
tot=0; tw=0; agg={'ga':[0,0],'na':[0,0]}; trigdays={'ga':set(),'na':set()}
fills={'none':[], 'ga':[], 'na':[]}
for s in range(NS):
    b0,_=sim(s,None); fills['none'].append(len(b0))
    tot+=len(b0); tw+=sum(1 for _,t in b0 if t['result']=='win')
    for mode in ('ga','na'):
        _,tg = sim(s,None) if False else (None,None)
        # 발동일은 규칙 없음 타임라인에서 판정 (두 읽기 차이는 카운터 처리)
        held=[]; streak=0; tg=set()
        for d in dates:
            done=[x for x in held if x[0]<d]; held=[x for x in held if x[0]>=d]
            for rd,t in sorted(done,key=lambda x:(x[0],x[1]['code'])):
                streak = 0 if t['result']=='win' else streak+1
            if streak>=5:
                tg.add(d)
                if mode=='na': streak=0
            free=5-len(held)
            if free>0 and d in byday:
                c=byday[d][:]; c.sort(key=lambda t: slot_sim.order_key(s,t))
                for t in c[:free]: held.append((t['resolve_date'],t))
        trigdays[mode]|=tg
        for d,t in b0:
            if d in tg:
                agg[mode][0]+=1; agg[mode][1]+= t['result']=='win'
    if s<3:
        bg,_=sim(s,'ga'); bn,_=sim(s,'na')
        fills['ga'].append(len(bg)); fills['na'].append(len(bn))
print("\n[자기잠금] seed 0~2 체결: 규칙없음 %s · 판(가) %s · 판(나) %s   (파일 434 → 50)"
      % (fills['none'][:3], fills['ga'], fills['na']))
print("\n[1순위] 전체 매수 %d · 전체 승률 %.3f%%  (파일 84,573 / 34.319)" % (tot,100*tw/tot))
for mode,lab in (('ga','판(가)'),('na','판(나)')):
    n,w=agg[mode]
    print("   %s 발동일 매수 %d · 승률 %.3f%% · S %+.3f%%p   (파일 %s)"
          % (lab,n,100*w/n,100*w/n-100*tw/tot,
             "12,797 / 38.150 / +3.830" if mode=='ga' else "4,160 / 36.322 / +2.003"))
    print("      발동일 수(200 seed 합집합) %d" % len(trigdays[mode]))
