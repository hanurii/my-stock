import json, random, statistics as st
from collections import defaultdict
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
sizes=[len(byday[dt]) for dt in days]
pool=[e for dt in days for e in byday[dt]]
def stats(groups):
    wipe=[g for g in groups if all(x['result']=='loss' for x in g)]
    oth=[g for g in groups if not all(x['result']=='loss' for x in g)]
    A=[e for g in wipe for e in g]
    Bl=[e for g in oth for e in g if e['result']=='loss']
    if not A or not Bl: return None
    return (len(wipe), st.median([e['max_gain_pct'] for e in Bl])-st.median([e['max_gain_pct'] for e in A]),
            sum(1 for e in A if e['max_gain_pct']<3)/len(A) - sum(1 for e in Bl if e['max_gain_pct']<3)/len(Bl),
            sum(1 for e in A if e['days_held']<=3)/len(A) - sum(1 for e in Bl if e['days_held']<=3)/len(Bl))
obs=stats([byday[dt] for dt in days])
print('관측: 전멸일수=%d, maxgain중앙차(그밖패배-전멸)=%.2f%%p, 3%%미만비율차=%.3f, 3일이내비율차=%.3f'%obs)
random.seed(7); N=3000
cnt=[0,0,0,0]; dist=[[],[],[],[]]
for _ in range(N):
    random.shuffle(pool); g=[]; i=0
    for s in sizes: g.append(pool[i:i+s]); i+=s
    r=stats(g)
    if r is None: continue
    for k in range(4):
        dist[k].append(r[k])
        if r[k]>=obs[k]: cnt[k]+=1
names=['전멸일수','maxgain중앙차','3%미만비율차','3일이내비율차']
for k in range(4):
    print(f'{names[k]:14s} 관측 {obs[k]:7.3f}  귀무평균 {st.mean(dist[k]):7.3f}  p(단측)={cnt[k]/len(dist[k]):.4f}')
