import json, os, sys, glob, math, collections, statistics as st
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib.trend_template import compute_gate_margin
BY = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\bydata"
files={}
for p in sorted(glob.glob(os.path.join(BY,"*.json"))):
    d=json.load(open(p,encoding="utf-8")); files[d["data_date"]]=d
dates=sorted(files)
led=json.load(open(r"C:\Users\hanul\playground\my-stock\public\data\sepa-buy-rec-ledger.json",encoding="utf-8"))
rows=[]
miss=0
for e in led["entries"]:
    dt=e["date"]; code=e["code"]
    prev=[d for d in dates if d < dt]
    same=[d for d in dates if d <= dt]
    def get(dd):
        if not dd: return None
        rec=files[dd]["recs"].get(code)
        if rec is None: return None
        gm=compute_gate_margin(rec, rec.get("current_price"), rec.get("rs"), rs_min=80)
        return gm["score"] if gm else None
    sp=get(prev[-1] if prev else None); ss=get(same[-1] if same else None)
    if sp is None: miss+=1
    r=e.get("resolved") or {}
    rows.append(dict(date=dt,code=code,name=e["name"],status=e.get("status"),sp=sp,ss=ss,
                     outcome=r.get("outcome"),cur=r.get("cur_ret_pct"),maxg=r.get("max_gain_pct"),days=r.get("days")))
json.dump(rows,open(os.path.join(os.path.dirname(BY),"ledger_mine.json"),"w",encoding="utf-8"),ensure_ascii=False)
print("entries",len(rows),"prev score missing",miss)
res=[r for r in rows if r["outcome"] in ("target","stop") and r["sp"] is not None]
print("resolved w/ score:",len(res),collections.Counter(r["outcome"] for r in res))
def mwu(a,b):
    arr=sorted(a+b); rk={}; i=0
    while i<len(arr):
        j=i
        while j+1<len(arr) and arr[j+1]==arr[i]: j+=1
        rk[arr[i]]=(i+j)/2+1; i=j+1
    n1,n2=len(a),len(b); N=n1+n2
    R1=sum(rk[v] for v in a); U1=R1-n1*(n1+1)/2
    ties=collections.Counter(arr); tt=sum(t**3-t for t in ties.values())
    sd=math.sqrt(n1*n2/12*((N+1)-tt/(N*(N-1)))); mu=n1*n2/2
    z=(abs(U1-mu)-0.5)/sd; p=2*(1-0.5*(1+math.erf(z/math.sqrt(2))))
    return U1/(n1*n2), (U1-mu)/sd, p
tg=[r["sp"] for r in res if r["outcome"]=="target"]; sto=[r["sp"] for r in res if r["outcome"]=="stop"]
auc,z,p=mwu(tg,sto)
print(f"target n={len(tg)} med={st.median(tg):.1f} mean={st.mean(tg):.1f} | stop n={len(sto)} med={st.median(sto):.1f} mean={st.mean(sto):.1f} | AUC={auc:.3f} z={z:.2f} p={p:.4f}")
for lo,hi in [(0,20),(20,40),(40,60),(60,80),(80,101)]:
    g=[r for r in res if lo<=r["sp"]<hi]
    if not g: continue
    t=sum(1 for r in g if r["outcome"]=="target")
    print(f"  [{lo},{hi}) n={len(g)} target={t} ({t/len(g)*100:.0f}%)")
for c in [5,10,20,30,50]:
    a=[r for r in res if r["sp"]<c]; b=[r for r in res if r["sp"]>=c]
    if not a or not b: continue
    print(f"  cut {c}: <c n={len(a)} target {sum(1 for r in a if r['outcome']=='target')/len(a)*100:.0f}% | >=c n={len(b)} target {sum(1 for r in b if r['outcome']=='target')/len(b)*100:.0f}%")
# cur_ret across all with score (incl open)
allr=[r for r in rows if r["sp"] is not None and r["cur"] is not None]
print("all entries with cur_ret:",len(allr))
for lo,hi in [(0,20),(20,40),(40,60),(60,80),(80,101)]:
    g=[r for r in allr if lo<=r["sp"]<hi]
    if g: print(f"  [{lo},{hi}) n={len(g)} mean cur_ret={st.mean([r['cur'] for r in g]):+.2f}% mean max_gain={st.mean([r['maxg'] for r in g if r['maxg'] is not None]):+.2f}%")
