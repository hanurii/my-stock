# -*- coding: utf-8 -*-
import json, collections, statistics as st, math
ROOT='C:/Users/hanul/playground/my-stock/'
j=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
EV=[e for e in j['events'] if e['result'] in ('win','loss')]
ser=json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']
dates=[p['date'] for p in ser]; ups=[bool(p['up']) for p in ser]
FB,FS=0.0014,0.0014+0.002
net=lambda g:((1+g/100)*(1-FS)/(1+FB)-1)*100
scan=[e['scan_date'] for e in EV]; ret=[net(e['gain_at_resolve_pct']) for e in EV]
pos={d:i for i,d in enumerate(dates)}
def diff(labels):
    a=[r for s,r in zip(scan,ret) if s in pos and labels[pos[s]]]
    b=[r for s,r in zip(scan,ret) if s in pos and not labels[pos[s]]]
    if not a or not b: return None
    return st.mean(a)-st.mean(b), len(a), len(b), st.mean(a), st.mean(b)
obs=diff(ups); print('관측: 상승 %d건 %+.2f%% vs 조정 %d건 %+.2f%% → 차이 %+.2f%%p'%(obs[1],obs[3],obs[2],obs[4],obs[0]))
# t검정
a=[r for s,r in zip(scan,ret) if s in pos and ups[pos[s]]]; b=[r for s,r in zip(scan,ret) if s in pos and not ups[pos[s]]]
se=math.sqrt(st.variance(a)/len(a)+st.variance(b)/len(b)); print('t=%.2f (독립가정, 실제론 날짜군집이라 과대)'%(obs[0]/se))
# 원형이동 순열
N=len(ups); cnt=0; tot=0; vals=[]
for k in range(1,N):
    lab=ups[k:]+ups[:k]
    d=diff(lab)
    if d is None: continue
    vals.append(d[0]); tot+=1
    if d[0]>=obs[0]: cnt+=1
vals.sort()
print('원형이동 순열 %d회: 중앙 %+.2f%%p, P90 %+.2f%%p → p=%.3f'%(tot, vals[tot//2], vals[int(tot*0.9)], cnt/tot))
# 월별
by=collections.defaultdict(lambda:[[],[]])
for s,r in zip(scan,ret):
    if s not in pos: continue
    by[s[:7]][0 if ups[pos[s]] else 1].append(r)
print('\n월별 상승국면 vs 조정국면 (건당 순수익)')
for m in sorted(by):
    u,d=by[m]
    print('  %s  상승 %2d건 %+7.2f%%   조정 %2d건 %s'%(m,len(u),st.mean(u) if u else 0,len(d),'%+7.2f%%'%st.mean(d) if d else '   -   '))
