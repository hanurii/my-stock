import json, statistics as st, collections, random
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
def gsim(e,target=20.0,stop=-10.0,ndays=None,trail=None,realfill=True):
    s=e["ser"];b=e["bi_local"];P=e["entry_price"];T=P*(1+target/100);S=P*(1+stop/100)
    n=len(s["closes"]);peak=None
    for i in range(b,n):
        k=i-b;hi,lo,op=s["highs"][i],s["lows"][i],s["opens"][i]
        ht=hi is not None and hi>=T; hs=lo is not None and lo<=S
        if hs:
            fill=S
            if realfill and op is not None and op<S: fill=op   # 갭하락 → 시가 체결
            if ht and (not realfill or (op is not None and op>=S)):
                return (k,stop)   # 같은날 양쪽: 비관적으로 손절
            return (k,(fill/P-1)*100)
        if ht: return (k,target)
        if trail is not None:
            peak=hi if peak is None else max(peak,hi)
            if peak and s["closes"][i]<=peak*(1-trail/100) and k>0: return (k,(s["closes"][i]/P-1)*100)
        if ndays is not None and k>=ndays: return (k,(s["closes"][i]/P-1)*100)
    return (n-1-b,(s["closes"][-1]/P-1)*100)
def rulepol(sel,realfill=True):
    def f(r):
        i=r["i"];k=sel(r)
        bd,bg=gsim(E[i],realfill=realfill)
        if k is not None and k<bd:
            s=E[i]["ser"];b=E[i]["bi_local"];P=E[i]["entry_price"]
            return (k,(s["closes"][b+k]/P-1)*100)
        return (bd,bg)
    return f
def anyf(r):
    ks=[r["fires"][x] for x in RULES if r["fires"][x] is not None]; return min(ks) if ks else None
for rf in (False,True):
    tag="갭 무시(현행 파일 규약)" if not rf else "갭 반영(시장가 손절 실체결)"
    pols=[("현행 +20/-10",lambda r:gsim(E[r["i"]],realfill=rf)),
          ("트레일 -15%",lambda r:gsim(E[r["i"]],trail=15.0,realfill=rf)),
          ("트레일 -10%",lambda r:gsim(E[r["i"]],trail=10.0,realfill=rf)),
          ("익절 +15%",lambda r:gsim(E[r["i"]],target=15.0,realfill=rf)),
          ("규칙 heavy_vol",rulepol(lambda r:r["fires"]["heavy_volume_pullback"],rf)),
          ("규칙 ANY5",rulepol(anyf,rf))]
    print(f"[{tag}]")
    for n,p in pols:
        g=[p(r)[1] for r in R]
        print(f"   {n:<18} EV {st.mean(g):+7.3f}  합계 {sum(g):+8.1f}%p")
    print()
# 손절일 갭하락 실태
cnt=0;worse=[]
for r in R:
    e=E[r["i"]];s=e["ser"];b=e["bi_local"];P=e["entry_price"];S=P*0.9
    d,g=gsim(e,realfill=True)
    if g< -10.0001:
        cnt+=1; worse.append(g)
print(f"손절 체결이 -10%보다 나빴던 거래 {cnt}건, 평균 실현 {st.mean(worse):.2f}% (최악 {min(worse):.1f}%)")
