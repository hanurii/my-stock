import json, sys, math, collections, statistics as st
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
rows=json.load(open(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json",encoding="utf-8"))
sc=json.load(open(r"C:\Users\hanul\playground\my-stock\public\data\scorecard.json",encoding="utf-8"))
key={(t["code"],t["open_date"],t["close_date"]):t for t in sc["trades"]}
res=[]
for r in rows:
    t=key[(r["code"],r["open_date"],r["close_date"])]
    px=None
    s=ohlcv_matrix.get_series(r["code"])
    ds=s["dates"]
    if r["open_date"] not in ds: continue
    i=ds.index(r["open_date"]); px=s["closes"][i]
    for H in (10,20):
        pass
    row=dict(r)
    for H in (5,10,20):
        j=min(i+H, len(ds)-1)
        hi=max(s["highs"][i:j+1]); lo=min(s["lows"][i:j+1]); cl=s["closes"][j]
        row[f"mfe{H}"]=(hi/px-1)*100; row[f"mae{H}"]=(lo/px-1)*100; row[f"fwd{H}"]=(cl/px-1)*100
        row[f"bars{H}"]=j-i
    res.append(row)
print("n",len(res),"| trades with <20 future bars:",sum(1 for r in res if r["bars20"]<20))
def mwu(a,b):
    arr=sorted(a+b); rk={}; i=0
    while i<len(arr):
        j=i
        while j+1<len(arr) and arr[j+1]==arr[i]: j+=1
        rk[arr[i]]=(i+j)/2+1; i=j+1
    n1,n2=len(a),len(b); N=n1+n2
    U1=sum(rk[v] for v in a)-n1*(n1+1)/2
    ties=collections.Counter(arr); tt=sum(t**3-t for t in ties.values())
    sd=math.sqrt(n1*n2/12*((N+1)-tt/(N*(N-1)))); mu=n1*n2/2
    z=(abs(U1-mu)-0.5)/sd; p=2*(1-0.5*(1+math.erf(z/math.sqrt(2))))
    return U1/(n1*n2), p
def pear(x,y):
    mx=st.mean(x);my=st.mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
def rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); rr=[0]*len(v); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): rr[s[k]]=avg
        i=j+1
    return rr
sp=[r["sp"] for r in res]
print("\n-- stop-free forward outcomes vs entry margin (spearman) --")
for m in ("mfe5","mfe10","mfe20","mae10","mae20","fwd5","fwd10","fwd20"):
    v=[r[m] for r in res]
    print(f"  {m:6}: spearman={pear(rank(sp),rank(v)):+.3f}  mean={st.mean(v):+6.2f}%")
print("\n-- bins on stop-free 20-day outcome --")
for lo,hi in [(0,20),(20,50),(50,101)]:
    g=[r for r in res if lo<=r["sp"]<hi]
    print(f"  [{lo},{hi}) n={len(g)} mfe20={st.mean([r['mfe20'] for r in g]):+6.2f}% mae20={st.mean([r['mae20'] for r in g]):+6.2f}% fwd20={st.mean([r['fwd20'] for r in g]):+6.2f}% | mfe20>=+10%: {sum(1 for r in g if r['mfe20']>=10)}/{len(g)}")
a=[r["mfe20"] for r in res if r["sp"]>=30]; b=[r["mfe20"] for r in res if r["sp"]<30]
auc,p=mwu(a,b); print(f"\n  mfe20 sp>=30 vs <30: AUC={auc:.3f} p={p:.3f}")
