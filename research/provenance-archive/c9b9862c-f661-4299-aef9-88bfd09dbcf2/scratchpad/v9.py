import json, math, random
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
byday=defaultdict(list)
upday={}
for x in D['events']:
    if x['result'] in ('win','loss'):
        byday[x['entry_date']].append(1 if x['result']=='win' else 0)
        upday[x['entry_date']]=reg[x['scan_date']]
days=sorted(byday); idx={d:i for i,d in enumerate(days)}
random.seed(21)
big=[d for d in days if len(byday[d])>=6]
# matched: d has >=6, next entry day d2 has >=3
matched=[]
for d in big:
    i=idx[d]
    if i+1<len(days) and len(byday[days[i+1]])>=3: matched.append((d,days[i+1]))
print('짝 지어진 날 %d개 (6건+ 날 %d개 중)'%(len(matched),len(big)))
T=40000
def run(mode):
    z=0;wsum=0
    for _ in range(T):
        d,d2=random.choice(matched)
        if mode=='same': s=random.sample(byday[d],6)
        elif mode=='next': s=random.sample(byday[d],3)+random.sample(byday[d2],3)
        elif mode=='far':
            while True:
                o=random.choice(days)
                if len(byday[o])>=3 and abs(idx[o]-idx[d])>=10: break
            s=random.sample(byday[d],3)+random.sample(byday[o],3)
        z+= (sum(s)==0); wsum+=sum(s)
    return 100*z/T, wsum/T
for m,l in (('same','같은 날 6개'),('next','그날 3 + 다음 진입일 3'),('far','그날 3 + 10일 이상 떨어진 날 3')):
    p,w=run(m); print('%-26s 전멸확률 %.1f%%  평균 승수 %.2f/6'%(l,p,w))
print()
# same for uptrend-only days
bigU=[d for d in big if upday[d]]
matchedU=[]
for d in bigU:
    i=idx[d]
    if i+1<len(days) and len(byday[days[i+1]])>=3 and upday[days[i+1]]: matchedU.append((d,days[i+1]))
print('상승국면 짝 %d개'%len(matchedU))
matched=matchedU
daysU=[d for d in days if upday[d]]
def runU(mode):
    z=0;wsum=0
    for _ in range(T):
        d,d2=random.choice(matched)
        if mode=='same': s=random.sample(byday[d],6)
        elif mode=='next': s=random.sample(byday[d],3)+random.sample(byday[d2],3)
        else:
            while True:
                o=random.choice(daysU)
                if len(byday[o])>=3 and abs(idx[o]-idx[d])>=10: break
            s=random.sample(byday[d],3)+random.sample(byday[o],3)
        z+= (sum(s)==0); wsum+=sum(s)
    return 100*z/T, wsum/T
for m,l in (('same','[상승] 같은 날 6개'),('next','[상승] 그날 3 + 다음날 3'),('far','[상승] 그날 3 + 먼 날 3')):
    p,w=runU(m); print('%-26s 전멸확률 %.1f%%  평균 승수 %.2f/6'%(l,p,w))
