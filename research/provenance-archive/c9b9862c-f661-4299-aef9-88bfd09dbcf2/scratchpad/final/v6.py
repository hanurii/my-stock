# -*- coding: utf-8 -*-
import json, statistics as st, math, collections
ROOT='C:/Users/hanul/playground/my-stock/'
j=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
EV=[e for e in j['events'] if e['result'] in ('win','loss')]
REG={p['date']:p['up'] for p in json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']}
FB,FS=0.0014,0.0014+0.002
net=lambda g:((1+g/100)*(1-FS)/(1+FB)-1)*100
def stat(s,lab):
    r=[net(e['gain_at_resolve_pct']) for e in s]
    se=st.stdev(r)/math.sqrt(len(r))
    print('%-12s n=%3d  건당순 %+.2f%%  표준편차 %.1f  표준오차 ±%.2f%%p  t=%.2f  승률 %.1f%%'%(
        lab,len(r),st.mean(r),st.stdev(r),se,st.mean(r)/se,100*sum(1 for e in s if e['result']=='win')/len(s)))
stat(EV,'전체580')
stat([e for e in EV if REG.get(e['scan_date'],True)],'상승국면433')
stat([e for e in EV if not REG.get(e['scan_date'],True)],'조정국면147')
# 손익비 구조
w=[net(e['gain_at_resolve_pct']) for e in EV if e['result']=='win']
l=[net(e['gain_at_resolve_pct']) for e in EV if e['result']=='loss']
print('\n승 %d건 평균 %+.2f%% / 패 %d건 평균 %+.2f%%  → 손익비 %.2f, 손익분기 승률 %.1f%%'%(
    len(w),st.mean(w),len(l),st.mean(l),st.mean(w)/abs(st.mean(l)), 100*abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))))
# 패턴별/월별
print('\n패턴별 건당순수익')
by=collections.defaultdict(list)
for e in EV: by[e['pattern']].append(net(e['gain_at_resolve_pct']))
for k,v in sorted(by.items(), key=lambda x:-len(x[1])): print('  %-12s n=%3d  %+.2f%%'%(k,len(v),st.mean(v)))
