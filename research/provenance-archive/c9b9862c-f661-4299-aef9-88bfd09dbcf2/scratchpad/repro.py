import json, statistics as st
P=json.load(open("paths.json",encoding="utf-8"))
def base(e, target=20.0, stop=-10.0, opt=False):
    p=e["path"]; E=e["entry_price"]
    T=E*(1+target/100); S=E*(1+stop/100)
    for i in range(len(p["closes"])):
        hi,lo=p["highs"][i],p["lows"][i]
        ht = hi is not None and hi>=T
        hs = lo is not None and lo<=S
        if i==0:
            if ht and hs: return ("ambiguous", i, target if opt else stop)
            if ht: return ("win", i, target)
            if hs: return ("ambiguous", i, target if opt else stop)  # stop_on_breakout_day
            continue
        if ht and hs: return ("ambiguous", i, target if opt else stop)
        if ht: return ("win", i, (p["highs"][i]/E-1)*100 if False else target)
        if hs: return ("loss", i, stop)
    return ("unresolved", len(p["closes"])-1, (p["closes"][-1]/E-1)*100)
mism=0
res=[]
for e in P:
    r,d,g = base(e)
    res.append((r,d,g))
    if r!=e["result"] or d!=e["days_held"]: mism+=1
print("mismatch",mism,"of",len(P))
import collections
print(collections.Counter(r for r,_,_ in res))
g=[x[2] for x in res]
print("nominal EV",round(st.mean(g),4),"sum",round(sum(g),1),"days",sum(x[1] for x in res),
      "per-day",round(sum(g)/sum(x[1] for x in res),4))
# actual realized close-based
def realized(e):
    p=e["path"]; E=e["entry_price"]
    r,d,gnom = base(e)
    return (p["closes"][d]/E-1)*100
ra=[realized(e) for e in P]
print("realized-close EV",round(st.mean(ra),4),"sum",round(sum(ra),1))
