import json, statistics as st
from collections import defaultdict
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
m=json.load(open(root+r'\public\data\market-regime.json',encoding='utf-8'))['series']
dates=[r['date'] for r in m]
sk=[]; s=0
for r in m:
    s=s+1 if r['up'] else 0; sk.append(s)
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
pos={dt:i for i,dt in enumerate(dates)}
def rule_gain(shift,thr=12):
    keep=[];skip=[]
    for dt in days:
        i=pos.get(dt)
        if i is None: continue
        v=sk[(i+shift)%len(sk)]
        (skip if v>=thr else keep).extend(byday[dt])
    if not keep or not skip: return None
    wk=100*sum(1 for e in keep if e['result']=='win')/len(keep)
    wa=100*sum(1 for e in keep+skip if e['result']=='win')/len(keep+skip)
    return wk-wa
obs=rule_gain(0)
null=[rule_gain(s) for s in range(5,len(sk)-5)]
null=[x for x in null if x is not None]
p=sum(1 for x in null if x>=obs)/len(null)
print(f'streak>=12 버리기: 관측 승률개선 {obs:+.2f}%p, 순환이동 귀무 {len(null)}개 중 평균 {st.mean(null):+.2f}%p, p={p:.3f}')
# 버리는 날이 몇 개의 '에피소드'인가
sd=[dt for dt in days if sk[pos[dt]]>=12]
eps=[]; prev=None
for dt in sd:
    if prev is None or (pos[dt]-pos[prev])>5: eps.append([dt])
    else: eps[-1].append(dt)
    prev=dt
print('버리는 날 %d일 = 연속 에피소드 %d개:'%(len(sd),len(eps)), [ (g[0],g[-1],len(g)) for g in eps])
