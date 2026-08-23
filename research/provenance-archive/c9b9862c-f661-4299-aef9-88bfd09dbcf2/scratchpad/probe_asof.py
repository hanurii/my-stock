import sys, os, json, bisect, time, glob
ROOT = r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from canslim_lib.trend_template import evaluate_trend_template, WINDOW_52W

SER = os.path.join(ROOT, ".cache", "ohlcv", "series")
files = sorted(glob.glob(os.path.join(SER, "*.json")))
t0=time.time()
data = {}
for f in files:
    code = os.path.basename(f)[:-5]
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if d.get("closes"):
        data[code] = (d["dates"], d["closes"])
print("loaded", len(data), "codes in %.1fs" % (time.time()-t0))

def run(asof, rs_min=80, min_pool=100):
    rows = []
    for code,(dt,cl) in data.items():
        idx = bisect.bisect_right(dt, asof)
        c = cl[:idx]
        if len(c) < 200:
            continue
        rows.append((code, c))
    # RS
    own = {}
    for code, c in rows:
        n=len(c); win=min(n-1, WINDOW_52W)
        if win < 20: continue
        if len(c) < win+1: continue
        base = c[-win-1]
        if not base or base<=0: continue
        own[code]=(win, c[-1]/base-1.0)
    by_win={}
    for code,(w,r) in own.items(): by_win.setdefault(w,[]).append(r)
    sorted_by_win={w:sorted(v) for w,v in by_win.items()}
    rs_map={}
    for code,(w,r) in own.items():
        pool=sorted_by_win[w]
        if len(pool)<min_pool: rs_map[code]=None; continue
        below=bisect.bisect_left(pool,r)
        rs_map[code]=max(1,min(99,round(below/len(pool)*100)))
    npass=0; pc_hist={}; c_fail={str(i):0 for i in range(1,9)}
    passers=[]
    for code,c in rows:
        res = evaluate_trend_template(c, rs=rs_map.get(code), rs_min=rs_min)
        pc_hist[res["passed_count"]]=pc_hist.get(res["passed_count"],0)+1
        for k,v in res["criteria"].items():
            if not v["pass"]: c_fail[k]+=1
        if res["pass"]:
            npass+=1; passers.append(code)
    return dict(asof=asof, evaluable=len(rows), rs_ok=sum(1 for v in rs_map.values() if v is not None),
                win_pool_sizes={w:len(v) for w,v in sorted(sorted_by_win.items())[-3:]},
                npass=npass, fail_by_criterion=c_fail, sample=passers[:10])

for a in ["2025-06-02","2025-10-27","2025-11-26","2025-12-05","2026-01-13","2026-04-02","2026-08-13","2026-08-21"]:
    t=time.time(); r=run(a); r["secs"]=round(time.time()-t,2)
    print(json.dumps(r, ensure_ascii=False))
