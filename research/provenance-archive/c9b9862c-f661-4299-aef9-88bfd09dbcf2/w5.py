import json, statistics as st, math
from collections import defaultdict, Counter
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
m=json.load(open(root+r'\public\data\market-regime.json',encoding='utf-8'))['series']
dates=[r['date'] for r in m]; pos={dt:i for i,dt in enumerate(dates)}
idx=[r['index'] for r in m]
streak={}; s=0
for r in m:
    s=s+1 if r['up'] else 0; streak[r['date']]=s
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
wipe=set(dt for dt in days if all(x['result']=='loss' for x in byday[dt]))
def fwd(dt,k):
    i=pos.get(dt)
    if i is None or i+k>=len(idx): return None
    return 100*(idx[i+k]/idx[i]-1)
print('== 진입일 이후 지수 수익률 (전멸일 vs 그밖) ==')
for k in (1,3,5,10):
    a=[fwd(dt,k) for dt in sorted(wipe)]; a=[x for x in a if x is not None]
    b=[fwd(dt,k) for dt in days if dt not in wipe]; b=[x for x in b if x is not None]
    print(f'+{k:2d}일: 전멸일 중앙 {st.median(a):6.2f}% (n={len(a)})  그밖 중앙 {st.median(b):6.2f}% (n={len(b)})')
print()
print('== streak>=15 인 날의 달력 분포 (독립적인 사건인가?) ==')
c=Counter(dt[:7] for dt in days if streak.get(dt,0)>=15)
print(dict(sorted(c.items())))
print('그 중 전멸일:', sorted([dt for dt in wipe if streak.get(dt,0)>=15]))
print()
print('== 전멸일 14일의 달력 분포 ==')
print(dict(sorted(Counter(dt[:7] for dt in wipe).items())))
print('전체 71일 분포:', dict(sorted(Counter(dt[:7] for dt in days).items())))
