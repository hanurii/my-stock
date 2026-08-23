import json, math
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
ev=json.load(open(SP+'feat.json',encoding='utf-8'))
res=[e for e in ev if e['result'] in ('win','loss')]
def binom_two_sided(k,n,p=0.5):
    # exact two-sided sign test
    from math import comb
    probs=[comb(n,i)*p**i*(1-p)**(n-i) for i in range(n+1)]
    obs=probs[k]
    return sum(pr for pr in probs if pr<=obs*(1+1e-9))
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
print('days total', len(byday))
for cut in [2,1,0,-1,-2,-3]:
    up=dn=tie=0; diffs=[]
    for d,xs in byday.items():
        a=[x for x in xs if x['d1_ret']>=cut]; b=[x for x in xs if x['d1_ret']<cut]
        if not a or not b: continue
        wa=sum(1 for x in a if x['result']=='win')/len(a)
        wb=sum(1 for x in b if x['result']=='win')/len(b)
        diffs.append(wa-wb)
        if wa>wb: up+=1
        elif wa<wb: dn+=1
        else: tie+=1
    n=up+dn
    p=binom_two_sided(min(up,dn),n) if n else 1
    print(f'cut {cut:>3}: 같은날 비교일 {len(diffs)} (동률 {tie}) 위>아래 {up}승{dn}패  p={p:.2g}  평균차 {sum(diffs)/len(diffs)*100:.1f}%p')
