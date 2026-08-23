import json, statistics as st, math
from collections import defaultdict
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
m=json.load(open(root+r'\public\data\market-regime.json',encoding='utf-8'))['series']
# up streak (연속으로 20일선 위에 있던 일수) — 전멸일 주석의 '상승연속 N일' 후보 정의
streak={}; s=0
idx={}
for i,r in enumerate(m):
    s = s+1 if r['up'] else 0
    streak[r['date']]=s
    idx[r['date']]=r['index']
dates=[r['date'] for r in m]
pos={dt:i for i,dt in enumerate(dates)}
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
wipe=set(dt for dt in days if all(x['result']=='loss' for x in byday[dt]))
print('전멸일 streak:', [(dt,streak.get(dt,'NA')) for dt in sorted(wipe)])
print()
# 기저율
def cnt(dts,thr): return sum(1 for dt in dts if streak.get(dt,0)>=thr)
for thr in (5,9,12):
    w=cnt(sorted(wipe),thr); o=cnt([dt for dt in days if dt not in wipe],thr)
    print(f'streak>={thr}: 전멸일 {w}/14 = {100*w/14:.0f}%   그밖의날 {o}/57 = {100*o/57:.0f}%')
print()
# streak 구간별 승률 (같은날 기준 아님 — 날 단위 집계)
bins=[(0,0),(1,4),(5,8),(9,14),(15,100)]
print('구간별  일수  거래수  승률   전멸일수')
for lo,hi in bins:
    dd=[dt for dt in days if lo<=streak.get(dt,0)<=hi]
    tr=[e for dt in dd for e in byday[dt]]
    if not tr: continue
    w=sum(1 for e in tr if e['result']=='win')
    wp=sum(1 for dt in dd if dt in wipe)
    print(f'{lo}~{hi}: {len(dd):4d}일 {len(tr):5d}건 {100*w/len(tr):5.1f}% 전멸 {wp}일')
