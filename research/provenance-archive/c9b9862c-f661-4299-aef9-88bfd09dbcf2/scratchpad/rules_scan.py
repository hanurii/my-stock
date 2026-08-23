import json, sys
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN/"scripts"))
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib import sell_rules as SR

E=json.load(open("evfull.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]

def base_resolve(e):
    s=e["ser"]; b=e["bi_local"]; P=e["entry_price"]
    T=P*1.20; S=P*0.90
    n=len(s["closes"])
    for i in range(b,n):
        hi,lo=s["highs"][i],s["lows"][i]
        ht=hi is not None and hi>=T; hs=lo is not None and lo<=S
        k=i-b
        if k==0:
            if ht and hs: return ("ambiguous",0,-10.0)
            if ht: return ("win",0,20.0)
            if hs: return ("ambiguous",0,-10.0)
            continue
        if ht and hs: return ("ambiguous",k,-10.0)
        if ht: return ("win",k,20.0)
        if hs: return ("loss",k,-10.0)
    return ("unresolved",n-1-b,(s["closes"][-1]/P-1)*100)

out=[]
for idx,e in enumerate(E):
    s=e["ser"]; b=e["bi_local"]
    r,dh,g = base_resolve(e)
    n=len(s["closes"])
    fires={rid:None for rid in RULES}
    watch={rid:None for rid in RULES}
    daily=[]
    for k in range(1, dh+1):
        t = truncate_series(s, s["dates"][b+k])
        st = {}
        st["heavy_volume_pullback"]=SR.rule_heavy_volume_pullback(t,b)["status"]
        st["consecutive_lower_lows"]=SR.rule_consecutive_lower_lows(t,b)["status"]
        st["close_below_ma"]=SR.rule_close_below_ma(t,b)["status"]
        st["weak_days_dominant"]=SR.rule_weak_days_dominant(t,b)["status"]
        st["breakout_failure"]=SR.rule_breakout_failure(t,b,e["pivot"],breakout_confirmed=True,start=b)["status"]
        for rid in RULES:
            if fires[rid] is None and st[rid]=="violation": fires[rid]=k
            if watch[rid] is None and st[rid] in ("violation","watch"): watch[rid]=k
        daily.append({"k":k,**{rid:st[rid][0] for rid in st}})
    out.append({"i":idx,"code":e["code"],"entry_date":e["entry_date"],"result":r,"days":dh,"gain":g,
                "fires":fires,"watch":watch,"daily":daily})
    if idx%100==0: print(idx,flush=True)
json.dump(out,open("rulescan.json","w",encoding="utf-8"),ensure_ascii=False)
print("done")
