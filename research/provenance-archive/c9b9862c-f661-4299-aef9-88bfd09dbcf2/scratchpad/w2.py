import json, statistics as st
from collections import defaultdict
d=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=[dt for dt,v in byday.items() if len(v)>=4]
wipe=set(dt for dt in days if all(x['result']=='loss' for x in byday[dt]))
A=[e for dt in days if dt in wipe for e in byday[dt]]       # 84
B=[e for dt in days if dt not in wipe for e in byday[dt]]   # 378
def med(x,f): 
    v=[f(e) for e in x if f(e) is not None]; return round(st.median(v),2), round(st.mean(v),2), len(v)
print('== 클레임 그대로 재현 (전멸일 전체 vs 그밖 전체) ==')
print('maxgain 전멸', med(A,lambda e:e['max_gain_pct']), ' 그밖', med(B,lambda e:e['max_gain_pct']))
print('3%미만비율 전멸', round(100*sum(1 for e in A if e['max_gain_pct']<3)/len(A),1), ' 그밖', round(100*sum(1 for e in B if e['max_gain_pct']<3)/len(B),1))
print('3일이내 전멸', round(100*sum(1 for e in A if e['days_held']<=3)/len(A),1), ' 그밖', round(100*sum(1 for e in B if e['days_held']<=3)/len(B),1))
print('B 구성: win',sum(1 for e in B if e['result']=='win'),'loss',sum(1 for e in B if e['result']=='loss'))
print()
print('== 순환성 제거: 패배 거래끼리만 비교 ==')
Bl=[e for e in B if e['result']=='loss']
print('n', len(A), len(Bl))
print('maxgain 전멸일-패배', med(A,lambda e:e['max_gain_pct']), ' 그밖-패배', med(Bl,lambda e:e['max_gain_pct']))
print('3%미만 전멸일-패배', round(100*sum(1 for e in A if e['max_gain_pct']<3)/len(A),1), ' 그밖-패배', round(100*sum(1 for e in Bl if e['max_gain_pct']<3)/len(Bl),1))
print('3일이내 전멸일-패배', round(100*sum(1 for e in A if e['days_held']<=3)/len(A),1), ' 그밖-패배', round(100*sum(1 for e in Bl if e['days_held']<=3)/len(Bl),1))
print('maxdd 전멸', med(A,lambda e:e['max_dd_pct']), ' 그밖-패배', med(Bl,lambda e:e['max_dd_pct']))
# Mann-Whitney U approx
def mw(a,b):
    import math
    xs=sorted([(v,0) for v in a]+[(v,1) for v in b])
    # ranks with ties
    ranks={}; i=0; R0=0
    arr=[v for v,_ in xs]
    r=[0]*len(xs); i=0
    while i<len(arr):
        j=i
        while j+1<len(arr) and arr[j+1]==arr[i]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[k]=avg
        i=j+1
    R0=sum(r[k] for k in range(len(xs)) if xs[k][1]==0)
    n0,n1=len(a),len(b)
    U=R0-n0*(n0+1)/2
    mu=n0*n1/2; sd=math.sqrt(n0*n1*(n0+n1+1)/12)
    z=(U-mu)/sd
    from math import erfc,sqrt
    p=erfc(abs(z)/sqrt(2))
    return round(z,2), round(p,4)
print('MannWhitney maxgain (전멸패배 vs 그밖패배) z,p =', mw([e['max_gain_pct'] for e in A],[e['max_gain_pct'] for e in Bl]))
print('MannWhitney days_held z,p =', mw([e['days_held'] for e in A],[e['days_held'] for e in Bl]))
