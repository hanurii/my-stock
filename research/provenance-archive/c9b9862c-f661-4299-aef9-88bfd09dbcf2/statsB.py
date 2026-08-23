# -*- coding: utf-8 -*-
import json,os,statistics as st
from collections import Counter
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows=json.load(open(os.path.join(SP,'tradesB.json'),encoding='utf-8'))
print('n=',len(rows))
print('allpass_prev:',Counter(r['allpass_prev'] for r in rows))
print('allpass_same:',Counter(r['allpass_same'] for r in rows))
print()
def q(v):
    v=sorted(v)
    n=len(v)
    def pct(p):
        if n==1: return v[0]
        i=p*(n-1); lo=int(i); hi=min(lo+1,n-1); f=i-lo
        return v[lo]*(1-f)+v[hi]*f
    return pct(0.25),pct(0.5),pct(0.75)
for key in ('score_prev','score_same'):
    W=[r[key] for r in rows if r['outcome']=='win']
    L=[r[key] for r in rows if r['outcome']=='loss']
    print(f'--- {key} ---')
    for lab,v in (('win',W),('loss',L)):
        a,b,c=q(v)
        print(f'  {lab} n={len(v)} mean={st.mean(v):.1f} Q1={a:.1f} med={b:.1f} Q3={c:.1f} min={min(v):.1f} max={max(v):.1f}')
    # Mann-Whitney U with normal approx + ties
    def mw(x,y):
        allv=[(v,0) for v in x]+[(v,1) for v in y]
        allv.sort(key=lambda t:t[0])
        ranks={}
        i=0; rk=[0]*len(allv)
        while i<len(allv):
            j=i
            while j+1<len(allv) and allv[j+1][0]==allv[i][0]: j+=1
            avg=(i+j)/2+1
            for k in range(i,j+1): rk[k]=avg
            i=j+1
        R1=sum(rk[k] for k in range(len(allv)) if allv[k][1]==0)
        n1,n2=len(x),len(y)
        U1=R1-n1*(n1+1)/2
        U2=n1*n2-U1
        U=min(U1,U2)
        mu=n1*n2/2
        # tie correction
        cnt=Counter(v for v,_ in allv)
        N=n1+n2
        tie=sum(t**3-t for t in cnt.values())
        sd=( n1*n2/12*((N+1)-tie/(N*(N-1))) )**0.5
        import math
        z=(U-mu+0.5)/sd if sd>0 else 0
        p=math.erfc(abs(z)/math.sqrt(2))
        return U1,U2,z,p, U1/(n1*n2)
    U1,U2,z,p,auc=mw(W,L)
    print(f'  Mann-Whitney: U(win)={U1:.0f} z={z:.2f} p={p:.3f}  AUC(win>loss)={auc:.3f}')
    print()
