import json, statistics as st, collections, random
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
def gsim(e,target=20.0,stop=-10.0,ndays=None,trail=None,realfill=False):
    s=e["ser"];b=e["bi_local"];P=e["entry_price"];T=P*(1+target/100);S=P*(1+stop/100)
    n=len(s["closes"]);peak=None
    for i in range(b,n):
        k=i-b;hi,lo,op=s["highs"][i],s["lows"][i],s["opens"][i]
        ht=hi is not None and hi>=T; hs=lo is not None and lo<=S
        if hs:
            fill=S
            if realfill and op is not None and op<S: fill=op
            return (k,(fill/P-1)*100)
        if ht: return (k,target)
        if trail is not None:
            peak=hi if peak is None else max(peak,hi)
            if peak and s["closes"][i]<=peak*(1-trail/100) and k>0: return (k,(s["closes"][i]/P-1)*100)
        if ndays is not None and k>=ndays: return (k,(s["closes"][i]/P-1)*100)
    return (n-1-b,(s["closes"][-1]/P-1)*100)
def rulepol(sel,rf=False):
    def f(r):
        i=r["i"];k=sel(r); bd,bg=gsim(E[i],realfill=rf)
        if k is not None and k<bd:
            s=E[i]["ser"];b=E[i]["bi_local"];P=E[i]["entry_price"]
            return (k,(s["closes"][b+k]/P-1)*100)
        return (bd,bg)
    return f
def anyf(r):
    ks=[r["fires"][x] for x in RULES if r["fires"][x] is not None]; return min(ks) if ks else None
POL={}
POL["현행 +20/-10"]=lambda r:gsim(E[r["i"]])
for X in (5,7,8,10,12,15,18): POL[f"익절+{X}%"]=lambda r,X=X:gsim(E[r["i"]],target=float(X))
for N in (3,5,7,10,15,20,25,30,40): POL[f"{N}일청산"]=lambda r,N=N:gsim(E[r["i"]],ndays=N)
for X in (8,10,12,15):
    for N in (5,10,20): POL[f"+{X}%&{N}일"]=lambda r,X=X,N=N:gsim(E[r["i"]],target=float(X),ndays=N)
for T in (5,8,10,12,15,18): POL[f"트레일-{T}%"]=lambda r,T=T:gsim(E[r["i"]],trail=float(T))
for rid in RULES: POL["규칙:"+rid]=rulepol(lambda r,rid=rid:r["fires"][rid])
POL["규칙:ANY5"]=rulepol(anyf)
def nth(r,n):
    ks=sorted(r["fires"][x] for x in RULES if r["fires"][x] is not None); return ks[n] if len(ks)>n else None
POL["규칙:2+"]=rulepol(lambda r:nth(r,1)); POL["규칙:3+"]=rulepol(lambda r:nth(r,2))
def firstfire(r,rid,cond):
    e=E[r["i"]];s=e["ser"];b=e["bi_local"];P=e["entry_price"]
    for row in r["daily"]:
        k=row["k"]
        if k>=r["days"]: break
        if row[rid]!="v": continue
        pnl=(s["closes"][b+k]/P-1)*100
        if (cond=="loss" and pnl<0) or (cond=="profit" and pnl>=0): return k
    return None
for cond in ("loss","profit"):
    for rid in RULES: POL[f"규칙({cond}):{rid}"]=rulepol(lambda r,rid=rid,c=cond:firstfire(r,rid,c))
    POL[f"규칙({cond}):ANY5"]=rulepol(lambda r,c=cond:min([k for k in (firstfire(r,x,c) for x in RULES) if k is not None],default=None))
G={n:[p(r)[1] for r in R] for n,p in POL.items()}
b=G["현행 +20/-10"]
rows=sorted(((n,st.mean(g),st.mean(g)-st.mean(b)) for n,g in G.items()), key=lambda x:-x[1])
print(f"훑은 정책 총 {len(POL)}개 (현행 포함). 상위 8개:")
for n,m,d in rows[:8]: print(f"   {n:<26} EV {m:+7.3f}  Δ현행 {d:+7.3f}")
print(f"   ... 최하위: {rows[-1][0]} EV {rows[-1][1]:+.3f}")
print(f"현행보다 EV 높은 정책 = {sum(1 for n,m,d in rows if d>1e-9)}개 / {len(POL)-1}개")
CUT="2026-03-25"
print()
print("상위 경쟁자의 전후반 Δ(현행 대비) 부호")
for n,m,d in rows[:4]:
    if n=="현행 +20/-10": continue
    d1=st.mean([G[n][i]-b[i] for i in range(len(R)) if R[i]["entry_date"]<CUT])
    d2=st.mean([G[n][i]-b[i] for i in range(len(R)) if R[i]["entry_date"]>=CUT])
    print(f"   {n:<26} 전반 {d1:+.3f} / 후반 {d2:+.3f}  → {'부호유지' if d1*d2>0 else '부호뒤집힘'}")
