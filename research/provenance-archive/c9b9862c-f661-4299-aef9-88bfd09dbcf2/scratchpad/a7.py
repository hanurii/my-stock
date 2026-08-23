import json, collections, bisect
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
reg=json.load(open(P+'public/data/market-regime.json',encoding='utf-8'))
up={r['date']:r['up'] for r in reg['series']}; rd=sorted(up)
def isup(k):
    if k in up: return up[k],'exact'
    i=bisect.bisect_left(rd,k)-1
    return (up[rd[i]] if i>=0 else None),'prior'
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
for key in ('scan_date','entry_date'):
    ex=sum(1 for x in ev if x[key] in up)
    w=collections.Counter(); t=collections.Counter()
    for x in ev:
        u,_=isup(x[key]); t[u]+=1; w[u]+= (x['result']=='win')
    print(key, "exact-match trades:",ex,"/",len(ev), {k:(t[k], round(100*w[k]/t[k],1)) for k in t})
