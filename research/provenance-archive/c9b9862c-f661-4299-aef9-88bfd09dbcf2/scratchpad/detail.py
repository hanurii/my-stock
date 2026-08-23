import json, statistics as st
from collections import Counter
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows = json.load(open(SP+r'\myTrades.json', encoding='utf-8'))

print("--- big losses (net<=-8) ---")
for r in sorted([x for x in rows if x['net']<=-8], key=lambda x:x['net']):
    print(f"  {r['open_date']} {r['name']:12s} sp={r['sp']:5.1f} ss={r['ss']:5.1f} net={r['net']:+7.2f} hold={r['hold']} tight={r['tight_prev']}")
print("  median sp of big losses:", st.median([x['sp'] for x in rows if x['net']<=-8]))
print("--- big wins (net>=8) ---")
for r in sorted([x for x in rows if x['net']>=8], key=lambda x:-x['net']):
    print(f"  {r['open_date']} {r['name']:12s} sp={r['sp']:5.1f} ss={r['ss']:5.1f} net={r['net']:+7.2f} hold={r['hold']} tight={r['tight_prev']}")
print("  median sp of big wins:", st.median([x['sp'] for x in rows if x['net']>=8]))

print("--- sp == 0 ---")
z=[r for r in rows if r['sp']==0]
for r in z: print(f"  {r['open_date']} {r['name']:12s} net={r['net']:+7.2f} {r['outcome']} tight={r['tight_prev']}")
print(f"  n={len(z)} win={sum(1 for r in z if r['outcome']=='win')} mean={st.mean([r['net'] for r in z]):+.2f}")
nz=[r for r in rows if r['sp']>0]
print(f"  sp>0 n={len(nz)} win={sum(1 for r in nz if r['outcome']=='win')/len(nz)*100:.0f}% mean={st.mean([r['net'] for r in nz]):+.2f}")

print("--- repeats ---")
c=Counter(r['name'] for r in rows)
for nm,k in c.most_common():
    if k>1:
        print(' ', nm, [(r['open_date'], r['sp'], r['net']) for r in sorted(rows,key=lambda x:x['open_date']) if r['name']==nm])

print("--- distribution / tightest ---")
print(' bins:', Counter('0-20' if r['sp']<20 else '20-50' if r['sp']<50 else '50-100' for r in rows))
print(' sp==0:', sum(1 for r in rows if r['sp']==0), ' sp<5:', sum(1 for r in rows if r['sp']<5))
print(' tightest:', Counter(r['tight_prev'] for r in rows).most_common())

print("--- stop-loss dominance ---")
L=[r for r in rows if r['outcome']!='win']
print(' loss n=',len(L),' net<=-4.5:',sum(1 for r in L if r['net']<=-4.5),' -6.5<=net<=-4.5:',sum(1 for r in L if -6.5<=r['net']<=-4.5))
print(' loss hold dist:', Counter(r['hold'] for r in L).most_common())
print(' median net all:', st.median([r['net'] for r in rows]), ' mean:', round(st.mean([r['net'] for r in rows]),2))

print("--- per-condition AUC ---")
import math
def mw(a,b):
    n1,n2=len(a),len(b); allv=sorted(a+b); ranks={}; i=0; tc=0.0
    while i<len(allv):
        j=i
        while j+1<len(allv) and allv[j+1]==allv[i]: j+=1
        r=(i+1+j+1)/2.0
        for k in range(i,j+1): ranks.setdefault(allv[k],r)
        t=j-i+1; tc+=t**3-t; i=j+1
    R1=sum(ranks[x] for x in a); U1=R1-n1*(n1+1)/2; auc=U1/(n1*n2)
    mu=n1*n2/2; N=n1+n2
    sd=math.sqrt(n1*n2/12*((N+1)-tc/(N*(N-1))))
    z=(U1-mu-(0.5 if U1>mu else -0.5))/sd if sd>0 else 0.0
    p=2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2))))
    return auc,p
for k in '12345678':
    W=[r['per_prev'][k]['pct'] for r in rows if r['outcome']=='win']
    L2=[r['per_prev'][k]['pct'] for r in rows if r['outcome']!='win']
    a,p=mw(W,L2)
    print(f"  cond{k}: win med {st.median(W):5.1f} vs loss med {st.median(L2):5.1f}  AUC={a:.3f} p={p:.3f}")
# raw cond7 margin (distance from 52w high)
W=[r['per_prev']['7']['margin']-25 for r in rows if r['outcome']=='win']
L2=[r['per_prev']['7']['margin']-25 for r in rows if r['outcome']!='win']
print('  cond7 raw %from52wHigh: win med', round(st.median(W),1), 'loss med', round(st.median(L2),1))
