import json, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"

d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
print("n events", len(ev), "unique codes", len({e['code'] for e in ev}))
from collections import Counter
print(Counter(e['result'] for e in ev))

# --- quartile reconstruction ---
vals=sorted(e['atr_pct'] for e in ev if e['atr_pct'] is not None)
print("atr None:", sum(1 for e in ev if e['atr_pct'] is None))
import statistics
n=len(vals)
def q(p):
    k=(n-1)*p
    f=int(k); c=min(f+1,n-1)
    return vals[f]+(vals[c]-vals[f])*(k-f)
q1,q2,q3=q(.25),q(.5),q(.75)
print(f"ATR quartile cuts: min={vals[0]:.2f} q25={q1:.2f} q50={q2:.2f} q75={q3:.2f} max={vals[-1]:.2f}")
def band(v):
    if v is None: return "미상"
    if v<=q1: return "Q1"
    if v<=q2: return "Q2"
    if v<=q3: return "Q3"
    return "Q4"
for e in ev: e['Q']=band(e['atr_pct'])
def stats(rows):
    c=Counter(r['result'] for r in rows)
    w,l,a,u=c['win'],c['loss'],c['ambiguous'],c['unresolved']
    res=w+l
    wr=w/res*100 if res else float('nan')
    ev20=(w*20-l*10)/res if res else float('nan')
    return dict(n=len(rows),win=w,loss=l,amb=a,unres=u,wr=round(wr,1),ev=round(ev20,2),
                codes=len({r['code'] for r in rows}))
print("\n[재계산 사분위]")
for k in ["Q1","Q2","Q3","Q4"]:
    rows=[e for e in ev if e['Q']==k]
    lo=min(r['atr_pct'] for r in rows); hi=max(r['atr_pct'] for r in rows)
    print(f"  {k} ({lo:.1f}~{hi:.1f}%) {stats(rows)}")
print("  전체", stats(ev))
