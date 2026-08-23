import json, random, math
from collections import defaultdict
random.seed(7)
P = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
ev = [e for e in json.load(open(P, encoding="utf-8"))["events"] if e["result"] in ("win","loss")]
W = lambda e: 1.0 if e["result"]=="win" else 0.0
by = defaultdict(list)
for e in ev: by[e["entry_date"]].append(e)
days = {k:v for k,v in by.items() if len(v)>=3}

# 0) how much of the pooled quartile split is pure tie-ordering artifact?
s = sorted(ev, key=lambda e: e["gap_up_pct"]); q=len(s)//4
for i in range(4):
    ch = s[i*q:(i+1)*q]
    print("pooled Q%d: winrate %.3f  gap range %.2f~%.2f  (all-zero-gap: %s)"
          % (i+1, sum(map(W,ch))/len(ch), ch[0]["gap_up_pct"], ch[-1]["gap_up_pct"],
             all(c["gap_up_pct"]==0 for c in ch)))

# 1) zero-gap vs positive-gap, PAIRED within day
print("\n--- within-day: gap==0 vs gap>0 (days containing both) ---")
zn=zw=pn=pw=0; pos_d=neg_d=tie_d=0; nd=0
for dt,items in days.items():
    z=[e for e in items if e["gap_up_pct"]==0]; p=[e for e in items if e["gap_up_pct"]>0]
    if not z or not p: continue
    nd+=1
    zw+=sum(map(W,z)); zn+=len(z); pw+=sum(map(W,p)); pn+=len(p)
    dz=sum(map(W,z))/len(z)-sum(map(W,p))/len(p)
    if dz>1e-9: pos_d+=1
    elif dz<-1e-9: neg_d+=1
    else: tie_d+=1
print("days=%d  gap==0: %d trades %.4f | gap>0: %d trades %.4f  diff=%+.4f"
      %(nd,zn,zw/zn,pn,pw/pn,zw/zn-pw/pn))
n=pos_d+neg_d; k=min(pos_d,neg_d)
p2 = min(1.0, 2*sum(math.comb(n,i) for i in range(k+1))/2**n) if n else 1.0
print("sign test by day: zero-better %d, pos-better %d, tie %d -> p=%.4f"%(pos_d,neg_d,tie_d,p2))

# 2) big gap (>=2%) vs rest, within day
print("\n--- within-day: gap>=2%% vs rest (days containing both) ---")
for TH in (1.0,2.0,3.0):
    an=aw=bn=bw=0; nd2=0
    for dt,items in days.items():
        a=[e for e in items if e["gap_up_pct"]>=TH]; b=[e for e in items if e["gap_up_pct"]<TH]
        if not a or not b: continue
        nd2+=1; aw+=sum(map(W,a)); an+=len(a); bw+=sum(map(W,b)); bn+=len(b)
    if an: print("  TH=%.0f%%: days=%d  big-gap %d trades %.4f | rest %d trades %.4f"
                 %(TH,nd2,an,aw/an,bn,bw/bn))

# 3) restrict top2 test to days where the rule is DETERMINATE (2 strictly smallest exist)
print("\n--- top2 test on determinate days only ---")
det=[]
for dt,items in days.items():
    v=sorted(e["gap_up_pct"] for e in items)
    if v[1]<v[2]: det.append((dt,items))
print("determinate days:",len(det))
if det:
    tw=rw=bw2=0.0; pos=neg=tie=0
    for dt,items in det:
        s2=sorted(items,key=lambda e:e["gap_up_pct"])
        t=(W(s2[0])+W(s2[1]))/2; base=sum(map(W,items))/len(items)
        vv=sorted(e["gap_up_pct"] for e in items)
        s3=sorted(items,key=lambda e:-e["gap_up_pct"]); b=(W(s3[0])+W(s3[1]))/2
        tw+=t; rw+=base; bw2+=b
        if t>base+1e-9: pos+=1
        elif t<base-1e-9: neg+=1
        else: tie+=1
    N=len(det)
    print("  TOP2=%.4f RANDOM=%.4f BOT2=%.4f (trades=%d)"%(tw/N,rw/N,bw2/N,2*N))
    n=pos+neg; k=min(pos,neg)
    pp = min(1.0,2*sum(math.comb(n,i) for i in range(k+1))/2**n) if n else 1.0
    print("  sign: better %d worse %d tie %d -> p=%.4f"%(pos,neg,tie,pp))
    B=2000; sims=[]
    for _ in range(B):
        s4=0.0
        for dt,items in det:
            a,b3=random.sample(items,2); s4+=(W(a)+W(b3))/2
        sims.append(s4/N)
    sims.sort(); obs=tw/N
    ge=sum(1 for x in sims if x>=obs-1e-12); le=sum(1 for x in sims if x<=obs+1e-12)
    print("  bootstrap two-sided p=%.4f (random mean %.4f)"%(min(1.0,2*min(ge,le)/B), sum(sims)/B))
