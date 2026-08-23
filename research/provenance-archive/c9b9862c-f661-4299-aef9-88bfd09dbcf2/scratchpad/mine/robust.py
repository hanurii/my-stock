import json, math, random, statistics as st, collections, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
P=r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json"
rows=json.load(open(P,encoding="utf-8"))

# --- 1) clustered (block) permutation by code, max over cuts
rows.sort(key=lambda r:r["sp"]); n=len(rows); sp=[r["sp"] for r in rows]
MIN=5; splits=[k for k in range(MIN,n-MIN+1) if sp[k-1]!=sp[k]]
def maxstat(lab):
    pre=[0.0]*(n+1)
    for i,v in enumerate(lab): pre[i+1]=pre[i]+v
    return max(abs(pre[k]/k-(pre[n]-pre[k])/(n-k)) for k in splits)
codes=collections.defaultdict(list)
for i,r in enumerate(rows): codes[r["code"]].append(i)
groups=list(codes.values())
for name,lab in (("winrate",[1.0 if r["net"]>0 else 0.0 for r in rows]),("meanNet",[r["net"] for r in rows])):
    obs=maxstat(lab); random.seed(3); NP=20000; c=0
    for _ in range(NP):
        gv=[[lab[i] for i in g] for g in groups]
        random.shuffle(gv)
        perm=[0.0]*n
        for g,vals in zip(groups,gv):
            # reassign whole blocks; block sizes vary so pad/truncate by cycling
            for pos,i in enumerate(g): perm[i]=vals[pos%len(vals)]
        if maxstat(perm)>=obs-1e-12: c+=1
    print(f"cluster-permuted (block by code) {name}: obs={obs:.4f} p={(c+1)/(NP+1):.4f}")

# --- 2) per-condition tests with Holm correction
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
ps=[]
for k in "12345678":
    a=[r["p_per"][k] for r in rows if r["net"]>0]; b=[r["p_per"][k] for r in rows if r["net"]<=0]
    auc,p=mwu(a,b); ps.append((k,auc,p,st.median(a),st.median(b)))
ps_sorted=sorted(ps,key=lambda x:x[2])
m=len(ps)
print("per-condition (Holm):")
for rank,(k,auc,p,ma,mb) in enumerate(ps_sorted):
    holm=min(1.0,p*(m-rank))
    print(f"  cond {k}: win med={ma:.1f} lose med={mb:.1f} AUC={auc:.3f} raw p={p:.3f} Holm p={holm:.3f}")
