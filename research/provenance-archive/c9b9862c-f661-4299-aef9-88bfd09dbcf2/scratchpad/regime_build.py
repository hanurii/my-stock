# -*- coding: utf-8 -*-
import json, collections, math, statistics, os, pickle

ROOT = r"C:/Users/hanul/playground/my-stock"
d = json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
events = [x for x in d["events"] if x["result"] in ("win","loss")]
reg = json.load(open(ROOT+"/public/data/market-regime.json", encoding="utf-8"))["series"]

dates = [r["date"] for r in reg]
idx   = [r["index"] for r in reg]
ma20  = [r["ma20"] for r in reg]
up    = [bool(r["up"]) for r in reg]
pos = {dt:i for i,dt in enumerate(dates)}
N = len(dates)

def ret(i,k):
    if i-k < 0: return None
    a,b = idx[i-k], idx[i]
    if a is None or b is None or a==0: return None
    return (b/a-1)*100

M = {}   # metric name -> list over calendar index (None if undefined)

M["①지수5일수익"]   = [ret(i,5) for i in range(N)]
M["②지수10일수익"]  = [ret(i,10) for i in range(N)]
M["③지수20일수익"]  = [ret(i,20) for i in range(N)]
M["④지수60일수익"]  = [ret(i,60) for i in range(N)]
M["⑤20일선기울기5"] = [None if i<5 or ma20[i] is None or ma20[i-5] is None else (ma20[i]/ma20[i-5]-1)*100 for i in range(N)]
M["⑥20일선기울기10"]= [None if i<10 or ma20[i] is None or ma20[i-10] is None else (ma20[i]/ma20[i-10]-1)*100 for i in range(N)]
M["⑦20일선이격"]    = [None if ma20[i] in (None,0) else (idx[i]/ma20[i]-1)*100 for i in range(N)]

# days since regime flip
dsf=[]; cnt=0
for i in range(N):
    if i>0 and up[i]!=up[i-1]: cnt=0
    else: cnt = cnt+1 if i>0 else 0
    dsf.append(cnt)
M["⑧국면경과일"] = dsf

# drawdown from 60d high of index
def dd(i,k):
    if i-k+1 < 0: return None
    w = idx[max(0,i-k+1):i+1]
    hi = max(w)
    return (idx[i]/hi-1)*100 if hi else None
M["⑨60일고점대비"] = [dd(i,60) for i in range(N)]
M["⑩120일고점대비"] = [dd(i,120) for i in range(N)]

# realized vol of index (20d std of daily % change)
def rv(i,k):
    if i-k < 0: return None
    r=[]
    for j in range(i-k+1, i+1):
        if idx[j-1]: r.append((idx[j]/idx[j-1]-1)*100)
    return statistics.pstdev(r) if len(r)>2 else None
M["⑪지수변동성20"] = [rv(i,20) for i in range(N)]
M["⑫지수변동성10"] = [rv(i,10) for i in range(N)]

# fraction of up days
def fracup(i,k):
    if i-k < 0: return None
    c=0
    for j in range(i-k+1,i+1):
        if idx[j] > idx[j-1]: c+=1
    return c/k*100
M["⑬상승일비율10"] = [fracup(i,10) for i in range(N)]
M["⑭상승일비율20"] = [fracup(i,20) for i in range(N)]

# index percentile rank within trailing 120d
def pct(i,k=120):
    if i-k+1 < 0: return None
    w = idx[max(0,i-k+1):i+1]
    return sum(1 for v in w if v<=idx[i])/len(w)*100
M["⑮지수120일백분위"] = [pct(i) for i in range(N)]

# acceleration: 10d ret minus prior 10d ret
M["⑯지수10일가속"] = [None if (ret(i,10) is None or ret(i-10,10) is None or i-20<0) else ret(i,10)-ret(i-10,10) for i in range(N)]

# ma20 curvature: slope5 - prior slope5
s5 = M["⑤20일선기울기5"]
M["⑰20일선가속"] = [None if (i-5<0 or s5[i] is None or s5[i-5] is None) else s5[i]-s5[i-5] for i in range(N)]

# consecutive up-closes of index
cu=[]; c=0
for i in range(N):
    if i>0 and idx[i]>idx[i-1]: c+=1
    else: c=0
    cu.append(c)
M["⑱지수연속상승일"] = cu

pickle.dump({"dates":dates,"pos":pos,"M":M,"up":up,"idx":idx,"ma20":ma20},
            open(os.path.dirname(os.path.abspath(__file__))+"/regime_metrics.pkl","wb"))

# day-level outcomes keyed by entry_date; metric measured at previous trading day (scan close)
byday = collections.defaultdict(lambda: [0,0])
for e in events:
    byday[e["entry_date"]][0]+=1
    byday[e["entry_date"]][1]+= 1 if e["result"]=="win" else 0
print("entry days:", len(byday), "trades:", sum(v[0] for v in byday.values()),
      "wins:", sum(v[1] for v in byday.values()))
miss=[dt for dt in byday if dt not in pos]
print("entry dates missing from regime calendar:", len(miss), miss[:5])
# check prior-day availability
prior_missing=[dt for dt in byday if dt in pos and pos[dt]==0]
print("prior missing:", prior_missing)
print("regime calendar:", dates[0], dates[-1], N)
