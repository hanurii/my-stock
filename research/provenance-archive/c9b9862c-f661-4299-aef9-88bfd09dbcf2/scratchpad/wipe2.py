import json, collections, random
from math import comb
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
def mk(mode):
    out=[]
    for x in ev:
        r=x["result"]
        if mode=="resolved" and r not in ("win","loss"): continue
        out.append(dict(code=x["code"],day=x["entry_date"],scan=x["scan_date"],
            win=1 if r=="win" else 0,to=x["turnover_eok"],ret=x.get("gain_at_resolve_pct"),rs=x["rs"]))
    return out
def rand_wipe(n,w,K):
    k=min(K,n)
    if w==0: return 1.0
    if n-w<k: return 0.0
    return comb(n-w,k)/comb(n,k)
def rule_wipe(items,K,key):
    k=min(K,len(items)); s=sorted(items,key=key,reverse=True); v=[key(x) for x in s]
    if k<len(s) and v[k-1]==v[k]:
        tot=0
        for _ in range(400):
            sh=items[:]; random.shuffle(sh); sh.sort(key=key,reverse=True)
            tot+=0 if any(x["win"] for x in sh[:k]) else 1
        return tot/400
    return 0.0 if any(x["win"] for x in s[:k]) else 1.0
random.seed(11)
for mode in ("all","resolved"):
    P=mk(mode); byday=collections.defaultdict(list)
    for x in P: byday[x["day"]].append(x)
    days=sorted(byday)
    print("=== pool=%s  days=%d ==="%(mode,len(days)))
    for K in (1,3,6):
        r=[];t=[]
        for dy in days:
            it=byday[dy];n=len(it);w=sum(x["win"] for x in it)
            r.append(rand_wipe(n,w,K)); t.append(rule_wipe(it,K,lambda x:x["to"]))
        print(" K=%d random %.1f  turnover %.1f  diff %.1f"%(K,100*sum(r)/len(r),100*sum(t)/len(t),100*(sum(t)-sum(r))/len(r)))
    # regime split (entry-date regime and scan-date regime)
    for lab,keyf in (("entry-day",lambda it:upmap.get(it[0]["day"])),("scan-day(no lookahead)",lambda it:upmap.get(it[0]["scan"]))):
        up=[dy for dy in days if keyf(byday[dy]) is True]
        dn=[dy for dy in days if keyf(byday[dy]) is False]
        na=[dy for dy in days if keyf(byday[dy]) is None]
        print("  regime[%s] up=%d down=%d missing=%d"%(lab,len(up),len(dn),len(na)))
        for K in (1,3,6):
            a=[rand_wipe(len(byday[x]),sum(y['win'] for y in byday[x]),K) for x in up]
            b=[rand_wipe(len(byday[x]),sum(y['win'] for y in byday[x]),K) for x in dn]
            ta=[rule_wipe(byday[x],K,lambda z:z["to"]) for x in up]
            tb=[rule_wipe(byday[x],K,lambda z:z["to"]) for x in dn]
            print("   K=%d rand up %.1f vs dn %.1f (gap %.1f) | turnover up %.1f vs dn %.1f"%(
                K,100*sum(a)/len(a),100*sum(b)/len(b),100*(sum(b)/len(b)-sum(a)/len(a)),100*sum(ta)/len(ta),100*sum(tb)/len(tb)))
    print()
