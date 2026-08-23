import json, math, collections, statistics as st
from datetime import date
P=r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json"
rows=json.load(open(P,encoding="utf-8"))
def D(s): y,m,d=map(int,s.split("-")); return date(y,m,d)
lag=collections.Counter((D(r["open_date"])-D(r["prev_dd"])).days for r in rows)
print("calendar lag prev->buy:", dict(sorted(lag.items())))

def mwu(a,b):
    # returns AUC(a>b), z, p (two-sided), tie-corrected, continuity corrected
    all_v=sorted(a+b); n1,n2=len(a),len(b); N=n1+n2
    # ranks with ties
    vals=sorted(a+b); ranks={}
    i=0; rk={}
    arr=vals
    while i<len(arr):
        j=i
        while j+1<len(arr) and arr[j+1]==arr[i]: j+=1
        r=(i+j)/2+1
        rk[arr[i]]=r
        i=j+1
    R1=sum(rk[v] for v in a)
    U1=R1-n1*(n1+1)/2
    auc=U1/(n1*n2)
    ties=collections.Counter(arr)
    tie_term=sum(t**3-t for t in ties.values())
    mu=n1*n2/2
    sd=math.sqrt(n1*n2/12*((N+1)-tie_term/(N*(N-1))))
    z=(abs(U1-mu)-0.5)/sd if sd>0 else 0.0
    p=2*(1-0.5*(1+math.erf(z/math.sqrt(2))))
    return auc,(U1-mu)/sd if sd>0 else 0.0,p

def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    ph=k/n; d=1+z*z/n
    c=(ph+z*z/(2*n))/d
    h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return (c-h, c+h)

win=[r for r in rows if r["net"]>0]; lose=[r for r in rows if r["net"]<=0]
print("n win",len(win),"n lose",len(lose))
for key in ("sp","ss"):
    a=[r[key] for r in win if r[key] is not None]; b=[r[key] for r in lose if r[key] is not None]
    auc,z,p=mwu(a,b)
    print(f"{key}: win n={len(a)} med={st.median(a):.1f} mean={st.mean(a):.1f} | lose n={len(b)} med={st.median(b):.1f} mean={st.mean(b):.1f} | AUC={auc:.3f} z={z:.2f} p={p:.3f}")

# bins
def bins(key,edges):
    print(f"-- {key} bins {edges}")
    for lo,hi in zip(edges[:-1],edges[1:]):
        g=[r for r in rows if r[key] is not None and lo<=r[key]<hi]
        if not g: print(f"  [{lo},{hi}) n=0"); continue
        w=sum(1 for r in g if r["net"]>0)
        lo_,hi_=wilson(w,len(g))
        print(f"  [{lo},{hi}) n={len(g)} win={w} ({w/len(g)*100:.0f}%, CI {lo_*100:.0f}-{hi_*100:.0f}%) meanNet={st.mean([r['net'] for r in g]):+.2f}%")
bins("sp",[0,20,50,101])
bins("sp",[0,20,40,60,80,101])
# cuts
print("-- cut sweep (sp)")
for c in [1,5,10,15,20,25,30,40,50,60]:
    lo_g=[r for r in rows if r["sp"]<c]; hi_g=[r for r in rows if r["sp"]>=c]
    if not lo_g or not hi_g: continue
    wl=sum(1 for r in lo_g if r["net"]>0); wh=sum(1 for r in hi_g if r["net"]>0)
    print(f"  cut {c:>3}: <c n={len(lo_g)} win {wl/len(lo_g)*100:.0f}% mean {st.mean([r['net'] for r in lo_g]):+.2f} | >=c n={len(hi_g)} win {wh/len(hi_g)*100:.0f}% mean {st.mean([r['net'] for r in hi_g]):+.2f}")
# correlation
xs=[r["sp"] for r in rows]; ys=[r["net"] for r in rows]
def pearson(x,y):
    n=len(x); mx=st.mean(x);my=st.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
    return num/den
def rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v)
    i=0
    while i<len(s):
        j=i
        while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[s[k]]=avg
        i=j+1
    return r
print(f"pearson r={pearson(xs,ys):.3f} spearman={pearson(rank(xs),rank(ys)):.3f}")
# distribution
print("sp distribution:", collections.Counter("0" if r["sp"]==0 else "0-20" if r["sp"]<20 else "20-50" if r["sp"]<50 else "50+" for r in rows))
print("tightest condition counts:", collections.Counter(r["p_tight"] for r in rows))
# loss structure
losses=[r["net"] for r in rows if r["net"]<=0]
print("losses <=-4.5:",sum(1 for x in losses if x<=-4.5),"in -6.5..-4.5:",sum(1 for x in losses if -6.5<=x<=-4.5))
print("hold days of losers:", collections.Counter(r["hold"] for r in rows if r["net"]<=0))
print("median net all:", st.median([r["net"] for r in rows]), "mean:", round(st.mean([r["net"] for r in rows]),2))
