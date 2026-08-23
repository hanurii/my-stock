import sys, os, json, bisect, glob
ROOT=r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT,"scripts"))
from canslim_lib.trend_template import evaluate_trend_template, compute_gate_margin, WINDOW_52W
SER=os.path.join(ROOT,".cache","ohlcv","series")
full={}
for f in glob.glob(os.path.join(SER,"*.json")):
    c=os.path.basename(f)[:-5]; d=json.load(open(f,encoding="utf-8"))
    if d.get("closes"): full[c]=(d["dates"],d["closes"])
scores=[]
for D in ["2026-02-16","2026-04-02","2026-06-15","2026-08-13"]:
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
    rs={c:(None if len(sw[w])<100 else max(1,min(99,round(bisect.bisect_left(sw[w],r)/len(sw[w])*100)))) for c,(w,r) in own.items()}
    for c,cl in st.items():
        res=evaluate_trend_template(cl,rs=rs.get(c),rs_min=80)
        if not res["pass"]: continue
        gm=compute_gate_margin(res, cl[-1], rs.get(c), rs_min=80)
        if gm and gm.get("score") is not None: scores.append(gm["score"])
scores.sort()
n=len(scores)
print("gate-margin scores on TT passers, n=",n)
print("quartile cuts:", [round(scores[int(n*q)],1) for q in (0.25,0.5,0.75)])
print("min/max:", scores[0], scores[-1])
