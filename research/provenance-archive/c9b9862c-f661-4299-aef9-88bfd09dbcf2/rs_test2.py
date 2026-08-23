# -*- coding: utf-8 -*-
import json, random, math
from collections import defaultdict, Counter
random.seed(20260822)
P = r"C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win","loss")]
by_date = defaultdict(list)
for e in ev: by_date[e["entry_date"]].append(e)
days = {k:v for k,v in by_date.items() if len(v)>=3}
n_days = len(days)
def win(e): return 1.0 if e["result"]=="win" else 0.0
def bucket(rs):
    return "95+" if rs>=95 else "90-94" if rs>=90 else "85-89" if rs>=85 else "80-84" if rs>=80 else "<80"

# whole-pool bucket
raw2 = defaultdict(lambda:[0,0])
for e in ev:
    b=bucket(e["rs"]); raw2[b][0]+=win(e); raw2[b][1]+=1
print("(whole pool, NOT same-day - calendar illusion prone)")
for b in ["<80","80-84","85-89","90-94","95+"]:
    if raw2[b][1]: print("  %-6s n=%3d WR=%.1f%%"%(b,raw2[b][1],raw2[b][0]/raw2[b][1]*100))

# bucket day-demeaned permutation p-value (shuffle results within each day)
dem_obs = defaultdict(list)
for dt,c in days.items():
    base = sum(win(x) for x in c)/len(c)
    for x in c: dem_obs[bucket(x["rs"])].append(win(x)-base)
obs = {b: sum(v)/len(v) for b,v in dem_obs.items()}
B=2000
cnt = {b:0 for b in obs}
for _ in range(B):
    acc = defaultdict(list)
    for dt,c in days.items():
        res = [win(x) for x in c]; random.shuffle(res)
        base = sum(res)/len(res)
        for x,r in zip(c,res): acc[bucket(x["rs"])].append(r-base)
    for b in obs:
        m = sum(acc[b])/len(acc[b])
        if abs(m) >= abs(obs[b])-1e-12: cnt[b]+=1
print("\nbucket permutation test (shuffle outcomes within each day, 2000x):")
for b in ["80-84","85-89","90-94","95+"]:
    if b in obs:
        print("  %-6s vs_dayavg %+.1fpp  two-sided p=%.4f"%(b,obs[b]*100,(cnt[b]+1)/(B+1)))

# tie robustness: best-case / worst-case deterministic tie-break for TOP2
def topk_det(c,k,rev,best):
    s = sorted(c, key=lambda x:(x["rs"] if rev else -x["rs"], (win(x) if best else -win(x))), reverse=True)
    return s[:k]
for best in (True,False):
    wr = sum(sum(win(x) for x in topk_det(c,2,True,best))/2 for c in days.values())/n_days
    print("TOP2 RS, %s-case tie-break: %.4f"%("best" if best else "worst", wr))
for best in (True,False):
    wr = sum(sum(win(x) for x in topk_det(c,2,False,best))/2 for c in days.values())/n_days
    print("BOT2 RS, %s-case tie-break: %.4f"%("best" if best else "worst", wr))

# top1 sanity + mean gain_at_resolve comparison
def exp_topk(c,key,k,rev):
    vals=sorted({key(x) for x in c},reverse=rev); taken=0; e=0.0
    for v in vals:
        g=[x for x in c if key(x)==v]; room=k-taken
        if room<=0: break
        if len(g)<=room: e+=sum(win(x) for x in g); taken+=len(g)
        else: e+=room*(sum(win(x) for x in g)/len(g)); taken=k
    return e
t1=sum(exp_topk(c,lambda x:x["rs"],1,True) for c in days.values())/n_days
b1=sum(exp_topk(c,lambda x:x["rs"],1,False) for c in days.values())/n_days
base=sum(sum(win(x) for x in c)/len(c) for c in days.values())/n_days
print("\nTOP1 %.4f  RANDOM1 %.4f  BOT1 %.4f"%(t1,base,b1))

# mean realized gain per pick (day-equal)
def exp_topk_val(c,k,rev,field):
    vals=sorted({x["rs"] for x in c},reverse=rev); taken=0; e=0.0
    for v in vals:
        g=[x for x in c if x["rs"]==v]; room=k-taken
        if room<=0: break
        if len(g)<=room: e+=sum(x[field] for x in g); taken+=len(g)
        else: e+=room*(sum(x[field] for x in g)/len(g)); taken=k
    return e
for f in ("gain_at_resolve_pct","max_gain_pct"):
    t=sum(exp_topk_val(c,2,True,f) for c in days.values())/(2*n_days)
    r=sum(sum(x[f] for x in c)/len(c) for c in days.values())/n_days
    b=sum(exp_topk_val(c,2,False,f) for c in days.values())/(2*n_days)
    print("%-20s TOP2 %+.2f%%  RANDOM %+.2f%%  BOT2 %+.2f%%"%(f,t,r,b))
