import json, statistics as st, collections
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
def gsim(e,target=20.0,stop=-10.0,ndays=None,trail=None):
    s=e["ser"];b=e["bi_local"];P=e["entry_price"];T=P*(1+target/100);S=P*(1+stop/100);n=len(s["closes"]);peak=None
    for i in range(b,n):
        k=i-b;hi,lo=s["highs"][i],s["lows"][i]
        ht=hi is not None and hi>=T; hs=lo is not None and lo<=S
        if ht and hs: return (k,stop)
        if ht: return (k,target)
        if hs: return (k,stop)
        if trail is not None:
            peak=hi if peak is None else max(peak,hi)
            if peak and s["closes"][i]<=peak*(1-trail/100) and k>0: return (k,(s["closes"][i]/P-1)*100)
        if ndays is not None and k>=ndays: return (k,(s["closes"][i]/P-1)*100)
    return (n-1-b,(s["closes"][-1]/P-1)*100)
def rulepol(sel):
    def f(r):
        i=r["i"];k=sel(r)
        if k is not None and k<r["days"]:
            s=E[i]["ser"];b=E[i]["bi_local"];P=E[i]["entry_price"]
            return (k,(s["closes"][b+k]/P-1)*100)
        return (r["days"],r["gain"])
    return f
def anyf(r):
    ks=[r["fires"][x] for x in RULES if r["fires"][x] is not None]; return min(ks) if ks else None
pols=[("현행 +20/-10",lambda r:(r["days"],r["gain"])),
      ("트레일 -15%",lambda r:gsim(E[r["i"]],trail=15.0)),
      ("트레일 -10%",lambda r:gsim(E[r["i"]],trail=10.0)),
      ("트레일 -8%",lambda r:gsim(E[r["i"]],trail=8.0)),
      ("익절 +15%",lambda r:gsim(E[r["i"]],target=15.0)),
      ("익절 +12%",lambda r:gsim(E[r["i"]],target=12.0)),
      ("N=10일",lambda r:gsim(E[r["i"]],ndays=10)),
      ("N=20일",lambda r:gsim(E[r["i"]],ndays=20)),
      ("규칙 heavy_vol",rulepol(lambda r:r["fires"]["heavy_volume_pullback"])),
      ("규칙 close_below_ma",rulepol(lambda r:r["fires"]["close_below_ma"])),
      ("규칙 ANY5",rulepol(anyf))]
G={n:[p(r)[1] for r in R] for n,p in pols}
mon=[r["entry_date"][:7] for r in R]
groups={"전체":lambda i:True,
        "2026-04 제외":lambda i:mon[i]!="2026-04",
        "상승월(EV>0인 달)":lambda i:mon[i] in {"2025-11","2025-12","2026-01","2026-04","2026-06"},
        "하락월(EV<0인 달)":lambda i:mon[i] in {"2026-02","2026-03","2026-05","2026-07","2026-08"}}
print(f"{'정책':<20}"+"".join(f"{k:>16}" for k in groups))
for n,_ in pols:
    row=f"{n:<20}"
    for k,f in groups.items():
        v=[G[n][i] for i in range(len(R)) if f(i)]
        row+=f"{st.mean(v):>+16.3f}"
    print(row)
print()
for k,f in groups.items():
    v=[i for i in range(len(R)) if f(i)]
    best=max(G,key=lambda n:st.mean([G[n][i] for i in v]))
    print(f"  {k}: n={len(v)} 최고정책 = {best} ({st.mean([G[best][i] for i in v]):+.3f})")
