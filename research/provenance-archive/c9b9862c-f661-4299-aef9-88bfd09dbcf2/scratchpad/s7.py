import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
for e in EV:
    p,en,r=e['pivot'],e['entry_price'],e['result']
    ex = p*1.20 if r=='win' else (p*0.90 if r in ('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
    e['_full']=ex/en-1
byday=defaultdict(list)
for e in EV: byday[e['entry_date']].append(e)
rnd=random.Random(3)
def stat(order_key_shuffle=False):
    A=[];B=[]
    for d,xs in byday.items():
        if len(xs)<3: continue
        s=list(xs)
        if order_key_shuffle: rnd.shuffle(s)
        else: s=sorted(s,key=lambda e:-e['turnover_eok'])
        k=max(1,len(s)//3)
        A+=[e['_full'] for e in s[:k]]; B+=[e['_full'] for e in s[k:]]
    return statistics.mean(A)-statistics.mean(B)
obs=stat()
sims=[stat(True) for _ in range(3000)]
print(f'거래대금 상위1/3 금전우위 {obs*100:+.2f}%p | 같은날 순서섞기 {statistics.mean(sims)*100:+.2f}±{statistics.pstdev(sims)*100:.2f}  p={sum(1 for s in sims if s>=obs)/len(sims):.4f}')
# 갭업 차이
A=[];B=[]
for d,xs in byday.items():
    if len(xs)<3: continue
    s=sorted(xs,key=lambda e:-e['turnover_eok']); k=max(1,len(s)//3)
    A+=s[:k]; B+=s[k:]
for nm,f in [('gap_up_pct',lambda e:e['gap_up_pct']),('entry/pivot',lambda e:e['entry_price']/e['pivot']),('승률',lambda e:1.0 if e['result']=='win' else 0.0),('atr',lambda e:e['atr_pct'])]:
    print(f'  {nm}: 상위1/3 {statistics.mean(f(e) for e in A):.4f} vs 나머지 {statistics.mean(f(e) for e in B):.4f}')
# 종목 블록 부트스트랩
bycode=defaultdict(list)
for e in EV: bycode[e['code']].append(e)
codes=list(bycode)
def stat_codes(cs):
    keep=set()
    cnt=defaultdict(int)
    for c in cs: cnt[c]+=1
    A=[];B=[]
    for d,xs in byday.items():
        if len(xs)<3: continue
        s=sorted(xs,key=lambda e:-e['turnover_eok']); k=max(1,len(s)//3)
        for e in s[:k]: A+= [e['_full']]*cnt[e['code']]
        for e in s[k:]: B+= [e['_full']]*cnt[e['code']]
    return (statistics.mean(A)-statistics.mean(B)) if A and B else 0
bs=sorted(stat_codes([rnd.choice(codes) for _ in codes]) for _ in range(1500))
print(f'  종목블록 부트스트랩 95%CI [{bs[37]*100:+.2f}, {bs[1462]*100:+.2f}]%p')
