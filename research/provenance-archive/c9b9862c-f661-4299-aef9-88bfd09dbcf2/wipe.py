import json, collections, math, random
from math import comb

BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]
reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))
rs=reg["series"] if isinstance(reg,dict) else reg
print("regime keys",list(reg.keys())[:10] if isinstance(reg,dict) else "list")
print("regime sample",rs[0], rs[-1], len(rs))
upmap={r["date"]:bool(r["up"]) for r in rs}

def pool(mode):
    """mode 'resolved': only win/loss. 'all': all events, non-win=fail"""
    out=[]
    for x in ev:
        r=x["result"]
        if mode=="resolved" and r not in ("win","loss"): continue
        out.append(dict(code=x["code"],day=x["entry_date"],scan=x["scan_date"],
                        win=1 if r=="win" else 0, to=x["turnover_eok"],
                        ret=x.get("gain_at_resolve_pct"), rs=x["rs"], name=x["name"]))
    return out

for mode in ("resolved","all"):
    P=pool(mode)
    byday=collections.defaultdict(list)
    for x in P: byday[x["day"]].append(x)
    print(mode,"events",len(P),"days",len(byday),"winrate",round(100*sum(x['win'] for x in P)/len(P),1))

P=pool("resolved")
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=sorted(byday)

def rand_wipe(n,w,K):
    k=min(K,n)
    if w==0: return 1.0
    if n-w < k: return 0.0
    return comb(n-w,k)/comb(n,k)

def rule_wipe(items,K,key,rev=True):
    k=min(K,len(items))
    s=sorted(items,key=lambda x:(key(x),), reverse=rev)
    # tie-aware: average over random tie breaks by simulation if ties at boundary
    vals=[key(x) for x in s]
    if k<len(s) and vals[k-1]==vals[k]:
        tot=0
        for _ in range(400):
            sh=items[:]; random.shuffle(sh)
            sh.sort(key=key,reverse=rev)
            tot+= 0 if any(x["win"] for x in sh[:k]) else 1
        return tot/400
    return 0.0 if any(x["win"] for x in s[:k]) else 1.0

random.seed(7)
print()
print("=== wipeout rate, all 146 days (each day equal weight) ===")
print("K  random  turnover-desc  turnover-asc  RS-desc  n_days")
for K in (1,2,3,4,5,6,8):
    r=[];t=[];ta=[];rr=[]
    for day in days:
        it=byday[day]; n=len(it); w=sum(x["win"] for x in it)
        r.append(rand_wipe(n,w,K))
        t.append(rule_wipe(it,K,lambda x:x["to"]))
        ta.append(rule_wipe(it,K,lambda x:-x["to"]))
        rr.append(rule_wipe(it,K,lambda x:x["rs"]))
    f=lambda a:round(100*sum(a)/len(a),1)
    print(K,f(r),f(t),f(ta),f(rr),len(days))

print()
print("=== wipeout rate, ONLY days where the slot cap binds (n > K) ===")
print("K  n_days  events  random  turnover-desc  diff(pp)")
for K in (1,2,3,4,5,6):
    sel=[day for day in days if len(byday[day])>K]
    r=[];t=[]
    for day in sel:
        it=byday[day]; n=len(it); w=sum(x["win"] for x in it)
        r.append(rand_wipe(n,w,K)); t.append(rule_wipe(it,K,lambda x:x["to"]))
    f=lambda a:100*sum(a)/len(a)
    print(K,len(sel),sum(len(byday[x]) for x in sel),round(f(r),1),round(f(t),1),round(f(t)-f(r),1))
