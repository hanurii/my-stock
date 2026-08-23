import sys, os, json, bisect, time, glob
import numpy as np
ROOT = r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from canslim_lib.trend_template import evaluate_trend_template, WINDOW_52W

P=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad\passmatrix.npz'
z=np.load(P, allow_pickle=True)
pmdates=list(z['dates']); pmcodes=list(z['codes']); ap=z['all_pass']

SER=os.path.join(ROOT,".cache","ohlcv","series")
full={}
for f in glob.glob(os.path.join(SER,"*.json")):
    c=os.path.basename(f)[:-5]
    d=json.load(open(f,encoding="utf-8"))
    if d.get("closes"): full[c]=(d["dates"],d["closes"])

def cache_pass(D, rs_min=80):
    st={}
    for c,(dt,cl) in full.items():
        i=bisect.bisect_right(dt,D)
        if i>=200: st[c]=cl[:i]
    own={}
    for c,cl in st.items():
        n=len(cl); w=min(n-1,WINDOW_52W)
        if w<20 or len(cl)<w+1: continue
        b=cl[-w-1]
        if not b or b<=0: continue
        own[c]=(w,cl[-1]/b-1.0)
    bw={}
    for c,(w,r) in own.items(): bw.setdefault(w,[]).append(r)
    sw={w:sorted(v) for w,v in bw.items()}
    rs={}
    for c,(w,r) in own.items():
        p=sw[w]; rs[c]=None if len(p)<100 else max(1,min(99,round(bisect.bisect_left(p,r)/len(p)*100)))
    return set(c for c,cl in st.items() if evaluate_trend_template(cl,rs=rs.get(c),rs_min=rs_min)["pass"])

both=set(full)&set(pmcodes)
print("codes in both:", len(both))
for D in ["2025-11-26","2025-12-05","2026-01-13","2026-02-16","2026-03-16","2026-04-02","2026-05-15","2026-06-15","2026-07-15","2026-08-13"]:
    if D not in pmdates:
        print(D,"not in passmatrix dates"); continue
    i=pmdates.index(D)
    pm=set(np.array(pmcodes)[ap[i]]) & both
    ca=cache_pass(D) & both
    inter=len(pm&ca); un=len(pm|ca)
    print(f"{D}  passmatrix={len(pm):4d}  cache={len(ca):4d}  overlap={inter:4d}  jaccard={inter/un if un else 0:.3f}  pm_only={len(pm-ca):3d}  cache_only={len(ca-pm):3d}", flush=True)
