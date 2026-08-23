import json, random, statistics
from math import comb
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
for e in EV:
    p,en,r=e['pivot'],e['entry_price'],e['result']
    ex = p*1.20 if r=='win' else (p*0.90 if r in ('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
    e['_full']=ex/en-1
def bt(k,n):
    probs=[comb(n,i)*0.5**n for i in range(n+1)]; o=probs[k]
    return sum(pr for pr in probs if pr<=o*(1+1e-9))
res=[e for e in EV if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
print('=== 거래대금 상대순위(그날 상위1/3 vs 하위2/3) 같은날 승률 비교 ===')
for half in [('전체',lambda d:True),('전반',lambda d:d<'2026-03-25'),('후반',lambda d:d>='2026-03-25')]:
    up=dn=tie=0; diffs=[]
    for d,xs in byday.items():
        if not half[1](d) or len(xs)<3: continue
        s=sorted(xs,key=lambda e:-e['turnover_eok'])
        k=max(1,len(s)//3); a,b=s[:k],s[k:]
        if not b: continue
        wa=sum(1 for x in a if x['result']=='win')/len(a); wb=sum(1 for x in b if x['result']=='win')/len(b)
        diffs.append(wa-wb)
        if wa>wb: up+=1
        elif wa<wb: dn+=1
        else: tie+=1
    n=up+dn
    print(f'{half[0]}: {up}승{dn}패 (동률{tie}) p={bt(min(up,dn),n):.4f} 평균차 {statistics.mean(diffs)*100:+.1f}%p')
print()
print('=== 같은날 거래대금 1등 vs 나머지 ===')
up=dn=tie=0
for d,xs in byday.items():
    if len(xs)<2: continue
    s=sorted(xs,key=lambda e:-e['turnover_eok']); a,b=s[:1],s[1:]
    wa=1.0 if a[0]['result']=='win' else 0.0; wb=sum(1 for x in b if x['result']=='win')/len(b)
    if wa>wb: up+=1
    elif wa<wb: dn+=1
    else: tie+=1
print(f'1등 {up}승{dn}패 (동률{tie}) p={bt(min(up,dn),up+dn):.3f}')
print()
print('=== 거래대금 상위1/3의 금전(1건당 수익) — 같은날 내 ===')
byday2=defaultdict(list)
for e in EV: byday2[e['entry_date']].append(e)
for half in [('전체',lambda d:True),('전반',lambda d:d<'2026-03-25'),('후반',lambda d:d>='2026-03-25')]:
    A=[];B=[]
    for d,xs in byday2.items():
        if not half[1](d) or len(xs)<3: continue
        s=sorted(xs,key=lambda e:-e['turnover_eok']); k=max(1,len(s)//3)
        A+= [e['_full'] for e in s[:k]]; B+=[e['_full'] for e in s[k:]]
    print(f'{half[0]}: 상위1/3 {statistics.mean(A)*100:+.2f}% (n={len(A)}) vs 나머지 {statistics.mean(B)*100:+.2f}% (n={len(B)})  차 {(statistics.mean(A)-statistics.mean(B))*100:+.2f}%p')
