import sys, os, json, bisect, time, glob
ROOT=r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT,"scripts"))
from canslim_lib.trend_template import evaluate_trend_template, WINDOW_52W
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P
from canslim_lib.power_play import evaluate_power_play
from canslim_lib.pivot_backtest import truncate_series, simulate_pivot_trade

SER=os.path.join(ROOT,".cache","ohlcv","series")
full={}
for f in glob.glob(os.path.join(SER,"*.json")):
    c=os.path.basename(f)[:-5]
    d=json.load(open(f,encoding="utf-8"))
    if d.get("closes"): full[c]=d
cal=full["005930"]["dates"]
START,END="2026-01-13","2026-08-13"
scan=[d for d in cal if START<=d<=END]
print("scan days",len(scan))

open_until={"A":{}, "E":{}}
ev={"A":[], "E":[]}
t0=time.time()
for D in scan:
    st={}
    for c,s in full.items():
        t=truncate_series(s,D)
        if len(t["closes"])>=200: st[c]=t
    own={}
    for c,t in st.items():
        n=len(t["closes"]); w=min(n-1,WINDOW_52W)
        if w<20 or len(t["closes"])<w+1: continue
        b=t["closes"][-w-1]
        if not b or b<=0: continue
        own[c]=(w,t["closes"][-1]/b-1.0)
    bw={}
    for c,(w,r) in own.items(): bw.setdefault(w,[]).append(r)
    sw={w:sorted(v) for w,v in bw.items()}
    rs={}
    for c,(w,r) in own.items():
        p=sw[w]; rs[c]=None if len(p)<100 else max(1,min(99,round(bisect.bisect_left(p,r)/len(p)*100)))
    for c,t in st.items():
        if not evaluate_trend_template(t["closes"],rs=rs.get(c),rs_min=80)["pass"]: continue
        s=full[c]
        try: di=s["dates"].index(D)
        except ValueError: continue
        ni=di+1
        if ni>=len(s["dates"]): continue
        for pname,fn in (("VCP",lambda x:evaluate_vcp(x)),("3C",lambda x:evaluate_cheat(x,CHEAT_P)),("PP",lambda x:evaluate_power_play(x))):
            try: r=fn(t)
            except Exception: continue
            if r.get("status")!="actionable" or not r.get("pivot_price"): continue
            pv=r["pivot_price"]
            hi=s["highs"][ni]
            if hi is None or hi<pv: continue
            ed=s["dates"][ni]
            for mode,cond in (("A",True),("E",bool(r.get("entry_ready")))):
                if not cond: continue
                ou=open_until[mode]
                if c in ou and ed<=ou[c]: continue
                sim=simulate_pivot_trade(s,ni,pv,target_pct=20.0,stop_pct=10.0)
                ou[c]=sim.get("resolve_date") or ed
                ev[mode].append({"c":c,"p":pname,"m":ed[:7],"res":sim["result"],"days":sim.get("days_held")})
print("elapsed %.1fs (%.2fs/day)"%(time.time()-t0,(time.time()-t0)/len(scan)))
import collections
for mode,label in (("A","status==actionable (기존 러너 방식)"),("E","entry_ready (프로덕션 매수대상)")):
    e=ev[mode]
    print("\n---",label,"---")
    print("entries", len(e), "unique codes", len(set(x["c"] for x in e)))
    print("by pattern", dict(collections.Counter(x["p"] for x in e)))
    print("by result ", dict(collections.Counter(x["res"] for x in e)))
    print("by month  ", dict(sorted(collections.Counter(x["m"] for x in e).items())))
