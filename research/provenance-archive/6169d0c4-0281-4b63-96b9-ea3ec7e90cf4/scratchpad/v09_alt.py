# -*- coding: utf-8 -*-
"""연속 판정 시점: 당일 결착 포함(<=d) vs 미포함(<d) — 어느 쪽이 파일 값과 맞는가."""
import json, collections, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
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
                      'entry_date':p['entry_date'],'resolve_date':p['dates'][i],'result':lb})
    del d
byday=collections.defaultdict(list)
for t in paths: byday[t['entry_date']].append(t)
dates=sorted(set(list(byday)+[t['resolve_date'] for t in paths]))

def run(seed, mode, same_day):
    held=[]; streak=0; bought=[]; trig=set()
    for d in dates:
        if same_day:
            done=[x for x in held if x[0]<=d]; held=[x for x in held if x[0]>d]
        else:
            done=[x for x in held if x[0]<d];  held=[x for x in held if x[0]>=d]
        for rd,t in sorted(done,key=lambda x:(x[0],x[1]['code'])):
            streak = 0 if t['result']=='win' else streak+1
        if streak>=5:
            trig.add(d)
            if mode=='na': streak=0
        free=5-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; c.sort(key=lambda t: slot_sim.order_key(seed,t))
            for t in c[:free]:
                held.append((t['resolve_date'],t)); bought.append((d,t))
    return bought, trig

for same_day in (False, True):
    tot=tw=0; agg={'ga':[0,0],'na':[0,0]}
    for s in range(200):
        for mode in ('ga','na'):
            b,tg = run(s, mode, same_day)
            if mode=='ga':
                tot+=len(b); tw+=sum(1 for _,t in b if t['result']=='win')
            for d,t in b:
                if d in tg: agg[mode][0]+=1; agg[mode][1]+= t['result']=='win'
    print("당일 결착 %s → 전체 %d (승률 %.3f%%)" % ("포함(<=d)" if same_day else "미포함(<d)", tot, 100*tw/tot))
    for mode,lab,exp in (('ga','판(가)','12,797 / 38.150'),('na','판(나)','4,160 / 36.322')):
        n,w=agg[mode]
        print("   %s 발동일 매수 %5d · 승률 %.3f%%  (파일 %s)" % (lab,n,100*w/n,exp))
