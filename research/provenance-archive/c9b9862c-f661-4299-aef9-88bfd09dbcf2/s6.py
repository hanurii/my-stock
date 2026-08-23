import json, statistics
from math import comb
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
def bt(k,n):
    probs=[comb(n,i)*0.5**n for i in range(n+1)]; o=probs[k]
    return sum(pr for pr in probs if pr<=o*(1+1e-9))
def signtest(pool, minday, frac, ambloss):
    byday=defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    up=dn=tie=0
    for d,xs in byday.items():
        if len(xs)<minday: continue
        s=sorted(xs,key=lambda e:-e['turnover_eok'])
        k=max(1,int(len(s)*frac))
        a,b=s[:k],s[k:]
        if not b: continue
        def w(g): return sum(1 for x in g if x['result']=='win')/len(g)
        if w(a)>w(b): up+=1
        elif w(a)<w(b): dn+=1
        else: tie+=1
    return up,dn,tie
for ambloss in [False,True]:
    pool=[e for e in EV if e['result'] in ('win','loss')] if not ambloss else [e for e in EV if e['result']!='unresolved']
    for minday in [2,3,4]:
        for frac in [1/3,0.5]:
            u,dd,t=signtest(pool,minday,frac,ambloss)
            print(f'amb포함={ambloss} 최소{minday}건 상위{frac:.2f}: {u}승{dd}패 동률{t} p={bt(min(u,dd),u+dd):.3f}')
