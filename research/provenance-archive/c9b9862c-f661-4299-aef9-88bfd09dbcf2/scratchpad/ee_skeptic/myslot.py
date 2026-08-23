import json, statistics as st, random, collections
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
CAL=sorted({d for e in E for d in e["ser"]["dates"]})
IDX={d:i for i,d in enumerate(CAL)}
def exit_date(i,k):
    s=E[i]["ser"]; b=E[i]["bi_local"]; return s["dates"][min(b+k,len(s["dates"])-1)]
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
def base(r): return (r["days"],r["gain"])
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
def slotsim(policy,nslot=5,seed=None):
    order=sorted(range(len(R)),key=lambda i:(R[i]["entry_date"],i))
    if seed is not None:
        rnd=random.Random(seed); bk=collections.defaultdict(list)
        for i in order: bk[R[i]["entry_date"]].append(i)
        order=[]
        for d in sorted(bk):
            b=bk[d][:]; rnd.shuffle(b); order+=b
    free=[-1]*nslot; g=[]; cnt=0
    for i in order:
        ei=IDX[R[i]["entry_date"]]; s=None
        for si in range(nslot):
            if free[si]<=ei: s=si; break
        if s is None: continue
        d,gain=policy(R[i]); free[s]=IDX[exit_date(i,d)]; g.append(gain); cnt+=1
    return g
pols=[("현행 +20/-10",base),("트레일 -15%",lambda r:gsim(E[r["i"]],trail=15.0)),
      ("트레일 -10%",lambda r:gsim(E[r["i"]],trail=10.0)),("익절 +15%",lambda r:gsim(E[r["i"]],target=15.0)),
      ("N=10일",lambda r:gsim(E[r["i"]],ndays=10)),
      ("규칙 heavy_vol",rulepol(lambda r:r["fires"]["heavy_volume_pullback"])),
      ("규칙 ANY5",rulepol(anyf))]
for ns in (5,):
    print(f"[슬롯 {ns} · 동일진입일 순서 무작위 500회]")
    store={}
    for name,p in pols:
        eqs=[];cnts=[];sums=[]
        for sd in range(500):
            g=slotsim(p,ns,seed=sd); eq=1.0
            for x in g: eq*=(1+x/100/ns)
            eqs.append((eq-1)*100); cnts.append(len(g)); sums.append(sum(g))
        store[name]=eqs
        print(f"  {name:<16} 체결중앙 {st.median(cnts):>4.0f} 합계%p중앙 {st.median(sums):>7.1f} 복리중앙 {st.median(eqs):+7.2f}%  [5~95%: {sorted(eqs)[25]:+7.2f} ~ {sorted(eqs)[474]:+7.2f}]")
    b=store["현행 +20/-10"]
    for name,_ in pols[1:]:
        print(f"     {name} > 현행: {sum(1 for i in range(500) if store[name][i]>b[i])}/500")
# 결정론(파일순서) 한 번
print()
for name,p in pols[:2]:
    g=slotsim(p,5,None); eq=1.0
    for x in g: eq*=(1+x/100/5)
    print(f"  결정론 순서(파일순) {name}: 체결 {len(g)} 합계 {sum(g):.1f}%p 복리 {(eq-1)*100:+.2f}%")
