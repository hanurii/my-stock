import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
res=[e for e in EV if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
d4=[(d,xs) for d,xs in byday.items() if len(xs)>=4]
print('4건+ 진입일', len(d4), '전멸(0승)', sum(1 for d,xs in d4 if not any(x['result']=='win' for x in xs)))
d6=[(d,xs) for d,xs in byday.items() if len(xs)>=6]
print('6건+ 진입일', len(d6))
rnd=random.Random(5)
wipe=0; sweep=0; tot=0
for d,xs in d6:
    for _ in range(2000):
        s=rnd.sample(xs,6); tot+=1
        w=sum(1 for x in s if x['result']=='win')
        if w==0: wipe+=1
        if w==6: sweep+=1
print(f'6건+ 날에서 6개 무작위 추출: 전멸 {wipe/tot*100:.1f}%, 전승 {sweep/tot*100:.1f}% (표본일 {len(d6)})')
# 거래대금순 상위6 선택 시
wipe2=sum(1 for d,xs in d6 if not any(x['result']=='win' for x in sorted(xs,key=lambda e:-e['turnover_eok'])[:6]))
print(f'거래대금 상위6 선택 시 전멸 {wipe2}/{len(d6)} = {wipe2/len(d6)*100:.1f}%')
# 같은날 상관 rho 추정 (일별 승률의 과분산)
import math
p=sum(1 for e in res if e['result']=='win')/len(res)
num=0; den=0
for d,xs in byday.items():
    n=len(xs)
    if n<2: continue
    k=sum(1 for x in xs if x['result']=='win')
    num += k*(k-1) ; den += n*(n-1)
pair = num/den
rho = (pair - p*p)/(p*(1-p))
print(f'전체승률 p={p:.3f}  같은날 두 종목 동시승 확률 {pair:.3f} (독립이면 {p*p:.3f}) → rho={rho:.3f}')
