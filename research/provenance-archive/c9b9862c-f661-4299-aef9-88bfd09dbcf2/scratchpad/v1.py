import json, math
from collections import Counter, defaultdict

D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
print('resolved',len(ev))

for key in ('scan_date','entry_date'):
    miss=[x for x in ev if x[key] not in reg]
    up=[x for x in ev if reg.get(x[key])]
    dn=[x for x in ev if x[key] in reg and not reg[x[key]]]
    wu=sum(1 for x in up if x['result']=='win'); wd=sum(1 for x in dn if x['result']=='win')
    print(key,'miss',len(miss),'up',len(up),round(100*wu/len(up),1),'dn',len(dn),round(100*wd/len(dn),1))
