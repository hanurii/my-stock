# -*- coding: utf-8 -*-
import json, random, collections, math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
random.seed(7)
D=json.load(open('public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[e for e in D['events'] if e['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for e in ev: byday[e['entry_date']].append(e)
days=[v for v in byday.values() if len(v)>=3]
def w(e): return 1 if e['result']=='win' else 0
def exp_pick2(g):
    return 2.0*sum(w(e) for e in g)/len(g)
def exp_prefer(pats, wins, P, prefer=True):
    A=[wins[i] for i in range(len(pats)) if (pats[i]==P)==prefer]
    B=[wins[i] for i in range(len(pats)) if (pats[i]==P)!=prefer]
    if len(A)>=2: return 2.0*sum(A)/len(A)
    if len(A)==1: return A[0]+sum(B)/len(B)
    return 2.0*sum(B)/len(B)

R=2000
print("within-day label permutation (shuffle pattern labels inside each day, 2000x)")
for P in ('VCP','3C','PP'):
    dl=[v for v in days if any(e['pattern']==P for e in v) and any(e['pattern']!=P for e in v)]
    pats=[[e['pattern'] for e in v] for v in dl]; wins=[[w(e) for e in v] for v in dl]
    obs_top=sum(exp_prefer(pats[i],wins[i],P,True) for i in range(len(dl)))
    obs_bot=sum(exp_prefer(pats[i],wins[i],P,False) for i in range(len(dl)))
    obs_d=obs_top-obs_bot
    ge=0; geT=0
    for _ in range(R):
        s=0.0; t=0.0
        for i in range(len(dl)):
            pp=pats[i][:]; random.shuffle(pp)
            a=exp_prefer(pp,wins[i],P,True); b=exp_prefer(pp,wins[i],P,False)
            t+=a; s+=a-b
        if s>=obs_d-1e-9: ge+=1
        if t>=obs_top-1e-9: geT+=1
    picks=2*len(dl)
    print("  %-4s days=%d picks=%d  top2=%.1f%% bot2=%.1f%%  spread=%+.2f wins  perm p(spread)=%.4f  perm p(top2)=%.4f"
          %(P,len(dl),picks,100*obs_top/picks,100*obs_bot/picks,obs_d,(ge+1)/(R+1),(geT+1)/(R+1)))

# cluster bootstrap (resample days) on day-level mean diff
print("\ncluster bootstrap over days (2000x), day-level winrate diff P vs non-P:")
for P in ('VCP','3C','PP'):
    ds=[]
    for v in days:
        A=[w(e) for e in v if e['pattern']==P]; B=[w(e) for e in v if e['pattern']!=P]
        if A and B: ds.append(sum(A)/len(A)-sum(B)/len(B))
    m=sum(ds)/len(ds); bs=[]
    for _ in range(R):
        s=[random.choice(ds) for _ in ds]; bs.append(sum(s)/len(s))
    bs.sort(); lo=bs[int(.025*R)]; hi=bs[int(.975*R)]
    p2=2*min(sum(1 for x in bs if x<=0),sum(1 for x in bs if x>=0))/R
    print("  %-4s days=%d mean=%+.1f%%p  95%%CI [%+.1f, %+.1f]%%p  boot p=%.3f"%(P,len(ds),100*m,100*lo,100*hi,min(1.0,p2)))
