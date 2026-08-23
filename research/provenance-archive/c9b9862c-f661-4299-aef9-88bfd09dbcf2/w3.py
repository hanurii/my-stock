import json, statistics as st, math
from collections import defaultdict, Counter
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
wipe=set(dt for dt in days if all(x['result']=='loss' for x in byday[dt]))
A=[e for dt in days if dt in wipe for e in byday[dt]]
B=[e for dt in days if dt not in wipe for e in byday[dt]]
def mw(a,b):
    xs=sorted([(v,0) for v in a]+[(v,1) for v in b]); arr=[v for v,_ in xs]
    r=[0]*len(xs); i=0
    while i<len(arr):
        j=i
        while j+1<len(arr) and arr[j+1]==arr[i]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[k]=avg
        i=j+1
    R0=sum(r[k] for k in range(len(xs)) if xs[k][1]==0)
    n0,n1=len(a),len(b); U=R0-n0*(n0+1)/2
    mu=n0*n1/2; sd=math.sqrt(n0*n1*(n0+n1+1)/12); z=(U-mu)/sd
    return round(z,2), round(math.erfc(abs(z)/math.sqrt(2)),4)
print('== 종목 특성 (전멸일 84 vs 그밖 378) ==')
for f in ['rs','atr_pct','turnover_eok','gap_up_pct','entry_price']:
    a=[e[f] for e in A]; b=[e[f] for e in B]
    print(f'{f:14s} 중앙 {st.median(a):8.2f} vs {st.median(b):8.2f}  평균 {st.mean(a):8.2f} vs {st.mean(b):8.2f}  MW z,p={mw(a,b)}')
ca=Counter(e['pattern'] for e in A); cb=Counter(e['pattern'] for e in B)
print('패턴 전멸', {k:round(100*v/len(A),1) for k,v in ca.items()}, ' 그밖', {k:round(100*v/len(B),1) for k,v in cb.items()})
# 일 단위(하루 평균)로 접어서도 확인 — 종목 반복/하루 다건 중복 제거
print()
print('== 하루 단위(일 평균)로 접어서 ==')
for f in ['rs','atr_pct','turnover_eok']:
    a=[st.median([e[f] for e in byday[dt]]) for dt in days if dt in wipe]
    b=[st.median([e[f] for e in byday[dt]]) for dt in days if dt not in wipe]
    print(f'{f:14s} 전멸일 {len(a)}일 중앙 {st.median(a):8.2f} vs 그밖 {len(b)}일 {st.median(b):8.2f}  MW z,p={mw(a,b)}')
