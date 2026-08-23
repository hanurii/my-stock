import json, math
from collections import Counter, defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
y=[1 if x['result']=='win' else 0 for x in ev]
g=[1 if reg[x['scan_date']] else 0 for x in ev]
n=len(y)
my=sum(y)/n; mg=sum(g)/n
cov=sum((a-my)*(b-mg) for a,b in zip(y,g))/n
sy=math.sqrt(sum((a-my)**2 for a in y)/n); sg=math.sqrt(sum((b-mg)**2 for b in g)/n)
r=cov/(sy*sg)
print('phi/r=%.4f  R2=%.4f%%'%(r, 100*r*r))
# chi2 2x2
a=sum(1 for i in range(n) if g[i]==1 and y[i]==1); b=sum(1 for i in range(n) if g[i]==1 and y[i]==0)
c=sum(1 for i in range(n) if g[i]==0 and y[i]==1); d=sum(1 for i in range(n) if g[i]==0 and y[i]==0)
print('table up(w,l)=',a,b,'dn(w,l)=',c,d)
chi2=n*(a*d-b*c)**2/((a+b)*(c+d)*(a+c)*(b+d))
print('chi2=%.2f'%chi2, 'phi2=%.4f%%'%(100*chi2/n))
