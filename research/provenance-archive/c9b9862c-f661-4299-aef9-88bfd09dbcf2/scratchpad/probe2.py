import sys, os, json, bisect, time, glob
ROOT = r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from canslim_lib.trend_template import evaluate_trend_template, WINDOW_52W
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P
from canslim_lib.power_play import evaluate_power_play
from canslim_lib.pivot_backtest import truncate_series

SER = os.path.join(ROOT, ".cache", "ohlcv", "series")
t0=time.time()
full={}
for f in glob.glob(os.path.join(SER, "*.json")):
    code = os.path.basename(f)[:-5]
    d = json.load(open(f, encoding="utf-8"))
    if d.get("closes"): full[code]=d
print("loaded", len(full), "%.1fs"%(time.time()-t0))

def scan(D, rs_min=80):
    t_tr=time.time()
    st={}
    for c,s in full.items():
        t=truncate_series(s,D)
        if len(t["closes"])>=200: st[c]=t
    tr=time.time()-t_tr
    t_rs=time.time()
    own={}
    for c,t in st.items():
        n=len(t["closes"]); w=min(n-1,WINDOW_52W)
        if w<20 or len(t["closes"])<w+1: continue
        b=t["closes"][-w-1]
        if not b or b<=0: continue
        own[c]=(w,t["closes"][-1]/b-1.0)
    bw={}
    for c,(w,r) in own.items(): bw.setdefault(w,[]).append(r)
    sw={w:sorted(v) for w,v in bw.items()}
    rs={}
    for c,(w,r) in own.items():
        p=sw[w]
        rs[c]=None if len(p)<100 else max(1,min(99,round(bisect.bisect_left(p,r)/len(p)*100)))
    rst=time.time()-t_rs
    t_tt=time.time()
    passers=[c for c,t in st.items() if evaluate_trend_template(t["closes"],rs=rs.get(c),rs_min=rs_min)["pass"]]
    ttt=time.time()-t_tt
    t_det=time.time()
    act={"VCP":0,"3C":0,"PP":0}; er={"VCP":0,"3C":0,"PP":0}
    for c in passers:
        t=st[c]
        for name,fn in (("VCP",lambda x:evaluate_vcp(x)),("3C",lambda x:evaluate_cheat(x,CHEAT_P)),("PP",lambda x:evaluate_power_play(x))):
            try: r=fn(t)
            except Exception: continue
            if r.get("status")=="actionable" and r.get("pivot_price"): act[name]+=1
            if r.get("entry_ready") and r.get("status")=="actionable" and r.get("pivot_price"): er[name]+=1
    dett=time.time()-t_det
    return dict(D=D, n_eval=len(st), n_pass=len(passers), actionable=act, entry_ready=er,
                sec=dict(trunc=round(tr,2), rs=round(rst,2), tt=round(ttt,2), det=round(dett,2),
                         total=round(tr+rst+ttt+dett,2)))

for D in ["2025-12-05","2026-02-16","2026-04-02","2026-06-15","2026-08-13"]:
    print(json.dumps(scan(D), ensure_ascii=False), flush=True)
